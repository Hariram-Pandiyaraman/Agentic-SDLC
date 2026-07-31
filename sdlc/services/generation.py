"""Ollama structured generation with validation, repair, and deterministic fallback."""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from sdlc.config import Settings
from sdlc.prompts import SYSTEM_PROMPT, render_prompt

T = TypeVar("T", bound=BaseModel)
ChatCallable = Callable[[list[dict[str, str]], dict], str]


@dataclass(frozen=True)
class GenerationResult(Generic[T]):
    value: T
    provider: str
    model: str
    prompt_task: str
    prompt_version: str
    attempts: int
    repair_used: bool
    fallback_used: bool
    latency_ms: int
    errors: tuple[str, ...]

    def metadata(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "prompt_task": self.prompt_task,
            "prompt_version": self.prompt_version,
            "attempts": self.attempts,
            "repair_used": self.repair_used,
            "fallback_used": self.fallback_used,
            "latency_ms": self.latency_ms,
            "errors": list(self.errors),
        }


class OllamaGenerationService:
    def __init__(
        self,
        settings: Settings,
        chat_callable: ChatCallable | None = None,
    ) -> None:
        self.settings = settings
        self._chat_callable = chat_callable or self._ollama_chat

    def generate(
        self,
        task: str,
        response_model: type[T],
        variables: dict,
        fallback: Callable[[], T],
    ) -> GenerationResult[T]:
        prompt, prompt_version = render_prompt(task, variables)
        started = time.perf_counter()
        errors: list[str] = []
        if not self.settings.use_ollama:
            return self._fallback_result(
                fallback,
                task,
                prompt_version,
                started,
                ("Ollama generation is disabled by configuration.",),
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        schema = response_model.model_json_schema()
        try:
            raw = self._chat_callable(messages, schema)
            return self._validated_result(
                raw, response_model, task, prompt_version, started, attempts=1
            )
        except (ValidationError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            repair_messages = [
                *messages,
                {"role": "assistant", "content": raw if "raw" in locals() else ""},
                {
                    "role": "user",
                    "content": (
                        "Repair the previous response. Return JSON only, matching the "
                        f"schema exactly. Validation error: {exc}"
                    ),
                },
            ]
            try:
                repaired = self._chat_callable(repair_messages, schema)
                result = self._validated_result(
                    repaired,
                    response_model,
                    task,
                    prompt_version,
                    started,
                    attempts=2,
                    repair_used=True,
                    errors=tuple(errors),
                )
                return result
            except Exception as repair_exc:
                errors.append(f"{type(repair_exc).__name__}: {repair_exc}")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

        return self._fallback_result(
            fallback, task, prompt_version, started, tuple(errors)
        )

    def _ollama_chat(self, messages: list[dict[str, str]], schema: dict) -> str:
        response = httpx.post(
            f"{self.settings.ollama_base_url}/api/chat",
            json={
                "model": self.settings.ollama_model,
                "messages": messages,
                "stream": False,
                "format": schema,
                "options": {"temperature": self.settings.ollama_temperature},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        return payload["message"]["content"]

    def _validated_result(
        self,
        raw: str,
        response_model: type[T],
        task: str,
        prompt_version: str,
        started: float,
        *,
        attempts: int,
        repair_used: bool = False,
        errors: tuple[str, ...] = (),
    ) -> GenerationResult[T]:
        value = response_model.model_validate_json(raw)
        return GenerationResult(
            value=value,
            provider="ollama",
            model=self.settings.ollama_model,
            prompt_task=task,
            prompt_version=prompt_version,
            attempts=attempts,
            repair_used=repair_used,
            fallback_used=False,
            latency_ms=int((time.perf_counter() - started) * 1000),
            errors=errors,
        )

    def _fallback_result(
        self,
        fallback: Callable[[], T],
        task: str,
        prompt_version: str,
        started: float,
        errors: tuple[str, ...],
    ) -> GenerationResult[T]:
        return GenerationResult(
            value=fallback(),
            provider="deterministic_template",
            model=self.settings.ollama_model,
            prompt_task=task,
            prompt_version=prompt_version,
            attempts=max(1, len(errors)),
            repair_used=len(errors) > 1,
            fallback_used=True,
            latency_ms=int((time.perf_counter() - started) * 1000),
            errors=errors,
        )

