from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

import json
import re
from typing import Any, Dict

from app.components.llm import load_llm
from app.components.vector_store import load_vector_store
from app.config.config import HUGGINGFACE_REPO_ID, HF_TOKEN, MEDICAL_DISCLAIMER, RETRIEVAL_K
from app.common.logger import get_logger
from app.common.custom_exception import CustomException

logger = get_logger(__name__)

CUSTOM_PROMPT_TEMPLATE = """
You are a careful medical assistant. Use ONLY the information provided in the CONTEXT to answer the QUESTION.

Rules:
1) If the answer is not explicitly supported by the CONTEXT, set "answer" to "Not found in PDFs".
2) Do NOT make up facts, numbers, drug dosages, or diagnoses.
3) Keep the answer clear and concise.
4) Use the exact disclaimer string provided.

Return ONLY a valid JSON object with this schema (no markdown, no extra keys):
{{
  "answer": string,
  "evidence": [string],
  "disclaimer": string
}}

- "evidence" must be 1-3 short quotes or paraphrases grounded in the CONTEXT.
- If "answer" is "Not found in PDFs", set "evidence" to [].

CONTEXT:
{context}

QUESTION:
{input}

DISCLAIMER (use this exact text):
{disclaimer}
"""


def set_custom_prompt() -> PromptTemplate:
    return PromptTemplate(
        template=CUSTOM_PROMPT_TEMPLATE,
        input_variables=["context", "input", "disclaimer"],
    )


def create_qa_chain(k: int = RETRIEVAL_K):
    """
    LCEL RAG chain output:
      {"answer": str, "evidence": list[str], "disclaimer": str}
    """
    try:
        logger.info("Loading vector store")
        db = load_vector_store()
        if db is None:
            raise CustomException("Vector store not present or empty", None)

        retriever = db.as_retriever(search_kwargs={"k": k})

        logger.info("Loading LLM")
        llm = load_llm(huggingface_repo_id=HUGGINGFACE_REPO_ID, hf_token=HF_TOKEN)
        if llm is None:
            raise CustomException("LLM not loaded", None)

        prompt = set_custom_prompt()

        def _format_docs(docs) -> str:
            return "\n\n".join(getattr(d, "page_content", str(d)) for d in (docs or []))

        def _parse_llm_json(text: str) -> Dict[str, Any]:
            raw = (text or "").strip()

            # remove ```json fences if any
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)

            try:
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    raise ValueError("LLM output JSON is not an object")
            except Exception:
                # safe fallback (no hallucinations)
                return {
                    "answer": "Not found in PDFs",
                    "evidence": [],
                    "disclaimer": MEDICAL_DISCLAIMER,
                }

            answer = obj.get("answer", "")
            evidence = obj.get("evidence", [])
            disclaimer = obj.get("disclaimer", MEDICAL_DISCLAIMER)

            if not isinstance(answer, str):
                answer = str(answer)

            if not isinstance(evidence, list):
                evidence = []
            evidence = [str(x) for x in evidence][:3]

            if not isinstance(disclaimer, str):
                disclaimer = MEDICAL_DISCLAIMER

            if answer.strip() == "Not found in PDFs":
                evidence = []

            return {
                "answer": answer.strip(),
                "evidence": evidence,
                "disclaimer": disclaimer,
            }

        rag_chain = (
            {
                "context": itemgetter("input") | retriever | _format_docs,
                "input": itemgetter("input"),
                "disclaimer": RunnableLambda(lambda _: MEDICAL_DISCLAIMER),
            }
            | prompt
            | llm
            | StrOutputParser()
            | RunnableLambda(_parse_llm_json)
        )

        logger.info("Successfully created LCEL RAG chain")
        return rag_chain

    except Exception as e:
        logger.error("Failed to make LCEL RAG chain", exc_info=True)
        raise CustomException("Failed to make LCEL RAG chain", e)