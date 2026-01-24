from __future__ import annotations

from typing import Optional
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from langchain_core.runnables import RunnableLambda

from app.config.config import (
    HF_PROVIDER,
    HF_MAX_TOKENS,
    HF_TEMPERATURE,
    HF_TOP_P,
    HF_TIMEOUT,
)
from app.common.logger import get_logger
from app.common.custom_exception import CustomException

logger = get_logger(__name__)


def _to_float(x, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _to_int(x, default: int) -> int:
    try:
        return int(x)
    except Exception:
        return default


def load_llm(huggingface_repo_id: str, hf_token: Optional[str]):
    """
    Returns a Runnable that takes a string prompt and returns a string completion.

    Key behavior:
    - If HF_PROVIDER is empty OR "hf-inference": use direct HF Inference API (no router).
    - Else: use HF router with provider (e.g., together).
    - Try chat_completion; if it fails, fallback to text_generation.
    """
    try:
        if not hf_token:
            raise CustomException("HF token missing. Set HF_TOKEN in .env", None)

        provider = (HF_PROVIDER or "").strip()
        max_tokens = _to_int(HF_MAX_TOKENS, 512)
        temperature = _to_float(HF_TEMPERATURE, 0.2)
        top_p = _to_float(HF_TOP_P, 0.9)
        timeout = _to_int(HF_TIMEOUT, 120)

        # IMPORTANT:
        # - Router mode: provider + model + api_key
        # - Direct mode: model + token
        if provider and provider.lower() != "hf-inference":
            logger.info(f"Loading HF routed client provider={provider} model={huggingface_repo_id}")
            client = InferenceClient(
                provider=provider,
                model=huggingface_repo_id,
                api_key=hf_token,
                timeout=timeout,
            )
        else:
            logger.info(f"Loading HF direct client model={huggingface_repo_id}")
            client = InferenceClient(
                model=huggingface_repo_id,
                token=hf_token,
                timeout=timeout,
            )

        def _call_llm(prompt: object) -> str:
            prompt_text = str(prompt)

            # 1) Try chat completion
            try:
                out = client.chat_completion(
                    messages=[{"role": "user", "content": prompt_text}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                return out.choices[0].message.content
            except Exception as e:
                logger.warning(f"chat_completion failed, falling back to text_generation: {e}")

            # 2) Fallback: text generation (returns str by default)
            try:
                gen = client.text_generation(
                    prompt_text,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    return_full_text=False,
                )
                if isinstance(gen, str):
                    return gen
                return getattr(gen, "generated_text", str(gen))
            except Exception as e2:
                raise CustomException("HF inference failed (chat_completion + text_generation)", e2)

        return RunnableLambda(_call_llm)

    except Exception as e:
        err = CustomException("Failed to load HF chat LLM", e)
        logger.error(str(err))
        raise err