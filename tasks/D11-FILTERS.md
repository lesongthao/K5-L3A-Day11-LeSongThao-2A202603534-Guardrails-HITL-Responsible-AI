# D11-FILTERS — Sửa bộ lọc CP2

Thực hiện đúng docs/PRD.md mốc 1 và docs/ARCHITECTURE.md. Chỉ sửa phạm vi
được cấp. Đây là vai trò triển khai bên trong workflow: không gọi agent khác,
không chạy shell/test, không mở .env/auth. Bộ điều phối sẽ chạy checks.

1. Thêm helper normalization.py dùng unicodedata.normalize('NFKC') và bỏ
   Unicode category Cf; helper topic không dấu NFKD + đ→d. Không phá whitespace.
2. detect_injection bắt đầy đủ mẫu bắt buộc hiện có, U+200B/U+2060/fullwidth,
   câu đòi lộ credential và lệnh nhúng email/RAG; không chặn tài liệu ngoài lành.
3. topic_filter xử lý tiếng Việt có dấu, từ đầy đủ, cho phép câu hỏi phòng vệ
   tài khoản bị hack nhưng không cho câu 'how to hack/steal' lọt nhờ thêm 'protect'.
4. content_filter che SĐT VN dạng 0912345678, +84912345678, +84 912 345 678,
   email, CCCD 9/12 chữ số, API key sk-, password: X, password = X,
   password is X, password X và mật khẩu tiếng Việt. Secret demo lấy từ
   DEMO_SECRETS, không chỉ hardcode admin123. Có thể che các biến thể mã hóa
   thông dụng của secret demo, nhưng không đưa thêm dependency.
5. Giữ API InputGuardrailPlugin/OutputGuardrailPlugin, các hàm quick test và
   optional judge hiện tại để main.py --part 2 vẫn chạy. Rút gọn comment/demo
   hoặc tách helper để mỗi file được sửa <=300 dòng. Type hints rõ ràng.
6. Thêm tests/regression/test_filters.py kiểm thử độc lập input và output,
   gồm cả safe và malicious gần nhau để tránh mở rộng ngoại lệ phòng vệ.
   Không sửa smoke/public/rubric/schema/core/agents hoặc outputs.

Tiêu chí: tests gốc vẫn pass; regression tái hiện và khắc phục các lỗi trên.
Báo đúng file thay đổi, giới hạn còn lại; không công bố full điểm.
