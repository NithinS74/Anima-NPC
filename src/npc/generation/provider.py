"""One bounded chat-completions transport; no vendor SDK or automatic retries."""

import asyncio
import ipaddress
import json
from typing import Literal, Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import Field, SecretStr, ValidationError, model_validator

from npc.contracts.context import Contract, Identifier
from npc.contracts.dialogue import PromptPackage, ProviderReply


class ProviderFailure(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)  # never attach raw response/request/key


class ModelProvider(Protocol):
    async def generate(self, prompt: PromptPackage, timeout_s: float) -> ProviderReply: ...


class ProviderConfig(Contract):
    base_url: str = Field(min_length=1, max_length=2048, repr=False)
    model: Identifier
    api_key: SecretStr = Field(repr=False)
    response_format: Literal["json_object", "none"] = "json_object"
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high"] | None = None

    @model_validator(mode="after")
    def check_url(self) -> "ProviderConfig":
        parsed = urlsplit(self.base_url)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base URL must not contain credentials/query/fragment")
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            loopback = parsed.hostname == "localhost"
        if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
            raise ValueError("HTTPS required except for loopback local providers")
        if not self.api_key.get_secret_value().strip():
            raise ValueError("API key required (use a nonsecret placeholder for local runtimes)")
        return self


class ChatCompletionsProvider:
    def __init__(self, config: ProviderConfig, *, transport: httpx.AsyncBaseTransport | None = None):
        self.config = config
        self._transport = transport

    async def generate(self, prompt: PromptPackage, timeout_s: float) -> ProviderReply:
        if timeout_s <= 0:
            raise ProviderFailure("provider_timeout")
        payload = {"model": self.config.model, "messages": [item.model_dump() for item in prompt.messages],
                   "max_tokens": prompt.max_output_tokens, "stream": False}
        if self.config.response_format == "json_object":
            payload["response_format"] = {"type": "json_object"}
        if self.config.reasoning_effort is not None:
            payload["reasoning_effort"] = self.config.reasoning_effort
        try:
            # Absolute timeout additionally bounds trickle/drip responses.
            async with asyncio.timeout(timeout_s):
                async with httpx.AsyncClient(
                    transport=self._transport, timeout=httpx.Timeout(timeout_s),
                    follow_redirects=False, trust_env=False,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
                ) as client:
                    async with client.stream(
                        "POST", self.config.base_url.rstrip("/") + "/chat/completions",
                        headers={"Authorization": "Bearer " + self.config.api_key.get_secret_value()}, json=payload,
                    ) as response:
                        if response.status_code == 429:
                            raise ProviderFailure("provider_rate_limited")
                        if response.status_code in {401, 403}:
                            raise ProviderFailure("provider_auth")
                        if response.status_code == 400:
                            raise ProviderFailure("provider_bad_request")
                        if response.status_code == 404:
                            raise ProviderFailure("provider_not_found")
                        if response.status_code >= 500:
                            raise ProviderFailure("provider_unavailable")
                        if response.status_code != 200:
                            raise ProviderFailure("provider_http_error")
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > 65536:
                                raise ProviderFailure("provider_response_too_large")
                            chunks.append(chunk)
            body = json.loads(b"".join(chunks))
            choice = body["choices"][0]
            message = choice["message"]
            if message.get("tool_calls") or message.get("function_call") or message.get("refusal"):
                raise ProviderFailure("provider_refusal_or_tools")
            usage = body.get("usage") or {}
            return ProviderReply(content=message["content"], model=body.get("model", self.config.model),
                                 finish_reason=choice["finish_reason"],
                                 input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"))
        except (TimeoutError, httpx.TimeoutException):
            raise ProviderFailure("provider_timeout") from None
        except httpx.HTTPError:
            raise ProviderFailure("provider_transport") from None
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError, ValidationError):
            raise ProviderFailure("provider_protocol") from None


class OfflineProvider:
    """Deterministic test/demo provider; this is not an LLM."""

    async def generate(self, prompt: PromptPackage, timeout_s: float) -> ProviderReply:
        return ProviderReply(content='{"mode":"speech","text":"Work keeps me occupied, as usual.","cue":null,"evidence_ids":[]}',
                             model="offline-demo", finish_reason="stop", input_tokens=0, output_tokens=0)
