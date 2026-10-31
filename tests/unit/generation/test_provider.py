import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from npc.contracts.dialogue import ChatMessage, PromptPackage
from npc.generation.provider import ChatCompletionsProvider, ProviderConfig, ProviderFailure

PROMPT = PromptPackage(messages=(ChatMessage(role="system", content="Return JSON"), ChatMessage(role="user", content="Hello")), budget_bytes=300)


def config(**changes):
    return ProviderConfig(**{**dict(base_url="https://example.test/v1", model="test-model", api_key="PRIVATE_TEST_KEY"), **changes})


def body(**changes):
    return {**{"model": "actual-model", "choices": [{"message": {"content": '{"mode":"speech","text":"Hello"}'}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 20, "completion_tokens": 10}}, **changes}


def invoke(handler, **config_changes):
    provider = ChatCompletionsProvider(config(**config_changes), transport=httpx.MockTransport(handler))
    return asyncio.run(provider.generate(PROMPT, 1))


def test_transport_payload_and_usage_are_bounded_and_explicit():
    def handler(request):
        assert str(request.url) == "https://example.test/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer PRIVATE_TEST_KEY"
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["max_tokens"] == 160
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json=body())
    reply = invoke(handler)
    assert reply.model == "actual-model"
    assert (reply.input_tokens, reply.output_tokens) == (20, 10)


@pytest.mark.parametrize("url", ["http://remote.test/v1", "https://user:password@example.test/v1", "https://example.test/v1?key=secret", "file:///tmp/x", "https://example.test/#secret"])
def test_unsafe_provider_urls_are_rejected(url):
    with pytest.raises(ValidationError):
        config(base_url=url)


def test_loopback_and_optional_json_format_support():
    assert config(base_url="http://localhost:11434/v1").base_url.startswith("http:")
    def handler(request):
        assert "response_format" not in json.loads(request.content)
        return httpx.Response(200, json=body(usage=None))
    reply = invoke(handler, response_format="none")
    assert reply.input_tokens is None


@pytest.mark.parametrize("status,code", [(401, "provider_auth"), (429, "provider_rate_limited"), (500, "provider_http_error"), (302, "provider_http_error")])
def test_provider_errors_are_typed_redacted_and_not_retried(status, code):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="PRIVATE_RESPONSE", headers={"location": "https://other.test"})
    with pytest.raises(ProviderFailure) as error:
        invoke(handler)
    assert error.value.code == code
    assert "PRIVATE" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("payload", [{}, {"choices": []}, body(usage={"prompt_tokens": -1}), body(choices=[{"message": {"content": None}, "finish_reason": "stop"}])])
def test_malformed_provider_envelopes_fail_closed(payload):
    with pytest.raises(ProviderFailure, match="provider_protocol"):
        invoke(lambda request: httpx.Response(200, json=payload))


def test_large_http_response_is_rejected():
    with pytest.raises(ProviderFailure, match="provider_response_too_large"):
        invoke(lambda request: httpx.Response(200, content=b"x"*65537))


def test_network_errors_are_redacted():
    def handler(request):
        raise httpx.ConnectError("PRIVATE_TEST_KEY", request=request)
    with pytest.raises(ProviderFailure, match="provider_transport"):
        invoke(handler)


def test_total_timeout_bounds_handler_even_without_httpx_inactivity_timeout():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, json=body())
    provider = ChatCompletionsProvider(config(), transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderFailure, match="provider_timeout"):
        asyncio.run(provider.generate(PROMPT, 0.02))


def test_total_timeout_bounds_drip_fed_response():
    class Drip(httpx.AsyncByteStream):
        async def __aiter__(self):
            for _ in range(100):
                await asyncio.sleep(0.005)
                yield b" "
    provider = ChatCompletionsProvider(config(), transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Drip())))
    with pytest.raises(ProviderFailure, match="provider_timeout"):
        asyncio.run(provider.generate(PROMPT, 0.03))
