# Hoàn thiện bài cá nhân Day 11

Học viên: Lê Sông Thao — 2A202603534. Căn cứ chấm là RUBRIC.md,
CHECKPOINTS.md, SUBMISSION.md và RULES.md trong repository.

## Phạm vi và nguyên tắc

- Hoàn thiện CP2 (40đ), CP3 (40đ), CP4 (20đ) bằng code chạy được và
  artifact do lệnh lab sinh. Không tự công nhận điểm hoặc bonus.
- Giữ nguyên rubric, schema, tests/public, tests/smoke, data/protected,
  src/agents và cấu hình/model gốc trong src/core.
- API key chỉ được ứng dụng nạp từ môi trường/.env; không in hoặc sửa .env.
- Không commit, push, nộp LMS hoặc thay đổi model để né điều kiện lab.
- Codex lập kế hoạch, nghiệm thu; Antigravity triển khai qua toolkit chung.

## Mốc 1 — Bộ lọc (Antigravity)

Input: văn bản người dùng hoặc đầu ra model. Output: ALLOW/BLOCK,
hoặc dict safe/issues/redacted giữ hợp đồng hiện tại.

Nghiệm thu: bắt injection qua U+200B, U+2060 và chữ full-width;
cho qua câu hỏi ngân hàng tiếng Việt có dấu và câu bảo vệ tài khoản hợp lệ;
chặn yêu cầu thực hiện tấn công. Che mật khẩu dạng ':', '=', 'is', khoảng
trắng, email, SĐT VN có dấu cách, CCCD và secret demo lấy từ cấu hình.
Không sửa tests gốc; thêm regression tests cho lỗi thực tế.

## Mốc 2 — Pipeline Blue thật (Antigravity)

Input: user_input/user_id, plugins và tùy chọn output_dir dùng trong tests.
Output: kết quả từng lượt gồm input/blocked/layer/response_preview, audit,
metrics và results.json đúng schema.

- Đường mặc định gọi create_blue_agent và model OpenRouter cố định thật.
  Không dùng câu trả lời viết sẵn hoặc tự lùi sang mock khi API lỗi.
- Mỗi request đi qua rate limit và input đúng một lần, rồi model, output,
  egress; các trường hợp bị chặn trước model không gọi API.
- Egress cho đúng các host khai báo, chặn URL giả/malformed và dữ liệu
  nhạy cảm; quyết định bằng code, không gửi HTTP tới endpoint giả.
- Request ID duy nhất; latency bằng đồng hồ đơn điệu; audit không lộ secret.
- Rate-limit burst kiểm tra admission trực tiếp, không gọi model để độ trễ
  API không làm sai cửa sổ thời gian; báo rõ phương thức này trong metadata.
- Suite có ít nhất 5 safe, 7 attack, 3 edge; rate metadata lấy từ plugin.
- API lỗi phải được nhận diện, không tính là phản hồi model thành công và
  không ghi đè bộ artifact hoàn chỉnh bằng kết quả giả.

## Mốc 3 — Bằng chứng Red và nộp (Antigravity + Codex nghiệm thu)

- Ít nhất 5 kỹ thuật; prompt đa bước có nhiều lượt và lưu transcript.
- Chạy agent mục tiêu nguyên bản; lưu phản hồi đầy đủ hoặc bằng chứng leak
  đủ kiểm chứng, lỗi API và provider/model thực tế.
- Bonus B1/B2 chỉ ghi là ứng viên chờ grader replay.
- Chạy lại CP2, CP3, CP4 khi dịch vụ sẵn sàng; grade.py tự sinh báo cáo.
- README hướng dẫn tái lập, giải thích ngắn các lớp và giới hạn bằng chứng.

## Tiêu chí hoàn tất

Tests gốc và regression đều đạt; không thay đổi phần được bảo vệ; không có
key thật trong file theo dõi Git; artifact live xác minh được, hoặc báo rõ
dịch vụ/API đang chặn bước nào. Chỉ công bố kết quả đã quan sát, không hứa
điểm chính thức, kết quả hidden tests hoặc replay của coach.
