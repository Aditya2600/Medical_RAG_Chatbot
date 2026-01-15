import os

# Token
HF_TOKEN = os.environ.get("HF_TOKEN")

# LLM
HF_PROVIDER = os.environ.get("HF_PROVIDER", "together")
HUGGINGFACE_REPO_ID = os.environ.get("HF_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")

# Paths
DB_FAISS_PATH = os.environ.get("DB_FAISS_PATH", "vectorstore/db_faiss")
DATA_PATH = os.environ.get("DATA_PATH", "data/")

# Chunking
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 50))