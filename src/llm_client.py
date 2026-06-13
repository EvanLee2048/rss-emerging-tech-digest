"""OpenAI-compatible LLM client for digest pipeline calls.

Supports any OpenAI-compatible API endpoint (OpenAI, OpenRouter, vLLM,
local LLMs, etc.). Configured via LLM_API_KEY and LLM_BASE_URL env vars.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMClient:
    """Minimal OpenAI-compatible chat completion client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 120,
    ) -> None:
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = (
            base_url
            or os.environ.get("LLM_BASE_URL")
            or "https://api.deepseek.com/v1"
        ).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", "deepseek-v4-flash")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY not set. Provide via constructor or "
                "LLM_API_KEY environment variable."
            )

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            system_prompt: System-level instructions.
            user_prompt: User message content.
            temperature: Override the instance default.
            max_tokens: Override the instance default.
            response_format: Optional format spec (e.g. {"type": "json_object"}).

        Returns:
            The response text content.

        Raises:
            RuntimeError: On API error or unexpected response.
        """
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            body["response_format"] = response_format

        data = json.dumps(body).encode("utf-8")
        req = Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Hermes-Digest/1.0",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as e:
            raise RuntimeError(f"LLM API request failed: {e}") from e

        choices = result.get("choices", [])
        if not choices:
            raise RuntimeError(
                f"LLM API returned no choices: {json.dumps(result, indent=2)}"
            )
        return choices[0].get("message", {}).get("content", "").strip()

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Union[dict, list]:
        """Send a chat completion and parse the response as JSON.

        Uses the json_object response format to guarantee valid JSON output.
        """
        text = self.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        return json.loads(text)
