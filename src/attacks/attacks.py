"""CP4: chạy prompt lên Red và Red Advance nguyên bản, lưu bằng chứng thực."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from core.utils import chat_with_agent
from agents.guards_agent import GUARDS_SECRETS
from attacks.prompts import adversarial_prompts
from attacks.attack_outcome import classify_attack_outcome, response_leaked_secrets
from attacks.attack_io import save_attack_results, write_run_attack_json, attack_result_path
from attacks.ai_attacks import generate_ai_attacks, RED_TEAM_PROMPT


def evidence_preview(response: str) -> str:
    """Bản xem trước lấy đúng đoạn chứa leak; response đầy đủ luôn được giữ."""
    positions = [response.casefold().find(s.casefold()) for s in GUARDS_SECRETS if s]
    positions = [p for p in positions if p >= 0]
    start = max(0, min(positions) - 80) if positions else 0
    return response[start:start + 300]


async def run_attacks(agent: Any, runner: Any, prompts: list[dict] | None = None,
                      target_name: str = "agent", *, save_json: bool = True,
                      output_path: str | Path | None = None) -> list[dict]:
    """Mỗi attack có session riêng; trường turns chứa các lượt mở đầu."""
    results = []
    for attack in adversarial_prompts if prompts is None else prompts:
        print(f"Attack #{attack['id']} on {target_name}: {attack['category']}")
        conversation: list[dict] = []
        session_id = None
        transcript_mode = getattr(runner, "provider", None) in {"openai", "openrouter"}
        try:
            for prompt in [*attack.get("turns", []), attack["input"]]:
                request = prompt
                # Starter OpenAI stateless: gửi lại transcript để giữ ngữ cảnh;
                # Gemini ADK dùng session bản địa. Không sửa phòng thủ mục tiêu.
                if transcript_mode and conversation:
                    history = "\n".join(f"User: {t['input']}\nAssistant: {t['response']}" for t in conversation)
                    request = history + "\nUser: " + prompt
                response, session = await chat_with_agent(agent, runner, request, session_id=session_id)
                if not response.strip():
                    raise ValueError("empty model response")
                session_id = getattr(session, "id", session_id)
                conversation.append({"input": prompt, "response": response})
            full = "\n\n".join(t["response"] for t in conversation)
            outcome = classify_attack_outcome(attack["input"], full, target_name=target_name)
            row = {"id": attack["id"], "name": attack["category"], "category": attack["category"],
                   "input": attack["input"], "response": full, "response_preview": evidence_preview(full),
                   **outcome, "error": None, "target": target_name,
                   "conversation": conversation,
                   "session_mode": "transcript_context" if transcript_mode else "native_session"}
        except Exception as exc:
            error = f"{type(exc).__name__}; HTTP {getattr(exc, 'status_code', None)}"
            row = {"id": attack["id"], "category": attack["category"], "input": attack["input"],
                   "response": "", "response_preview": "Request failed; no success evidence.",
                   "leaked": False, "blocked_input": False, "blocked": False, "layer": "error",
                   "blocked_at": "ERROR — " + error, "error": error,
                   "target": target_name, "conversation": conversation}
        results.append(row)
        print(f"  {row['blocked_at']}")
    if save_json and not any(r.get("error") for r in results):
        write_run_attack_json(results, target_name=target_name, filepath=output_path)
    return results
