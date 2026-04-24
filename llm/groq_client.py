import logging
import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Explicitly load from project root .env (not llm/.env)
_root_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_root_env, override=True)

logger = logging.getLogger(__name__)
_GROQ_CLIENT: Groq | None = None


def get_groq_client() -> Groq:
    """
    Return a configured Groq API client.
    Reads GROQ_API_KEY from .env file.
    """
    global _GROQ_CLIENT
    if _GROQ_CLIENT is not None:
        return _GROQ_CLIENT

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment. "
            "Please add it to your .env file."
        )
    _GROQ_CLIENT = Groq(
        api_key=api_key,
        timeout=float(os.getenv("GROQ_TIMEOUT_SEC", "45")),
        max_retries=int(os.getenv("GROQ_MAX_RETRIES", "2")),
    )
    return _GROQ_CLIENT


def call_groq(
    system_prompt: str,
    user_prompt  : str,
    model        : str   = None,
    temperature  : float = 0.3,
    max_tokens   : int   = 2048
) -> str:
    """
    Call Groq API with system and user prompts.
    Returns the response text string.
    """
    if model is None:
        model = os.getenv(
            "GROQ_GENERATOR_MODEL",
            "deepseek-r1-distill-llama-70b"
        )

    logger.info(
        f"Calling Groq API — "
        f"model: {model}, "
        f"max_tokens: {max_tokens}"
    )

    try:
        client   = get_groq_client()
        response = client.chat.completions.create(
            model       = model,
            messages    = [
                {
                    "role"   : "system",
                    "content": system_prompt
                },
                {
                    "role"   : "user",
                    "content": user_prompt
                }
            ],
            temperature = temperature,
            max_tokens  = max_tokens,
        )

        result = response.choices[0].message.content
        logger.info(
            f"Groq API response received. "
            f"Length: {len(result)} chars"
        )
        return result

    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise