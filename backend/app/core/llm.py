from langchain_openai import ChatOpenAI

from app.core.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_VISION_MODEL,
)


def get_chat_llm(temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=f"{DEEPSEEK_BASE_URL}/v1",
        model=DEEPSEEK_MODEL,
        temperature=temperature,
    )


def get_vision_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=f"{DEEPSEEK_BASE_URL}/v1",
        model=DEEPSEEK_VISION_MODEL,
        temperature=temperature,
    )
