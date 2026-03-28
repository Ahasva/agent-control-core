from __future__ import annotations

import json
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from agent_control_core.llm.client import get_openai_client
from agent_control_core.settings import Settings

T = TypeVar("T", bound=BaseModel)


def call_structured_model(
    *,
    settings: Settings,
    model: str,
    system_prompt: str,
    user_input: str,
    response_model: Type[T],
) -> T:
    client = get_openai_client(settings)

    schema = response_model.model_json_schema()

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": response_model.__name__,
                "schema": schema,
            }
        },
    )

    raw_text = response.output_text
    if not raw_text:
        raise ValueError("Model returned empty output.")

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {raw_text}") from exc

    try:
        return response_model.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"Structured output validation failed: {exc}") from exc