import hashlib
import json
import math
import re
from typing import List, Tuple

from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

from app.common.logger import get_logger
from app.components.embeddings import get_embedding_model
from app.components.llm import load_llm
from app.components.retriever import set_custom_prompt
from app.components.vector_store import load_parent_docs, load_vector_store
from app.components.web_search import search_web
from app.config.config import (
    DEFAULT_ROUTE,
    HUGGINGFACE_REPO_ID,
    HF_TOKEN,
    CONTEXT_COMPRESSION_ENABLED,
    CONTEXT_DOC_MAX_CHARS,
    CONTEXT_MAX_CHARS,
    CONTEXT_MAX_SENTENCES_PER_DOC,
    CONTEXT_MAX_SENTENCES_TOTAL,
    CONTEXT_SENTENCE_CANDIDATE_LIMIT,
    CROSS_ENCODER_DEVICE,
    CROSS_ENCODER_MODEL,
    MEDICAL_DISCLAIMER,
    MULTI_QUERY_COUNT,
    MULTI_QUERY_ENABLED,
    RERANK_CANDIDATES,
    RERANK_ENABLED,
    RERANK_MAX_CHARS,
    RERANK_TOP_N,
    RETRIEVAL_FETCH_K,
    RETRIEVAL_K,
    RETRIEVAL_MMR_LAMBDA,
    RETRIEVAL_MIN_RELEVANCE,
)

logger = get_logger(__name__)

_VECTOR_STORE = None
_LLM = None
_EMBEDDINGS = None
_RERANKER = None
_PARENT_DOCS = None


def _get_vector_store():
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        _VECTOR_STORE = load_vector_store()
    return _VECTOR_STORE


def _get_llm():
    global _LLM
    if _LLM is None:
        _LLM = load_llm(huggingface_repo_id=HUGGINGFACE_REPO_ID, hf_token=HF_TOKEN)
    return _LLM


def _get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = get_embedding_model()
    return _EMBEDDINGS


def _get_reranker():
    global _RERANKER
    if _RERANKER is None:
        _RERANKER = CrossEncoder(CROSS_ENCODER_MODEL, device=CROSS_ENCODER_DEVICE)
    return _RERANKER


def _get_parent_docs():
    global _PARENT_DOCS
    if _PARENT_DOCS is None:
        _PARENT_DOCS = load_parent_docs()
        if not _PARENT_DOCS:
            logger.warning("Parent doc store is empty or missing.")
    return _PARENT_DOCS


def _format_docs(docs) -> str:
    parts = []
    for doc in docs:
        if isinstance(doc, str):
            text = doc
        else:
            text = getattr(doc, "page_content", str(doc))
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _summarize_doc(doc) -> dict:
    metadata = getattr(doc, "metadata", {}) or {}
    return {
        "source": metadata.get("source"),
        "page": metadata.get("page"),
        "parent_id": metadata.get("parent_id"),
        "parent_index": metadata.get("parent_index"),
        "child_index": metadata.get("child_index"),
        "chunk_type": metadata.get("chunk_type"),
    }


def _log_doc_sample(label: str, docs: List[Document], limit: int = 3):
    if not docs:
        logger.info("%s: 0 docs", label)
        return
    sample = [_summarize_doc(doc) for doc in docs[:limit]]
    logger.info("%s: %s docs, sample=%s", label, len(docs), sample)


def _distance_to_relevance(score) -> float:
    try:
        return 1.0 / (1.0 + float(score))
    except (TypeError, ValueError):
        return 0.0


def _retrieve_with_scores(query: str, db, k: int):
    try:
        results = db.similarity_search_with_relevance_scores(query, k=k)
        if results is None:
            results = []
        return results, "relevance"
    except Exception:
        logger.info("Relevance scores unavailable; falling back to distance scores.")

    results = db.similarity_search_with_score(query, k)
    normalized = [(doc, _distance_to_relevance(score)) for doc, score in results]
    return normalized, "distance"


def _is_retrieval_weak(best_score: float, min_relevance: float) -> bool:
    try:
        return float(best_score) < min_relevance
    except (TypeError, ValueError):
        return True


def build_fallback_payload() -> dict:
    return {
        "answer": "Not found in PDFs",
        "evidence": [],
        "disclaimer": MEDICAL_DISCLAIMER,
    }


def _parse_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _normalize_payload(payload: dict):
    if not isinstance(payload, dict):
        return None

    expected_keys = {"answer", "evidence", "disclaimer"}
    if set(payload.keys()) != expected_keys:
        return None

    answer = payload.get("answer")
    evidence = payload.get("evidence")
    disclaimer = payload.get("disclaimer")

    if not isinstance(answer, str) or not isinstance(disclaimer, str):
        return None
    if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
        return None

    answer = answer.strip()
    evidence = [item.strip() for item in evidence if item.strip()][:3]

    if not answer:
        answer = "Not found in PDFs"

    normalized_answer = answer.strip().lower().rstrip(".")
    if normalized_answer == "not found in pdfs":
        answer = "Not found in PDFs"
        evidence = []

    return {
        "answer": answer,
        "evidence": evidence,
        "disclaimer": MEDICAL_DISCLAIMER,
    }


def _is_not_found(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    answer = payload.get("answer")
    if not isinstance(answer, str):
        return False
    normalized = answer.strip().lower().rstrip(".")
    return normalized == "not found in pdfs"


def _build_evidence_from_docs(docs) -> List[str]:
    evidence = []
    for doc in docs:
        content = getattr(doc, "page_content", "")
        if not content:
            continue
        snippet = " ".join(content.split())
        if len(snippet) > 240:
            snippet = f"{snippet[:237].rstrip()}..."
        evidence.append(snippet)
        if len(evidence) >= 3:
            break
    return evidence


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _preview_text(text: str, max_chars: int = 600) -> str:
    if not text:
        return ""
    return _truncate_text(" ".join(text.split()), max_chars)


def _normalize_vector(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _split_sentences(text: str) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _doc_key(doc) -> str:
    metadata = getattr(doc, "metadata", {}) or {}
    parent_id = metadata.get("parent_id")
    if parent_id:
        return str(parent_id)
    source = metadata.get("source")
    page = metadata.get("page")
    chunk_index = (
        metadata.get("parent_index")
        if metadata.get("parent_index") is not None
        else metadata.get("child_index")
    )
    if source or page or chunk_index is not None:
        return f"{source}:{page}:{chunk_index}"
    content = getattr(doc, "page_content", str(doc))
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def _dedupe_docs(docs: List[Document]) -> List[Document]:
    seen = set()
    unique_docs = []
    for doc in docs:
        key = _doc_key(doc)
        if key in seen:
            continue
        seen.add(key)
        unique_docs.append(doc)
    return unique_docs


def _map_children_to_parents(docs: List[Document]) -> List[Document]:
    parent_docs = _get_parent_docs()
    if not parent_docs:
        return docs

    mapped = []
    for doc in docs:
        metadata = getattr(doc, "metadata", {}) or {}
        parent_id = metadata.get("parent_id")
        if parent_id and parent_id in parent_docs:
            mapped.append(parent_docs[parent_id])
        else:
            mapped.append(doc)
    return mapped


def _expand_queries(question: str, llm) -> List[str]:
    if not MULTI_QUERY_ENABLED or MULTI_QUERY_COUNT <= 0:
        return [question]

    prompt = (
        "You are a search query generator. Create "
        f"{MULTI_QUERY_COUNT} alternative search queries that rephrase the question. "
        "Return ONLY a JSON array of strings, no extra text.\n\n"
        f"Question: {question}"
    )

    try:
        raw = llm.invoke(prompt)
    except Exception as e:
        logger.warning("Multi-query expansion failed: %s", e)
        return [question]
    text = raw if isinstance(raw, str) else str(raw)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            queries = [str(item).strip() for item in parsed]
        else:
            queries = []
    except Exception:
        queries = []
        for line in text.splitlines():
            cleaned = line.strip().lstrip("-").lstrip("*").strip()
            cleaned = re.sub(r"^\d+[\.)]\s*", "", cleaned)
            if cleaned:
                queries.append(cleaned)

    combined = [question]
    seen = {question.strip().lower()}
    for query in queries:
        normalized = query.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        combined.append(query.strip())

    return combined[: max(1, MULTI_QUERY_COUNT + 1)]


def _mmr_search(db, query: str) -> List[Document]:
    try:
        return db.max_marginal_relevance_search(
            query,
            k=RETRIEVAL_K,
            fetch_k=RETRIEVAL_FETCH_K,
            lambda_mult=RETRIEVAL_MMR_LAMBDA,
        )
    except Exception:
        logger.info("MMR not available; falling back to similarity search.")
        results, _ = _retrieve_with_scores(query, db, RETRIEVAL_K)
        return [doc for doc, _ in results]


def _best_relevance_score(db, queries: List[str]) -> Tuple[float, str]:
    best_score = 0.0
    score_mode = "relevance"
    for query in queries:
        results, mode = _retrieve_with_scores(query, db, 1)
        score_mode = mode
        if results:
            best_score = max(best_score, results[0][1])
    return best_score, score_mode


def _rerank_documents(question: str, docs: List[Document]) -> List[Document]:
    if not RERANK_ENABLED or not docs:
        return docs

    reranker = _get_reranker()
    candidates = docs[:RERANK_CANDIDATES]
    if not candidates:
        return docs
    pairs = []
    for doc in candidates:
        content = getattr(doc, "page_content", str(doc))
        pairs.append((question, _truncate_text(content, RERANK_MAX_CHARS)))

    scores = reranker.predict(pairs)
    scored = sorted(zip(scores, candidates), key=lambda item: item[0], reverse=True)
    ranked = [doc for _, doc in scored]
    remaining = docs[len(candidates) :]
    return ranked + remaining


def _compress_documents(question: str, docs: List[Document]) -> List[Document]:
    if not CONTEXT_COMPRESSION_ENABLED or not docs:
        return docs

    embedder = _get_embeddings()
    query_vec = _normalize_vector(embedder.embed_query(question))
    compressed_docs = []
    total_sentences = 0

    for doc in docs:
        content = getattr(doc, "page_content", "")
        if not content:
            continue

        sentences = _split_sentences(content)
        if CONTEXT_SENTENCE_CANDIDATE_LIMIT > 0:
            sentences = sentences[:CONTEXT_SENTENCE_CANDIDATE_LIMIT]

        if not sentences:
            continue

        if len(sentences) == 1:
            selected = sentences
        else:
            sentence_vectors = embedder.embed_documents(sentences)
            scores = [
                _cosine_similarity(query_vec, _normalize_vector(vec))
                for vec in sentence_vectors
            ]
            top_indices = sorted(
                range(len(sentences)), key=lambda i: scores[i], reverse=True
            )[:CONTEXT_MAX_SENTENCES_PER_DOC]
            top_indices.sort()
            selected = [sentences[i] for i in top_indices]

        if total_sentences + len(selected) > CONTEXT_MAX_SENTENCES_TOTAL:
            remaining = max(CONTEXT_MAX_SENTENCES_TOTAL - total_sentences, 0)
            selected = selected[:remaining]

        total_sentences += len(selected)
        if not selected:
            break

        compressed_text = " ".join(selected)
        compressed_text = _truncate_text(compressed_text, CONTEXT_DOC_MAX_CHARS)
        compressed_docs.append(
            Document(page_content=compressed_text, metadata=getattr(doc, "metadata", {}))
        )

        if total_sentences >= CONTEXT_MAX_SENTENCES_TOTAL:
            break

    return compressed_docs


def _build_context(docs: List[Document]) -> str:
    context = _format_docs(docs)
    return _truncate_text(context, CONTEXT_MAX_CHARS)


def _retrieve_pdf_documents(question: str) -> Tuple[List[Document], float, str]:
    db = _get_vector_store()
    if db is None:
        logger.warning("Vector store not available.")
        return [], 0.0, "none"

    llm = _get_llm()
    queries = _expand_queries(question, llm)
    logger.info("Multi-query: %s queries generated.", len(queries))
    if len(queries) > 1:
        logger.info("Multi-query variants: %s", queries)
    best_score, score_mode = _best_relevance_score(db, queries)
    logger.info("Best retrieval score: %.4f (mode=%s)", best_score, score_mode)

    all_docs = []
    for query in queries:
        docs = _mmr_search(db, query)
        logger.info("MMR search returned %s docs for query.", len(docs))
        all_docs.extend(docs)

    deduped = _dedupe_docs(all_docs)
    _log_doc_sample("Retrieved child docs", deduped)
    parent_docs = _map_children_to_parents(deduped)
    parent_docs = _dedupe_docs(parent_docs)
    _log_doc_sample("Mapped parent docs", parent_docs)
    reranked = _rerank_documents(question, parent_docs)
    _log_doc_sample("Reranked parent docs", reranked)
    reranked = reranked[: max(RETRIEVAL_K, RERANK_TOP_N)]
    compressed = _compress_documents(question, reranked)
    _log_doc_sample("Compressed docs", compressed)
    return compressed, best_score, score_mode


def _answer_from_docs(question: str, docs: List[Document]) -> dict:
    prompt = set_custom_prompt()
    context = _build_context(docs)
    logger.info("Context length: %s chars", len(context))
    logger.info("Context preview: %s", _preview_text(context, 600))
    llm = _get_llm()
    prompt_text = prompt.format(
        context=context, input=question, disclaimer=MEDICAL_DISCLAIMER
    )

    raw_output = llm.invoke(prompt_text)
    raw_text = raw_output if isinstance(raw_output, str) else str(raw_output)
    logger.info("LLM raw output preview: %s", _preview_text(raw_text, 600))
    parsed = _parse_json(raw_text)
    normalized = _normalize_payload(parsed)

    if normalized is None:
        logger.warning("LLM response failed JSON validation. Coercing output.")
        normalized = _coerce_payload(raw_text, docs)
    else:
        logger.info(
            "Normalized answer: %s (evidence=%s)",
            normalized.get("answer"),
            len(normalized.get("evidence", [])),
        )

    return normalized


def _coerce_payload(raw_text: str, docs) -> dict:
    answer = raw_text.strip()
    if not answer:
        answer = "Unable to answer based on the provided PDFs."

    return {
        "answer": answer,
        "evidence": _build_evidence_from_docs(docs),
        "disclaimer": MEDICAL_DISCLAIMER,
    }


def serialize_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=True)


def generate_guardrailed_response(question: str, route: str = DEFAULT_ROUTE) -> str:
    route_value = (route or DEFAULT_ROUTE).strip().lower()
    if route_value not in {"pdf", "web", "hybrid"}:
        route_value = DEFAULT_ROUTE
    logger.info("Guardrails request route=%s question=%s", route_value, question)

    if route_value in {"pdf", "hybrid"}:
        docs, best_score, score_mode = _retrieve_pdf_documents(question)
        if not docs:
            logger.info("No docs retrieved from PDFs.")
            return serialize_payload(build_fallback_payload())
        if _is_retrieval_weak(best_score, RETRIEVAL_MIN_RELEVANCE):
            logger.info(
                "Retrieval weak (mode=%s, score=%.4f, min_relevance=%s).",
                score_mode,
                best_score,
                RETRIEVAL_MIN_RELEVANCE,
            )
            if route_value == "pdf":
                return serialize_payload(build_fallback_payload())

            try:
                web_docs = search_web(question)
            except Exception as e:
                logger.warning("Web fallback failed: %s", e)
                return serialize_payload(build_fallback_payload())

            if not web_docs:
                logger.info("Web fallback returned 0 docs.")
                return serialize_payload(build_fallback_payload())

            web_docs = _compress_documents(question, _rerank_documents(question, web_docs))
            if not web_docs:
                logger.info("Web docs empty after compression.")
                return serialize_payload(build_fallback_payload())
            payload = _answer_from_docs(question, web_docs)
            return serialize_payload(payload)

        web_docs_added = False
        if route_value == "hybrid":
            try:
                web_docs = search_web(question)
                if web_docs:
                    web_docs = _compress_documents(
                        question, _rerank_documents(question, web_docs)
                    )
                    if web_docs:
                        docs = docs + web_docs
                        logger.info("Hybrid route added %s web docs.", len(web_docs))
                        web_docs_added = True
            except Exception as e:
                logger.warning("Web enrichment failed: %s", e)

        payload = _answer_from_docs(question, docs)
        if route_value == "hybrid" and _is_not_found(payload) and not web_docs_added:
            logger.info("Hybrid answer not found; attempting web fallback.")
            try:
                web_docs = search_web(question)
            except Exception as e:
                logger.warning("Web fallback failed: %s", e)
                return serialize_payload(payload)

            if web_docs:
                web_docs = _compress_documents(
                    question, _rerank_documents(question, web_docs)
                )
                if web_docs:
                    payload = _answer_from_docs(question, web_docs)

        return serialize_payload(payload)

    try:
        web_docs = search_web(question)
    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return serialize_payload(build_fallback_payload())

    if not web_docs:
        logger.info("Web search returned 0 docs.")
        return serialize_payload(build_fallback_payload())

    web_docs = _compress_documents(question, _rerank_documents(question, web_docs))
    if not web_docs:
        logger.info("Web docs empty after compression.")
        return serialize_payload(build_fallback_payload())
    payload = _answer_from_docs(question, web_docs)
    return serialize_payload(payload)
