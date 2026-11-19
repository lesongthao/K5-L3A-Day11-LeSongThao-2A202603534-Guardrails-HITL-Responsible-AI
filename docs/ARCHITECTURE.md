# Kiến trúc bài Day 11

## Luồng Blue

User → RateLimitPlugin → InputGuardrailPlugin → Blue OpenRouter thật
→ OutputGuardrailPlugin → kiểm tra egress → trả lời.

Egress là cổng kiểm tra dữ liệu ra ngoài, giống kiểm tra phiếu xuất kho:
đích phải đúng danh sách được phép và hàng gửi không chứa dữ liệu bí mật.
Audit/monitoring bao quanh mọi nhánh thành công, bị chặn và lỗi.

## Hợp đồng module

| Module | Input | Output / trách nhiệm |
| --- | --- | --- |
| guardrails/normalization.py | str | Unicode NFKC, bỏ ký tự định dạng ẩn; dạng không dấu cho topic |
| guardrails/input_guardrails.py | str / ADK Content | ALLOW/BLOCK; callback chặn trước model |
| guardrails/output_guardrails.py | str / LLM response | safe/issues/redacted; giữ API plugin |
| assignment/rate_limiter.py | user_id + thời gian | hạn mức từng người, cửa sổ trượt |
| assignment/audit_log.py | input/output + request_id | UUID, latency, nhật ký đã che dữ liệu nhạy cảm |
| assignment/pipeline.py và helper | cấu hình + prompt | gọi model thật, thực thi thứ tự và egress, xuất artifact |
| attacks/ và helper | prompt hoặc các lượt | gọi Red/Red Advance, phân loại, lưu đầy đủ bằng chứng |

Tách helper khi cần để file Python được sửa không quá 300 dòng. Không sửa
starter src/agents hoặc src/core chỉ để đáp ứng giới hạn dòng; giữ nguyên
model và cơ chế phòng thủ mục tiêu của giảng viên.

## Cách kiểm thử

- Tests smoke/public gốc là hợp đồng không được sửa.
- Tests regression dùng model giả có chủ đích qua dependency injection hoặc
  mock ở ranh giới API; chỉ ghi vào tmp_path. Không dùng output giả để nộp.
- Suite mặc định luôn chạy live; có metadata nguồn model, thời điểm, số lần
  gọi và phương thức thử rate limit. Lỗi mạng/quota không được đổi thành pass.
- Tách kiểm tra admission của rate limiter khỏi độ trễ API. Mọi request
  thực tế trong suite vẫn được ghi audit/metrics chính xác.
- Mọi artifact chấm trong outputs được sinh bởi main.py hoặc grade.py.

## Phân công

Codex: hợp đồng, review diff và bằng chứng, điều tra lỗi, chạy lab/grader.
Antigravity: bộ lọc, pipeline, cải thiện đóng gói bằng chứng Red, regression
tests, theo phạm vi từng task. Không workflow lồng khi AGENT_WORKFLOW_ACTIVE=1.
