from openai import OpenAI

from agent_control_core.settings import Settings


def get_openai_client(settings: Settings) -> OpenAI:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=settings.openai_api_key)