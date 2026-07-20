"""
LLM adapters for clinical reasoning.

Supports:
- OpenAI-compatible API
- Local llama.cpp
- Disabled (returns not_configured)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from src.backend.reasoning.models import ClinicalReasoningResult

logger = logging.getLogger(__name__)


class LLMResult:
    """Result from an LLM call."""
    def __init__(self, success: bool, content: str = "", error: str = "",
                 model: str = "", token_usage: Optional[dict] = None,
                 latency_ms: float = 0.0):
        self.success = success
        self.content = content
        self.error = error
        self.model = model
        self.token_usage = token_usage or {}
        self.latency_ms = latency_ms


class LLMAdapter:
    """Base LLM adapter."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.provider = "unknown"
        self.model = self.config.get("model", "unknown")
        self.temperature = self.config.get("temperature", 0.1)
        self.seed = self.config.get("seed", 42)

    async def generate(self, prompt: str, system_prompt: str = "") -> LLMResult:
        """Generate text from the LLM."""
        raise NotImplementedError

    @property
    def is_available(self) -> bool:
        return False


class OpenAILikeAdapter(LLMAdapter):
    """
    Adapter for OpenAI-compatible APIs.
    Uses OPENAI_API_KEY or custom endpoint from env.
    """

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.provider = "openai_compatible"
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.api_base = self.config.get("api_base", "https://api.openai.com/v1")
        self.model = self.config.get("model", "gpt-4")

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, system_prompt: str = "") -> LLMResult:
        """Call OpenAI-compatible chat completion API."""
        if not self.is_available:
            return LLMResult(success=False, content="", error="API key not configured")

        import time
        import httpx

        start = time.monotonic()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "seed": self.seed,
                    },
                )
                latency = (time.monotonic() - start) * 1000

                if resp.status_code != 200:
                    return LLMResult(
                        success=False, error=f"API returned {resp.status_code}",
                        model=self.model, latency_ms=latency,
                    )

                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})

                return LLMResult(
                    success=True, content=content,
                    model=self.model, token_usage=usage, latency_ms=latency,
                )

        except httpx.TimeoutException:
            return LLMResult(success=False, error="Request timed out", model=self.model)
        except Exception as e:
            return LLMResult(success=False, error=str(e), model=self.model)


class LocalLLMAdapter(LLMAdapter):
    """Adapter for local llama.cpp server."""

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.provider = "local_llamacpp"
        self.api_base = self.config.get("api_base", "http://localhost:8080/v1")
        self.model = self.config.get("model", "local")

    @property
    def is_available(self) -> bool:
        return True  # Always try; will fail gracefully if server not running

    async def generate(self, prompt: str, system_prompt: str = "") -> LLMResult:
        import time
        import httpx

        start = time.monotonic()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.api_base}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                    },
                )
                latency = (time.monotonic() - start) * 1000

                if resp.status_code != 200:
                    return LLMResult(
                        success=False, error=f"Local LLM returned {resp.status_code}",
                        model=self.model, latency_ms=latency,
                    )

                data = resp.json()
                content = data.get("choices", [{}])[0].get("text", data.get("choices", [{}])[0].get("message", {}).get("content", ""))
                return LLMResult(success=True, content=content, model=self.model, latency_ms=latency)

        except Exception as e:
            return LLMResult(success=False, error=f"Local LLM unavailable: {e}", model=self.model)


class DisabledLLMAdapter(LLMAdapter):
    """Adapter that returns not_configured for all requests."""

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self.provider = "disabled"

    @property
    def is_available(self) -> bool:
        return False

    async def generate(self, prompt: str, system_prompt: str = "") -> LLMResult:
        return LLMResult(
            success=False,
            content="",
            error="LLM not configured. Set OPENAI_API_KEY or configure local endpoint.",
            model="disabled",
        )


def get_llm_adapter(config: Optional[dict] = None) -> LLMAdapter:
    """
    Factory function: returns the appropriate LLM adapter based on config.
    """
    cfg = config or {}
    provider = cfg.get("provider", os.getenv("LLM_PROVIDER", "disabled"))

    if provider == "openai":
        return OpenAILikeAdapter(cfg)
    elif provider in ("local", "llamacpp"):
        return LocalLLMAdapter(cfg)
    else:
        return DisabledLLMAdapter(cfg)
