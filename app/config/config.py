import os
from pathlib import Path
from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)
from typing import Optional

def env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}

def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except ValueError:
        return default

def env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except ValueError:
        return default


# =========================
# Secrets / Tokens
# =========================
HF_TOKEN: Optional[str] = os.environ.get("HF_TOKEN")


# =========================
# LLM
# =========================
# Safer default is hf-inference; set to "together" only if you're sure.
HF_PROVIDER = os.environ.get("HF_PROVIDER", "hf-inference")
HUGGINGFACE_REPO_ID = os.environ.get("HF_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")
HF_MAX_TOKENS = env_int("HF_MAX_TOKENS", 512)
HF_TEMPERATURE = env_float("HF_TEMPERATURE", 0.2)
HF_TOP_P = env_float("HF_TOP_P", 0.9)
HF_TIMEOUT = env_int("HF_TIMEOUT", 120)


# =========================
# Paths
# =========================
DB_FAISS_PATH = os.environ.get("DB_FAISS_PATH", "vectorstore/db_faiss")
DATA_PATH = os.environ.get("DATA_PATH", "data")

PARENT_DOCS_PATH = os.environ.get(
    "PARENT_DOCS_PATH", os.path.join(DB_FAISS_PATH, "parent_docs.json")
)


# =========================
# Chunking
# =========================
CHUNK_SIZE = env_int("CHUNK_SIZE", 500)
CHUNK_OVERLAP = env_int("CHUNK_OVERLAP", 50)

PARENT_CHUNK_SIZE = env_int("PARENT_CHUNK_SIZE", 1400)
PARENT_CHUNK_OVERLAP = env_int("PARENT_CHUNK_OVERLAP", 200)


# =========================
# Retrieval / Guardrails
# =========================
DEFAULT_ROUTE = os.environ.get("DEFAULT_ROUTE", "pdf")
RETRIEVAL_K = env_int("RETRIEVAL_K", 4)
RETRIEVAL_MIN_RELEVANCE = env_float("RETRIEVAL_MIN_RELEVANCE", 0.12)

RETRIEVAL_FETCH_K = env_int("RETRIEVAL_FETCH_K", 12)
RETRIEVAL_MMR_LAMBDA = env_float("RETRIEVAL_MMR_LAMBDA", 0.6)

MULTI_QUERY_COUNT = env_int("MULTI_QUERY_COUNT", 3)
MULTI_QUERY_ENABLED = env_bool("MULTI_QUERY_ENABLED", True)

RERANK_ENABLED = env_bool("RERANK_ENABLED", True)
RERANK_TOP_N = env_int("RERANK_TOP_N", 6)
RERANK_CANDIDATES = env_int("RERANK_CANDIDATES", 12)
RERANK_MAX_CHARS = env_int("RERANK_MAX_CHARS", 1200)

CONTEXT_COMPRESSION_ENABLED = env_bool("CONTEXT_COMPRESSION_ENABLED", True)
CONTEXT_MAX_CHARS = env_int("CONTEXT_MAX_CHARS", 4000)

CONTEXT_MAX_SENTENCES_PER_DOC = env_int("CONTEXT_MAX_SENTENCES_PER_DOC", 5)
CONTEXT_MAX_SENTENCES_TOTAL = env_int("CONTEXT_MAX_SENTENCES_TOTAL", 16)
CONTEXT_SENTENCE_CANDIDATE_LIMIT = env_int("CONTEXT_SENTENCE_CANDIDATE_LIMIT", 40)
CONTEXT_DOC_MAX_CHARS = env_int("CONTEXT_DOC_MAX_CHARS", 1200)

MEDICAL_DISCLAIMER = os.environ.get(
    "MEDICAL_DISCLAIMER",
    "This information is for educational purposes and not medical advice. Please consult a qualified doctor.",
)


# =========================
# Reranking (Cross-Encoder)
# =========================
CROSS_ENCODER_MODEL = os.environ.get(
    "CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
CROSS_ENCODER_DEVICE = os.environ.get("CROSS_ENCODER_DEVICE", "cpu")


# =========================
# Web Search (Tavily)
# =========================
TAVILY_API_KEY: Optional[str] = os.environ.get("TAVILY_API_KEY")
TAVILY_SEARCH_RESULTS = env_int("TAVILY_SEARCH_RESULTS", 5)
TAVILY_SEARCH_DEPTH = os.environ.get("TAVILY_SEARCH_DEPTH", "basic")


# =========================
# Speech (Server-side STT/TTS)
# =========================
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "en")



EDGE_TTS_VOICE = os.environ.get("EDGE_TTS_VOICE", "en-US-AriaNeural")
EDGE_TTS_RATE = os.environ.get("EDGE_TTS_RATE", "+0%")
EDGE_TTS_PITCH = os.environ.get("EDGE_TTS_PITCH", "+0Hz")
EDGE_TTS_OUTPUT_FORMAT = os.environ.get(
    "EDGE_TTS_OUTPUT_FORMAT", "audio-24khz-48kbitrate-mono-mp3"
)
