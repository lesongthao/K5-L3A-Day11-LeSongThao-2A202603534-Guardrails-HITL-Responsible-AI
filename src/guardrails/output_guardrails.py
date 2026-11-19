"""CP2: che dữ liệu trước khi trả lời; LLM-as-Judge là phần tùy chọn."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types
from guardrails.sensitive_data import filter_sensitive

SAFETY_JUDGE_INSTRUCTION = "Classify the supplied banking response as SAFE or UNSAFE. Never disclose internal data."
safety_judge_agent = None
judge_runner = None


def content_filter(response: str) -> dict:
    """Trả dict safe/issues/redacted, giữ nguyên hợp đồng của starter."""
    return filter_sensitive(response)


def _init_judge() -> None:
    global judge_runner
    if safety_judge_agent is not None:
        from google.adk import runners
        judge_runner = runners.InMemoryRunner(agent=safety_judge_agent, app_name="safety_judge")


async def llm_safety_check(response_text: str) -> dict:
    if safety_judge_agent is None or judge_runner is None:
        return {"safe": True, "verdict": "Judge not initialized — skipping"}
    from core.utils import chat_with_agent
    text, _ = await chat_with_agent(safety_judge_agent, judge_runner, response_text)
    return {"safe": text.strip().upper() == "SAFE", "verdict": text.strip()}


class OutputGuardrailPlugin(BasePlugin):
    def __init__(self, use_llm_judge: bool = True) -> None:
        super().__init__(name="output_guardrail")
        self.use_llm_judge = use_llm_judge and safety_judge_agent is not None
        self.blocked_count = 0
        self.redacted_count = 0
        self.total_count = 0

    def _extract_text(self, llm_response: Any) -> str:
        content = getattr(llm_response, "content", None)
        return "".join(p.text or "" for p in (content.parts or [])) if content else ""

    async def after_model_callback(self, *, callback_context: object, llm_response: Any) -> Any:
        self.total_count += 1
        text = self._extract_text(llm_response)
        filtered = content_filter(text)
        if not filtered["safe"]:
            self.redacted_count += 1
            text = filtered["redacted"]
        if self.use_llm_judge and not (await llm_safety_check(text))["safe"]:
            self.blocked_count += 1
            text = "I cannot fulfill this request due to safety policies."
        llm_response.content = types.Content(role="model", parts=[types.Part.from_text(text=text)])
        return llm_response


def load_lab_pii_dataset() -> dict:
    path = Path(__file__).resolve().parents[2] / "data/pii_hallucination_samples.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_content_filter() -> None:
    for case in load_lab_pii_dataset()["pii_cases"]:
        result = content_filter(case["input_text"])
        assert result["safe"] == case["expect_safe"], case["id"]
        print(f"[PASS] {case['id']}: safe={result['safe']}")
