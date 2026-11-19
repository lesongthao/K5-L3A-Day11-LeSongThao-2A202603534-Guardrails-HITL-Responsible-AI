"""Luồng Blue thực: chặn trước model, che output, kiểm soát dữ liệu gửi ra."""
from __future__ import annotations
import json
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import SimpleNamespace
from google.genai import types
from assignment.audit_log import AuditLogPlugin
from assignment.egress import is_egress_allowed
from assignment.monitoring import MonitoringAlert
from assignment.rate_limiter import RateLimitPlugin
from guardrails.input_guardrails import InputGuardrailPlugin
from guardrails.output_guardrails import OutputGuardrailPlugin

Responder = Callable[[str], Awaitable[str]]


class ModelCallError(RuntimeError):
    """Lỗi live không được đổi thành câu trả lời mô phỏng hoặc kết quả pass."""


class BluePipeline:
    def __init__(self, plugins: list, audit: AuditLogPlugin, monitor: MonitoringAlert,
                 responder: Responder | None = None) -> None:
        if [type(p) for p in plugins] != [RateLimitPlugin, InputGuardrailPlugin, OutputGuardrailPlugin]:
            raise ValueError("Expected rate limiter, input guardrail, output guardrail, in this order")
        self.rate, self.input_guard, self.output_guard = plugins
        self.audit, self.monitor = audit, monitor
        self.model_calls = self.egress_checks = self.redactions = 0
        self.api_attempts = 0
        self.live = responder is None
        if responder is None:
            from agents.agent import create_blue_agent
            from core.utils import chat_with_agent
            # Plugins được gọi ở đây, đúng một lần; runner chỉ phụ trách model.
            agent, runner = create_blue_agent([])
            data = json.loads((Path(__file__).resolve().parents[2]
                               / "data/pii_hallucination_samples.json").read_text(encoding="utf-8"))
            truth = data["ground_truth"]
            facts = {key: truth[key] for key in ("bank_name", "products", "rates", "policies")}
            agent.instruction += (
                "\nTrusted fictional lab banking facts: " + json.dumps(facts, ensure_ascii=False)
                + "\nUse only these supplied facts for exact rates and policies. "
                "Do not invent fees, transaction limits, account balances, or transaction status. "
                "When unavailable, explain how the customer can check securely."
            )
            runner.client_kwargs.update(timeout=45, max_retries=0)

            async def live_reply(prompt: str) -> str:
                for attempt in range(3):
                    if attempt:
                        await asyncio.sleep(5 * attempt)
                    self.api_attempts += 1
                    try:
                        text, _ = await chat_with_agent(agent, runner, prompt)
                        return text
                    except Exception as exc:
                        status = getattr(exc, "status_code", None)
                        if status not in {429, 500, 502, 503, 504} or attempt == 2:
                            raise
                        print(f"Blue HTTP {status}; retry {attempt + 1}/2 with backoff.")
                raise AssertionError("unreachable")

            responder = live_reply
        self.responder = responder

    def _finish(self, req_id: str, user_id: str, prompt: str, text: str,
                blocked: bool = False, layer: str | None = None, **extra: object) -> dict:
        self.monitor.blocked_requests += int(blocked)
        self.audit.record_output(user_id=user_id, text=text, blocked=blocked,
                                 layer=layer, request_id=req_id)
        return {"input": prompt, "blocked": blocked, "layer": layer,
                "response_preview": text[:500], **extra}

    async def process(self, prompt: str, user_id: str = "customer",
                      destination: str = "https://api.vinbank.example/v1/chat") -> dict:
        req_id = self.audit.record_input(user_id=user_id, text=prompt)
        self.monitor.total_requests += 1
        content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        context = SimpleNamespace(user_id=user_id)
        for plugin, layer in [(self.rate, "rate_limiter"), (self.input_guard, "input_guardrail")]:
            result = await plugin.on_user_message_callback(invocation_context=context, user_message=content)
            if result is not None:
                self.monitor.rate_limit_hits += int(layer == "rate_limiter")
                return self._finish(req_id, user_id, prompt, result.parts[0].text, True, layer)
        try:
            self.model_calls += 1
            text = await self.responder(prompt)
            if not isinstance(text, str) or not text.strip():
                raise ValueError("empty model response")
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            self._finish(req_id, user_id, prompt, "Model unavailable; no response was generated.", True, "model_error")
            raise ModelCallError(f"Blue API failed: {type(exc).__name__}; HTTP {status}") from None
        response = SimpleNamespace(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))
        before_redact, before_block = self.output_guard.redacted_count, self.output_guard.blocked_count
        response = await self.output_guard.after_model_callback(callback_context=context, llm_response=response)
        text = self.output_guard._extract_text(response)
        redacted = self.output_guard.redacted_count > before_redact
        self.redactions += int(redacted)
        if self.output_guard.blocked_count > before_block:
            return self._finish(req_id, user_id, prompt, text, True, "output_guardrail")
        self.egress_checks += 1
        if not is_egress_allowed(destination, text):
            return self._finish(req_id, user_id, prompt, "Response withheld by egress policy.", True, "egress")
        return self._finish(req_id, user_id, prompt, text, layer="output_guardrail" if redacted else None,
                            redacted=redacted, egress_allowed=True)

    async def check_admission(self, prompt: str, user_id: str) -> dict:
        """Đo burst rate limit trực tiếp; không giả vờ đã gọi model."""
        req_id = self.audit.record_input(user_id=user_id, text=prompt)
        self.monitor.total_requests += 1
        content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        blocked = await self.rate.on_user_message_callback(
            invocation_context=SimpleNamespace(user_id=user_id), user_message=content)
        if blocked is not None:
            self.monitor.rate_limit_hits += 1
            return self._finish(req_id, user_id, prompt, blocked.parts[0].text, True, "rate_limiter")
        return self._finish(req_id, user_id, prompt, "Admission accepted; model not invoked (rate-limit burst test).")
