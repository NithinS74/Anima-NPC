"""Bounded response-ready preview, without persistence or game delivery."""

import asyncio
from contextlib import asynccontextmanager
from time import monotonic
from typing import Callable

from pydantic import Field, StrictInt, model_validator

from npc.behavior import choose_plan
from npc.context import build_situation
from npc.contracts.context import ContextScenario, Contract
from npc.contracts.dialogue import CurrentState, ProviderReply, ResponseBody, TurnPreview
from npc.generation.prompt import PromptTooLarge, build_prompt
from npc.generation.provider import ModelProvider, ProviderFailure
from npc.validation import validate_response


class PreviewLimits(Contract):
    response_timeout_ms: StrictInt = Field(default=3000, ge=100, le=60000)
    model_cutoff_ms: StrictInt = Field(default=2450, ge=50, le=59000)
    max_input_bytes: StrictInt = Field(default=2048, ge=512, le=32000)
    max_output_tokens: StrictInt = Field(default=160, ge=32, le=512)

    @model_validator(mode="after")
    def reserve_response_time(self) -> "PreviewLimits":
        if self.model_cutoff_ms >= self.response_timeout_ms - 10:
            raise ValueError("reserve time after model work for validation/fallback")
        return self


async def _invoke(provider, prompt, timeout_s, cancellation, retain_cleanup):
    task = asyncio.create_task(provider.generate(prompt, timeout_s))
    cancel_task = asyncio.create_task(cancellation.wait()) if cancellation is not None else None
    tasks = {task} | ({cancel_task} if cancel_task else set())
    try:
        done, _ = await asyncio.wait(tasks, timeout=timeout_s, return_when=asyncio.FIRST_COMPLETED)
        if cancel_task is not None and cancel_task in done:
            raise ProviderFailure("cancelled")
        if task not in done:
            raise ProviderFailure("provider_timeout")
        return task.result()
    finally:
        if not task.done():
            task.cancel()
            retain_cleanup(task)
        else:
            # Retrieve exceptions even when cancellation won the race.
            if not task.cancelled():
                task.exception()
        if cancel_task is not None:
            cancel_task.cancel()
            await asyncio.gather(cancel_task, return_exceptions=True)


class PreviewRunner:
    """Reuse ONE instance to bound local provider work. No pending-work queue."""

    def __init__(self, provider: ModelProvider, limits: PreviewLimits | None = None, *, clock: Callable[[], float] = monotonic):
        self.provider = provider
        self.limits = limits or PreviewLimits()
        self.clock = clock
        self._slot = asyncio.Lock()
        self._pending_cleanup: asyncio.Task | None = None
        self._owners: set[tuple[str, str, str, str]] = set()

    def _retain_cleanup(self, task: asyncio.Task):
        # At most one outstanding provider task: its admission remains held.
        self._pending_cleanup = task

        def settled(completed):
            if not completed.cancelled():
                completed.exception()
            if self._pending_cleanup is completed:
                self._pending_cleanup = None

        task.add_done_callback(settled)

    @asynccontextmanager
    async def _admission(self):
        await self._slot.acquire()
        try:
            yield
        finally:
            cleanup = self._pending_cleanup
            if cleanup is not None and not cleanup.done():
                cleanup.add_done_callback(lambda _: self._slot.release())
            else:
                self._slot.release()

    async def run(self, scenario: ContextScenario, *, cancellation: asyncio.Event | None = None,
                  current_state: Callable[[], CurrentState] | None = None) -> TurnPreview:
        key = (scenario.turn.scope.game_id, scenario.turn.scope.world_id, scenario.turn.scope.save_branch_id, scenario.turn.npc_id)
        if key in self._owners:
            situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
            return TurnPreview(request_id=situation.request_id, npc_id=situation.npc_id, status="busy",
                               plan=choose_plan(situation), response=None, model_calls=0, error_code="npc_busy", elapsed_ms=0,
                               response_deadline_ms=self.limits.response_timeout_ms, model_cutoff_ms=self.limits.model_cutoff_ms,
                               timing_profile=self._timing_profile())
        self._owners.add(key)
        try:
            return await self._run(scenario, cancellation=cancellation, current_state=current_state)
        finally:
            self._owners.discard(key)

    def _timing_profile(self):
        return "realtime" if (self.limits.response_timeout_ms, self.limits.model_cutoff_ms) == (3000, 2450) else "development"

    async def _run(self, scenario: ContextScenario, *, cancellation: asyncio.Event | None = None,
                   current_state: Callable[[], CurrentState] | None = None) -> TurnPreview:
        start = self.clock()
        situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
        plan = choose_plan(situation)
        current_state = current_state or (lambda: CurrentState(dialogue_revision=situation.dialogue_revision, turn_epoch=situation.turn_epoch))
        calls, violations, model = 0, (), None
        input_tokens, output_tokens, usage_complete = 0, 0, True

        def stale():
            state = current_state()
            return (state.dialogue_revision, state.turn_epoch) != (situation.dialogue_revision, situation.turn_epoch)

        def stopped():
            return (cancellation is not None and cancellation.is_set()) or stale()

        def finish(status, response=None, error=None):
            # Never turn stale/cancelled work into an audible fallback.
            if stopped():
                status, response, error = "cancelled", None, "cancelled_or_stale"
            return TurnPreview(request_id=situation.request_id, npc_id=situation.npc_id, status=status,
                               plan=plan, response=response, model_calls=calls, violations=violations,
                               error_code=error, model=model, elapsed_ms=max(0, (self.clock()-start)*1000),
                               input_tokens=input_tokens, output_tokens=output_tokens, usage_complete=usage_complete,
                               response_deadline_ms=self.limits.response_timeout_ms, model_cutoff_ms=self.limits.model_cutoff_ms,
                               timing_profile=self._timing_profile())

        def checked(body):
            reply = ProviderReply(content=body.model_dump_json(), model="authored", finish_reason="stop")
            return validate_response(reply, situation, plan, current_state())

        def fallback(code):
            if (self.clock()-start)*1000 >= self.limits.response_timeout_ms:
                return finish("error_fallback", error="response_deadline")
            body = ResponseBody(mode="speech", text=plan.fallback_text)
            validation = checked(body)
            return finish("error_fallback", validation.response, code if validation.accepted else "invalid_fallback")

        if stopped():
            return finish("cancelled", error="cancelled_or_stale")
        if plan.route != "generate":
            body = ResponseBody(mode="end" if plan.route == "end" else "silence" if plan.route == "silent" else "speech",
                                text=plan.authored_text)
            validation = checked(body)
            return finish("policy_silence" if plan.route in {"silent", "end"} else "authored_success",
                          validation.response, None if validation.accepted else "invalid_authored_response")
        if self._slot.locked():
            return finish("busy", error="provider_busy")
        async with self._admission():
            for attempt in range(2):
                if stopped():
                    return finish("cancelled", error="cancelled_or_stale")
                remaining = self.limits.model_cutoff_ms/1000 - (self.clock()-start)
                if remaining <= 0:
                    return fallback("model_cutoff")
                try:
                    prompt = build_prompt(situation, plan, max_input_bytes=self.limits.max_input_bytes,
                                          max_output_tokens=self.limits.max_output_tokens,
                                          repair_codes=violations if attempt else ())
                except PromptTooLarge:
                    return fallback("prompt_budget")
                remaining = self.limits.model_cutoff_ms/1000 - (self.clock()-start)
                if remaining <= 0:
                    return fallback("model_cutoff")
                calls += 1
                try:
                    reply = await _invoke(self.provider, prompt, remaining, cancellation, self._retain_cleanup)
                except ProviderFailure as error:
                    usage_complete = False
                    if error.code == "cancelled":
                        return finish("cancelled", error="cancelled")
                    return fallback(error.code)
                model = reply.model
                usage_complete = usage_complete and reply.input_tokens is not None and reply.output_tokens is not None
                input_tokens += reply.input_tokens or 0
                output_tokens += reply.output_tokens or 0
                if stopped():
                    return finish("cancelled", error="cancelled_or_stale")
                if (self.clock()-start)*1000 >= self.limits.model_cutoff_ms:
                    return fallback("late_completion")
                validation = validate_response(reply, situation, plan, current_state())
                violations = tuple(dict.fromkeys(violations + validation.violations))
                if validation.accepted:
                    return finish("repair_success" if attempt else "model_success", validation.response)
                if "stale_state" in validation.violations:
                    return finish("cancelled", error="stale_state")
            return fallback("invalid_candidate")
        raise AssertionError("unreachable")
