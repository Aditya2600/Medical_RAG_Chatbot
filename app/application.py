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

from app.components.retriever import create_qa_chain

load_dotenv()

app = Flask(__name__)

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

# Build QA chain once at startup
qa_chain = None


def get_qa_chain():
    """Lazy init to avoid startup crash masking template/debug issues."""
    global qa_chain
    if qa_chain is None:
        qa_chain = create_qa_chain()
    return qa_chain


def get_session_messages():
    if "messages" not in session:
        session["messages"] = []
    return session["messages"]


def generate_answer(question: str) -> str:
    """Generate an answer using the LCEL Runnable chain.

    IMPORTANT:
    - Your retriever returns an LCEL RunnableSequence.
    - RunnableSequence is NOT callable; it must be invoked via `.invoke()`.

    Expected output shape from our chain:
        {"answer": "..."}
    """
    try:
        chain = get_qa_chain()
        result = chain.invoke({"input": question})

        if isinstance(result, dict):
            if "answer" in result and isinstance(result.get("answer"), str):
                return result["answer"]
            # If output shape changes in future, still return something usable
            if "result" in result and isinstance(result.get("result"), str):
                return result["result"]
            if "output_text" in result and isinstance(result.get("output_text"), str):
                return result["output_text"]
            return str(result)

        return str(result)

    except Exception as e:
        return f"Sorry, I couldn't process that right now. Error: {e}"


def stream_chunks(text: str, chunk_size: int = 28, delay_s: float = 0.02):
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]
        if delay_s:
            time.sleep(delay_s)


@app.route("/", methods=["GET"])
def home():
    """Landing page."""
    messages = get_session_messages()
    return render_template("index.html", messages=messages)


@app.route("/chat", methods=["POST"])
def chat():
    """Handle user question and return chatbot response."""
    question = (request.form.get("question") or request.form.get("prompt") or "").strip()
    messages = get_session_messages()

    if not question:
        return redirect(url_for("home"))

    # Add user message
    messages.append({"role": "user", "content": question})
    answer = generate_answer(question)

    # Add assistant message
    messages.append({"role": "assistant", "content": answer})
    session.modified = True

    return redirect(url_for("home"))


@app.route("/api/messages", methods=["GET"])
def api_messages():
    """Return chat history for the React frontend."""
    return jsonify({"messages": get_session_messages()})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Handle user question and return updated messages as JSON."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Question is required"}), 400

    messages = get_session_messages()
    messages.append({"role": "user", "content": question})
    answer = generate_answer(question)
    messages.append({"role": "assistant", "content": answer})
    session.modified = True

    return jsonify({"messages": messages})


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    """Stream assistant response as plain text chunks."""
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Question is required"}), 400

    messages = get_session_messages()
    messages.append({"role": "user", "content": question})
    answer = generate_answer(question)
    messages.append({"role": "assistant", "content": answer})
    session.modified = True

    response = Response(
        stream_with_context(stream_chunks(answer)),
        mimetype="text/plain; charset=utf-8",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Clear chat history for the React frontend."""
    session.pop("messages", None)
    return jsonify({"messages": []})


@app.route("/clear", methods=["POST", "GET"])
def clear_chat():
    """Clear chat history."""
    session.pop("messages", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    # Use 0.0.0.0 for docker deployment
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True)