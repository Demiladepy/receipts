"""Chat client. OpenAI by default; any OpenAI-compatible endpoint via OPENAI_BASE_URL
(the neatHack LiteLLM proxy, for example). Calls are traced through neatlogs.wrap."""

import os
from dataclasses import dataclass

import neatlogs

DEFAULT_MODEL = "gpt-4.1-mini"
# USD per 1M tokens. Override with RECEIPTS_PRICE_IN / RECEIPTS_PRICE_OUT for another model.
DEFAULT_PRICE_IN = 0.40
DEFAULT_PRICE_OUT = 1.60


def model_name() -> str:
    return os.environ.get("RECEIPTS_MODEL", DEFAULT_MODEL)


@dataclass(slots=True)
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def add(self, usage) -> None:
        self.calls += 1
        if usage is None:
            return
        self.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
        self.completion_tokens += getattr(usage, "completion_tokens", 0) or 0

    def cost_usd(self) -> float:
        price_in = float(os.environ.get("RECEIPTS_PRICE_IN", DEFAULT_PRICE_IN))
        price_out = float(os.environ.get("RECEIPTS_PRICE_OUT", DEFAULT_PRICE_OUT))
        return (self.prompt_tokens * price_in + self.completion_tokens * price_out) / 1_000_000

    def as_json(self) -> dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd(), 6),
        }


def make_client():
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )
    try:
        return neatlogs.wrap(client)
    except Exception:
        return client


_NO_TEMPERATURE: set[str] = set()


def complete(client, messages: list[dict], tools: list[dict]):
    model = model_name()
    kwargs = {"model": model, "messages": messages, "tools": tools, "tool_choice": "auto"}
    if model not in _NO_TEMPERATURE:
        kwargs["temperature"] = 0
    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        if "temperature" in str(exc) and "temperature" in kwargs:
            _NO_TEMPERATURE.add(model)
            kwargs.pop("temperature")
            return client.chat.completions.create(**kwargs)
        raise
