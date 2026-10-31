import asyncio

from npc.contracts.dialogue import ChatMessage, PromptPackage
from npc.generation.provider import OfflineProvider
from tools.npc_lab.diagnostics import InspectableProvider, capture_inputs
from tools.npc_lab.service import LabService, LabTurn, load_profiles


def test_exact_messages_are_recorded_without_credentials_and_scope_resets():
    async def run():
        prompt = PromptPackage(messages=(ChatMessage(role="system", content="Policy"),
                                         ChatMessage(role="user", content="Player input")), budget_bytes=200)
        provider = InspectableProvider(OfflineProvider())
        with capture_inputs() as calls:
            await provider.generate(prompt, 1)
            assert calls[0]["messages"] == [m.model_dump(mode="json") for m in prompt.messages]
            assert calls[0]["max_output_tokens"] == prompt.max_output_tokens
            assert not {"api_key", "headers", "authorization"}.intersection(calls[0])
        await provider.generate(prompt, 1)
        assert len(calls) == 1
    asyncio.run(run())


def test_concurrent_capture_does_not_mix_player_messages():
    async def run():
        provider = InspectableProvider(OfflineProvider())
        async def turn(text):
            prompt = PromptPackage(messages=(ChatMessage(role="system", content="Policy"),
                                             ChatMessage(role="user", content=text)), budget_bytes=200)
            with capture_inputs() as calls:
                await asyncio.sleep(0)
                await provider.generate(prompt, 1)
                return calls
        first, second = await asyncio.gather(turn("Alice"), turn("Bob"))
        assert first[0]["messages"][1]["content"] == "Alice"
        assert second[0]["messages"][1]["content"] == "Bob"
    asyncio.run(run())


def test_authored_route_records_no_prompt_but_generation_records_exact_provider_input():
    async def run():
        class Recording(OfflineProvider):
            def __init__(self): self.prompts = []
            async def generate(self, prompt, timeout_s):
                self.prompts.append(prompt)
                return await super().generate(prompt, timeout_s)
        provider = Recording()
        service = LabService(provider)
        p = load_profiles()["elin"]
        def request(text, id):
            return LabTurn(request_id=id, persona_id=p.id, text=text, relationship=p.relationship, mood=p.mood)
        authored = await service.turn(request("Hello", "greeting"))
        assert authored["result"]["model_calls"] == 0
        assert authored["llm_input"]["calls"] == []
        generated = await service.turn(request("What keeps you busy?", "question"))
        assert generated["result"]["model_calls"] == 1
        assert generated["llm_input"]["calls"][0]["messages"] == [m.model_dump(mode="json") for m in provider.prompts[0].messages]
    asyncio.run(run())


def test_repair_input_is_the_actual_second_package():
    async def run():
        from npc.contracts.dialogue import ProviderReply
        class Repair(OfflineProvider):
            def __init__(self): self.prompts = []
            async def generate(self, prompt, timeout_s):
                self.prompts.append(prompt)
                if len(self.prompts) == 1:
                    return ProviderReply(content="invalid", model="fake", finish_reason="stop")
                return await super().generate(prompt, timeout_s)
        provider = Repair(); service = LabService(provider); p = load_profiles()["elin"]
        result = await service.turn(LabTurn(request_id="repair", persona_id=p.id, text="What keeps you busy?",
                                           relationship=p.relationship, mood=p.mood))
        assert result["result"]["status"] == "repair_success"
        calls = result["llm_input"]["calls"]
        assert len(calls) == 2
        assert calls[1]["messages"] == [m.model_dump(mode="json") for m in provider.prompts[1].messages]
        assert "invalid_json" in calls[1]["messages"][0]["content"]
        assert '"text":"your line"' in calls[1]["messages"][0]["content"]
    asyncio.run(run())
