from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

from app.components.llm import load_llm
from app.components.vector_store import load_vector_store
from app.config.config import HUGGINGFACE_REPO_ID, HF_TOKEN
from app.common.logger import get_logger
from app.common.custom_exception import CustomException

logger = get_logger(__name__)

CUSTOM_PROMPT_TEMPLATE = """
You are a helpful medical assistant. Use ONLY the information provided in the CONTEXT to answer the user's QUESTION.

Rules:
1) If the answer is not present in the CONTEXT, say: "I don't know based on the provided documents."
2) Do NOT make up facts, numbers, drug dosages, or diagnoses.
3) Keep the answer clear and concise.
4) If the user asks for medical advice/treatment, add a short safety note: "Please consult a qualified doctor for medical advice."

Return format:
- Answer: <your answer>
- Evidence: <1-3 short bullet points quoting or referencing the context>
- Disclaimer: <one line medical disclaimer>

CONTEXT:
{context}

QUESTION:
{input}

Now respond following the Return format exactly.
"""


def set_custom_prompt():
    """
    Builds the prompt used by the LLM.
    LCEL convention: use `input` as the user question key.
    """
    return PromptTemplate(
        template=CUSTOM_PROMPT_TEMPLATE,
        input_variables=["context", "input"],
    )


def create_qa_chain(k: int = 1):
    """
    Modern LCEL RAG chain using only `langchain_core` (no `langchain.chains` dependency).

    Call:
        chain = create_qa_chain()
        result = chain.invoke({"input": "your question"})
        answer = result["answer"]

    Returns:
        Runnable chain that outputs: {"answer": "<final text>"}
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

        logger.info("Building LCEL RAG chain (RunnableSequence)")
        prompt = set_custom_prompt()

        def _format_docs(docs):
            # Each doc is typically a LangChain Document with `.page_content`
            return "\n\n".join(getattr(d, "page_content", str(d)) for d in docs)

        # LCEL pipeline:
        # input(question) -> retriever -> docs -> format -> {context,input} -> prompt -> llm -> text -> {"answer": text}
        rag_chain = (
            {
                "context": itemgetter("input") | retriever | _format_docs,
                "input": itemgetter("input"),
            }
            | prompt
            | llm
            | StrOutputParser()
            | RunnableLambda(lambda text: {"answer": text})
        )

        logger.info("Successfully created LCEL RAG chain")
        return rag_chain

    except Exception as e:
        logger.error("Failed to make LCEL RAG chain", exc_info=True)
        raise CustomException("Failed to make LCEL RAG chain", e)
