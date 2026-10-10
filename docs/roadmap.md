# Roadmap

## Đang làm — Pilot (bản gõ chữ)
- [ ] Deploy (xem `deploy_guide.md`) → pilot 3–5 học sinh, 1–2 tuần
- [ ] Review kỹ mọi nhận xét giai đoạn đầu (xem `review_guide.md`) → vòng v2 prompt
- [ ] Chốt bộ nhãn chiến lược diễn đạt sau khi có ví dụ thật
- [ ] README tiếng Anh (Why / What / How / Evaluation) như writing-coach

## Phát triển tương lai

### 🎤 Ghi âm câu trả lời (ưu tiên 1 sau pilot)
- **Cách làm:** mỗi câu chọn **🎤 Nói** hoặc **⌨️ Gõ**. Ghi âm bằng `st.audio_input` (có sẵn trong Streamlit, chạy trên điện thoại).
- **Chuyển giọng nói → chữ:** cần dịch vụ riêng (Claude API chưa nhận audio trực tiếp — kiểm tra lại lúc làm). Ứng viên: OpenAI Whisper / gpt-4o-transcribe (~$0.005/phút) → thêm 1 API key.
- **Chỗ khó:** học sinh bí sẽ **nói chen tiếng Việt** → STT xử lý kém (vd "viện phí" → "via fee").
  → Sau khi ghi âm, **hiện bản chữ cho học sinh sửa** (gõ lại tiếng Việt chỗ bí) rồi mới nhận xét.
- **Không đổi:** vẫn chỉ nhận xét **cách diễn đạt**; phát âm / độ trôi chảy không chấm qua bản chữ.
- **Cần đo khi làm:** tỉ lệ STT nhận đúng chỗ tiếng Việt; học sinh có sửa bản chữ không; thời gian chờ thêm.
- Ước tính: ~1 buổi code + eval chất lượng STT trên giọng học sinh.

### Khác
- **Nút "Gợi ý ý tưởng"**: 2–3 ý mẫu (AI soạn, giáo viên duyệt) cho học sinh không nghĩ ra gì → dùng lại làm bộ eval.
- **Tải nhận xét về (HTML)** để ôn lại, như writing-coach.
- **Thí nghiệm Haiku** (rẻ ~3 lần) trên bộ `data/gold` — chỉ đổi nếu ✓ % không giảm.
- **Nhận xét chất lượng ý tưởng** (v2) — hiện cố ý chỉ nhận xét cách diễn đạt.
- **Theo dõi tiến bộ**: học sinh có bớt "chỗ bí" qua các tuần không; chiến lược nào học sinh tự dùng được.
- **Chung nền tảng với writing-coach** (1 đăng nhập, 1 hồ sơ học sinh) khi hệ sinh thái có ≥ 3 công cụ.
