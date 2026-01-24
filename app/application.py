from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    stream_with_context,
    url_for,
)
from flask_cors import CORS
from dotenv import load_dotenv
import os
import time

from app.common.logger import get_logger

from app.components.guardrails import (
    build_fallback_payload,
    generate_guardrailed_response,
    serialize_payload,
)
from app.components.voice import (
    synthesize_speech,
    transcribe_audio,
    tts_mime_type,
    list_voices,
)
from app.config.config import (
    DEFAULT_ROUTE,
    EDGE_TTS_OUTPUT_FORMAT,
    EDGE_TTS_PITCH,
    EDGE_TTS_RATE,
    EDGE_TTS_VOICE,
)

load_dotenv()

app = Flask(__name__)
logger = get_logger(__name__)

ALLOWED_ROUTES = {"pdf", "web", "hybrid"}


def normalize_route(route: str) -> str:
    normalized = (route or DEFAULT_ROUTE).strip().lower()
    return normalized if normalized in ALLOWED_ROUTES else DEFAULT_ROUTE


def env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


# Allow local React dev server by default; override with CORS_ORIGINS
cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)
CORS(
    app,
    supports_credentials=True,
    origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
)

# NOTE: Use a strong secret in production (set FLASK_SECRET_KEY in env)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")


def get_session_messages():
    if "messages" not in session:
        session["messages"] = []
    return session["messages"]


def generate_answer(question: str, route: str = DEFAULT_ROUTE) -> str:
    """Generate a JSON string response using guardrails + retrieval."""
    try:
        return generate_guardrailed_response(question, route=route)
    except Exception:
        logger.exception("generate_answer failed (route=%s)", route)
        return serialize_payload(build_fallback_payload())


def stream_chunks(text: str, chunk_size: int = None, delay_s: float = None):
    if chunk_size is None:
        try:
            chunk_size = int(os.environ.get("STREAM_CHUNK_SIZE", "28"))
        except ValueError:
            chunk_size = 28
    if delay_s is None:
        try:
            delay_s = float(os.environ.get("STREAM_DELAY_S", "0"))
        except ValueError:
            delay_s = 0.0

    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]
        if delay_s:
            time.sleep(delay_s)


@app.route("/", methods=["GET"])
def home():
    messages = get_session_messages()
    return render_template("index.html", messages=messages)


@app.route("/chat", methods=["POST"])
def chat():
    question = (request.form.get("question") or request.form.get("prompt") or "").strip()
    route = normalize_route(request.form.get("route") or DEFAULT_ROUTE)
    messages = get_session_messages()

    if not question:
        return redirect(url_for("home"))

    messages.append({"role": "user", "content": question})
    answer = generate_answer(question, route=route)

    # Stored as JSON string (your guardrails returns JSON text)
    messages.append({"role": "assistant", "content": answer})
    session.modified = True

    return redirect(url_for("home"))


@app.route("/api/messages", methods=["GET"])
def api_messages():
    return jsonify({"messages": get_session_messages()})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    route = normalize_route(data.get("route") or DEFAULT_ROUTE)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    messages = get_session_messages()
    messages.append({"role": "user", "content": question})
    answer = generate_answer(question, route=route)
    messages.append({"role": "assistant", "content": answer})
    session.modified = True

    return jsonify({"messages": messages})


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    route = normalize_route(data.get("route") or DEFAULT_ROUTE)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    messages = get_session_messages()
    messages.append({"role": "user", "content": question})
    answer = generate_answer(question, route=route)
    messages.append({"role": "assistant", "content": answer})
    session.modified = True

    response = Response(
        stream_with_context(stream_chunks(answer)),
        mimetype="text/plain; charset=utf-8",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.route("/api/stt", methods=["POST"])
def api_stt():
    audio = request.files.get("audio")
    if audio is None or not audio.filename:
        return jsonify({"error": "Audio file is required"}), 400

    try:
        text, meta = transcribe_audio(audio)
        payload = {"text": text}
        payload.update(meta)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": f"STT failed: {e}"}), 500


@app.route("/api/voice/voices", methods=["GET"])
def api_voice_voices():
    """Frontend can call this to show voice dropdown."""
    try:
        voices = list_voices()
        lite = []
        for v in voices or []:
            lite.append(
                {
                    "name": v.get("Name"),
                    "shortName": v.get("ShortName"),
                    "locale": v.get("Locale"),
                    "gender": v.get("Gender"),
                }
            )
        return jsonify({"voices": lite})
    except Exception as e:
        return jsonify({"error": f"Failed to list voices: {e}"}), 500


@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Text is required"}), 400

    voice = data.get("voice") or EDGE_TTS_VOICE
    rate = data.get("rate") or EDGE_TTS_RATE
    pitch = data.get("pitch") or EDGE_TTS_PITCH
    # accept either key from frontend: output_format OR format
    output_format = data.get("output_format") or data.get("format") or EDGE_TTS_OUTPUT_FORMAT

    try:
        audio_bytes = synthesize_speech(
            text, voice=voice, rate=rate, pitch=pitch, output_format=output_format
        )
    except Exception as e:
        return jsonify({"error": f"TTS failed: {e}"}), 500

    response = Response(audio_bytes, mimetype=tts_mime_type(output_format))
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/api/clear", methods=["POST"])
def api_clear():
    session.pop("messages", None)
    return jsonify({"messages": []})


@app.route("/clear", methods=["POST", "GET"])
def clear_chat():
    session.pop("messages", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    debug = env_bool("FLASK_DEBUG", default=False)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=debug)