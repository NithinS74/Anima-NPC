import asyncio
import json

import pytest

from npc.contracts.context import ContextScenario
from npc.contracts.dialogue import CurrentState, ProviderReply
from npc.generation.provider import ProviderFailure
from npc.runtime.preview import PreviewLimits, PreviewRunner

VALID = '{"mode":"speech","text":"Work is tiring.","cue":null,"evidence_ids":[]}'


class ScriptedProvider:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    async def generate(self, prompt, timeout_s):
        self.calls.append(prompt)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ProviderReply(content=reply, model="fake", finish_reason="stop", input_tokens=10, output_tokens=5)


def generating(data):
    data["turn"]["facts"] = []
    data["turn"]["player_input"]["text"] = "How is your work going?"
    return ContextScenario.model_validate(data)


def test_one_call_success(scenario_data):
    provider = ScriptedProvider(VALID)
    result = asyncio.run(PreviewRunner(provider).run(generating(scenario_data)))
    assert result.status == "model_success"
    assert result.response.text == "Work is tiring."
    assert result.model_calls == 1
    assert result.input_tokens == 10
    assert result.timing_profile == "realtime"


def test_invalid_output_gets_one_targeted_repair(scenario_data):
    provider = ScriptedProvider("PRIVATE_INVALID_OUTPUT", VALID)
    result = asyncio.run(PreviewRunner(provider).run(generating(scenario_data)))
    assert result.status == "repair_success"
    assert result.model_calls == 2
    assert result.input_tokens == 20
    assert "invalid_json" in result.violations
    assert "PRIVATE_INVALID_OUTPUT" not in "".join(item.content for item in provider.calls[1].messages)


def test_two_invalid_outputs_then_validated_fallback(scenario_data):
    provider = ScriptedProvider("bad", "still bad")
    result = asyncio.run(PreviewRunner(provider).run(generating(scenario_data)))
    assert result.status == "error_fallback"
    assert result.model_calls == 2
    assert result.response.text == result.plan.fallback_text


@pytest.mark.parametrize("code", ["provider_timeout", "provider_rate_limited", "provider_auth", "provider_transport", "provider_output_limit"])
def test_provider_failures_fall_back_without_retry(scenario_data, code):
    provider = ScriptedProvider(ProviderFailure(code))
    result = asyncio.run(PreviewRunner(provider).run(generating(scenario_data)))
    assert result.status == "error_fallback"
    assert result.model_calls == 1
    assert result.error_code == code
    assert result.response is not None
    assert not result.usage_complete


def test_authored_busy_path_has_no_model_calls(scenario):
    provider = ScriptedProvider()
    result = asyncio.run(PreviewRunner(provider).run(scenario))
    assert result.status == "authored_success"
    assert result.response.text == result.plan.authored_text
    assert result.model_calls == 0


def test_combat_has_no_model_calls_or_speech(scenario_data):
    scenario_data["turn"]["facts"][0]["path"] = "npc.in_combat"
    result = asyncio.run(PreviewRunner(ScriptedProvider()).run(ContextScenario.model_validate(scenario_data)))
    assert result.status == "policy_silence"
    assert result.response.mode == "end"
    assert result.response.text == ""
    assert result.model_calls == 0


def test_budget_failure_has_no_provider_work(scenario_data):
    scenario_data["turn"]["player_input"]["text"] = "x"*4000
    scenario = generating(scenario_data)
    data = scenario.model_dump()
    data["turn"]["player_input"]["text"] = "x"*4000
    result = asyncio.run(PreviewRunner(ScriptedProvider()).run(ContextScenario.model_validate(data)))
    assert result.error_code == "prompt_budget"
    assert result.model_calls == 0


def test_stale_before_generation_does_not_speak(scenario_data):
    scenario = generating(scenario_data)
    state = lambda: CurrentState(dialogue_revision=999, turn_epoch=1)
    result = asyncio.run(PreviewRunner(ScriptedProvider()).run(scenario, current_state=state))
    assert result.status == "cancelled"
    assert result.response is None
    assert result.model_calls == 0


def test_state_change_during_generation_suppresses_output_and_fallback(scenario_data):
    scenario = generating(scenario_data)
    state = [CurrentState(dialogue_revision=7, turn_epoch=1)]
    class ChangingProvider:
        async def generate(self, prompt, timeout_s):
            state[0] = CurrentState(dialogue_revision=8, turn_epoch=2)
            return ProviderReply(content=VALID, model="fake", finish_reason="stop")
    result = asyncio.run(PreviewRunner(ChangingProvider()).run(scenario, current_state=lambda: state[0]))
    assert result.status == "cancelled"
    assert result.response is None


def test_late_result_rejected_and_repair_not_started(scenario_data):
    clock = [0.0]
    class LateProvider:
        async def generate(self, prompt, timeout_s):
            clock[0] = 2.6
            return ProviderReply(content=VALID, model="fake", finish_reason="stop")
    result = asyncio.run(PreviewRunner(LateProvider(), clock=lambda: clock[0]).run(generating(scenario_data)))
    assert result.error_code == "late_completion"
    assert result.model_calls == 1
    assert result.status == "error_fallback"


def test_whole_response_deadline_does_not_emit_late_fallback(scenario_data):
    clock = [0.0]
    class LateProvider:
        async def generate(self, prompt, timeout_s):
            clock[0] = 3.1
            return ProviderReply(content="bad", model="fake", finish_reason="stop")
    result = asyncio.run(PreviewRunner(LateProvider(), clock=lambda: clock[0]).run(generating(scenario_data)))
    assert result.error_code == "response_deadline"
    assert result.response is None


def test_cancellation_stops_provider_before_slot_is_released(scenario_data):
    async def run():
        started, stopped, cancellation = asyncio.Event(), asyncio.Event(), asyncio.Event()
        class SlowProvider:
            async def generate(self, prompt, timeout_s):
                started.set()
                try:
                    await asyncio.sleep(10)
                finally:
                    stopped.set()
        runner = PreviewRunner(SlowProvider())
        task = asyncio.create_task(runner.run(generating(scenario_data), cancellation=cancellation))
        await started.wait()
        cancellation.set()
        result = await task
        assert stopped.is_set()
        assert result.status == "cancelled"
        assert result.response is None
    asyncio.run(run())


def test_single_runner_arbitrates_same_npc_and_global_provider_slot(scenario_data):
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        class HoldingProvider:
            async def generate(self, prompt, timeout_s):
                started.set()
                await release.wait()
                return ProviderReply(content=VALID, model="fake", finish_reason="stop")
        runner = PreviewRunner(HoldingProvider())
        scenario = generating(scenario_data)
        first = asyncio.create_task(runner.run(scenario))
        await started.wait()
        second = await runner.run(scenario)
        assert second.error_code == "npc_busy"
        assert second.model_calls == 0
        data = scenario.model_dump()
        data["turn"]["npc_id"] = data["snapshot"]["npc_id"] = "another-npc"
        third = await runner.run(ContextScenario.model_validate(data))
        assert third.error_code == "provider_busy"
        release.set()
        assert (await first).status == "model_success"
    asyncio.run(run())


def test_development_timing_profile_is_explicit(scenario_data):
    limits = PreviewLimits(response_timeout_ms=10000, model_cutoff_ms=9450)
    result = asyncio.run(PreviewRunner(ScriptedProvider(VALID), limits).run(generating(scenario_data)))
    assert result.timing_profile == "development"
    assert result.response_deadline_ms == 10000


def test_slow_provider_cleanup_does_not_delay_caller_or_release_admission(scenario_data):
    async def run():
        cleaning, release = asyncio.Event(), asyncio.Event()
        class SlowCleanupProvider:
            async def generate(self, prompt, timeout_s):
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    cleaning.set()
                    await release.wait()
                    return ProviderReply(content=VALID, model="fake", finish_reason="stop")
        limits = PreviewLimits(response_timeout_ms=500, model_cutoff_ms=50)
        runner = PreviewRunner(SlowCleanupProvider(), limits)
        scenario = generating(scenario_data)
        task = asyncio.create_task(runner.run(scenario))
        try:
            await asyncio.wait_for(cleaning.wait(), timeout=1)
            # Cleanup is blocked indefinitely, so caller completion must be independent of it.
            result = await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
            assert result.error_code == "provider_timeout"
            assert result.response is not None
            assert result.elapsed_ms < 500
            still_busy = await runner.run(scenario)
            assert still_busy.status == "busy"
            assert still_busy.model_calls == 0
        finally:
            release.set()
            await task
            await asyncio.sleep(0)
    asyncio.run(run())
