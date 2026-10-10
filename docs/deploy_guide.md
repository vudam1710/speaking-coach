# Deploy Speaking Coach (pilot)

> Giống writing-coach, nhưng **dùng lại** API key, service account và mã học viên đã có → phần bạn làm chỉ ~20 phút.
> File `.streamlit/secrets.toml` đã được tạo sẵn từ writing-coach (gitignore, không lên GitHub). Chỉ thiếu **SHEET_ID**.

## 1. Google Sheet mới (~5 phút)
1. Tạo Google Sheet mới, tên `speaking-coach-data`.
2. **Share** → dán `client_email` (xem trong `.streamlit/secrets.toml`, mục `[gcp_service_account]`) → quyền **Editor** → bỏ tick "Notify people" → Share.
3. Copy Sheet ID trong URL: `https://docs.google.com/spreadsheets/d/`**`<SHEET_ID>`**`/edit`.
4. Mở `.streamlit/secrets.toml` → bỏ dấu `#` ở dòng `# SHEET_ID = "..."` → dán ID vào.

✅ Xong khi: chạy `streamlit run app.py`, đăng nhập, nhận xét 1 câu → Sheet tự có 2 tab `submissions` và `feedback`.

> **Không có Sheet = học sinh không vào được** ("Hệ thống đang bảo trì"). Cố ý: không có Sheet thì không đếm được lượt → không chặn được spam. Mã reviewer vẫn vào được để thử.

## 2. Mã học viên
- Đang dùng **chung mã với writing-coach** (cùng học sinh, 1 mã cho cả 2 app).
- Thêm học sinh: thêm 1 dòng vào `[access_codes]` ở **cả hai** nơi: file `secrets.toml` ở máy + Secrets trên Streamlit Cloud.
  ```toml
  [access_codes]
  minh_hs = "minh-2841"                               # học sinh
  co_lan  = { code = "lan-7392", role = "reviewer" }  # giáo viên chấm
  ```
- Mã khó đoán (tên + 4 số ngẫu nhiên), mỗi người 1 mã, không dùng chung.

## 3. Giới hạn chi phí
- `[limits]` trong secrets: **1 lượt = 1 câu trả lời** (= 1 lần gọi AI). Mặc định: học sinh 25/ngày, reviewer 60, toàn hệ thống 150 (~$5–7/ngày tệ nhất).
- Anthropic Console → Settings → Limits: kiểm tra spend limit tháng (đang dùng chung key với writing-coach → cộng chung).

## 4. Kiểm tra trước khi push
```powershell
git status                      # KHÔNG được thấy .streamlit/secrets.toml, .env, _scratch
git ls-files | findstr /i "secrets .env"
```
Chỉ được thấy `.streamlit/secrets.toml.example`.

## 5. Deploy trên Streamlit Community Cloud
1. https://share.streamlit.io → **Create app → Deploy a public app from GitHub**.
2. Repository `speaking-coach`, Branch `main`, Main file `app.py`. App URL ví dụ: `speaking-coach-logiq`.
3. **Advanced settings**: Python **3.12** → ô **Secrets**: dán toàn bộ nội dung `.streamlit/secrets.toml` (đã có SHEET_ID).
4. Deploy → chờ 2–5 phút. Từ giờ push lên `main` là app tự cập nhật.

## 6. Kiểm tra trên link thật
- [ ] Mã sai → bị chặn · mã học sinh **không** thấy nút đánh giá · mã reviewer thấy ✓/~/✗ + loại lỗi
- [ ] Part 1: trả lời 2/4 câu → "Nhận xét 2 câu trả lời" → 2 tab + tổng kết
- [ ] Nâng cấp 1 câu → có chỗ tô vàng
- [ ] Part 2 → nút "Làm tiếp Part 3 cùng chủ đề"
- [ ] Sheet: tab `submissions` có 1 dòng/câu (step coach / upgrade / practice), đủ câu trả lời + result_json
- [ ] `python evaluation/pull_sheet.py` → ra file `.md` + `review_items.csv`
- [ ] Mã reviewer → thanh bên trái **📊 Thống kê** → có số liệu
- [ ] Thử trên điện thoại

✅ Xong → `git tag v0.1` → `git push --tags`.
