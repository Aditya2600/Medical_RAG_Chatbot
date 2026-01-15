import os
from huggingface_hub import InferenceClient
from langchain_core.runnables import RunnableLambda

from app.common.logger import get_logger
from app.common.custom_exception import CustomException
from app.config.config import HF_TOKEN, HUGGINGFACE_REPO_ID, HF_PROVIDER

logger = get_logger(__name__)


def _to_text(x) -> str:
    """Convert LangChain PromptValue (StringPromptValue) -> plain text."""
    if isinstance(x, str):
        return x
    if hasattr(x, "to_string") and callable(getattr(x, "to_string")):
        return x.to_string()
    return str(x)


def load_llm(huggingface_repo_id: str = None, hf_token: str = None):
    """
    Returns a LangChain-compatible Runnable for LCEL pipelines.
    Works with HF Inference Providers + Together using chat_completion (conversational).
    """
    try:
        model_id = huggingface_repo_id or HUGGINGFACE_REPO_ID
        token = hf_token or HF_TOKEN

        if not token:
            raise CustomException("HF token missing. Set HF_TOKEN in .env", None)

        client = InferenceClient(
            provider=HF_PROVIDER,
            model=model_id,
            api_key=token,
        )

        def _call_llm(prompt_value) -> str:
            prompt_text = _to_text(prompt_value)  # ✅ IMPORTANT FIX
            out = client.chat_completion(
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=512,
            )
            return out.choices[0].message.content

        logger.info(f"Loaded HF chat LLM via provider={HF_PROVIDER}, model={model_id}")
        return RunnableLambda(_call_llm)

    except Exception as e:
        err = CustomException("Failed to load HF chat LLM", e)
        logger.error(str(err))
        raise err