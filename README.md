# Medical RAG Chatbot

Evidence-grounded medical Q and A over your own PDFs, built with a clean RAG pipeline and production-ready CI/CD hooks.

## Highlights
- End-to-end delivery: ingestion, vector search, LLM inference, and a working web UI.
- MLOps readiness: Dockerized app, Jenkins pipeline, Trivy scan, and AWS ECR/App Runner deployment flow.
- Clear, auditable answers: retrieval-first flow with a tight prompt for concise responses.

## What it does
- Loads medical PDFs from `data`.
- Splits and embeds text with `sentence-transformers/all-MiniLM-L6-v2`.
- Stores and retrieves context from FAISS at `vectorstore/db_faiss`.
- Answers questions using Hugging Face Inference (Mistral-7B-Instruct-v0.3).
- Serves a simple chat UI via Flask.

## Architecture
1) PDFs -> 2) Chunking -> 3) Embeddings -> 4) FAISS -> 5) RetrievalQA -> 6) LLM -> 7) Flask UI

## Quickstart (local)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .

export HF_TOKEN="your_huggingface_token"

# Build the vectorstore from your PDFs
python app/components/data_loader.py

# Run the app
python app/application.py
```
Open `http://localhost:5000` and ask a medical question.

## Docker
```bash
docker build -t medical-rag .

# Build the vectorstore inside a container
docker run --rm -it \
  -e HF_TOKEN="your_huggingface_token" \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/vectorstore:/app/vectorstore" \
  medical-rag \
  python app/components/data_loader.py

# Run the app
docker run --rm -p 5000:5000 \
  -e HF_TOKEN="your_huggingface_token" \
  -v "$(pwd)/vectorstore:/app/vectorstore" \
  medical-rag
```

## Configuration
- `HF_TOKEN` is required for Hugging Face inference.
- Model and data paths are defined in `app/config/config.py`.

## CI/CD and deployment
This repo includes a Jenkins pipeline that builds, scans with Trivy, pushes to AWS ECR, and triggers AWS App Runner. See `Jenkinsfile` for the pipeline steps.

## Repo layout
- `app`: Flask app and RAG components.
- `data`: PDF sources.
- `vectorstore`: FAISS index output.
- `Dockerfile`: Container build.
- `Jenkinsfile`: CI/CD pipeline.

## Notes
- This project is for information retrieval and demo purposes only. It is not medical advice.
- Ensure your PDFs are compliant and approved for use.
