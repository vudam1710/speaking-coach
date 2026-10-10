# Review những gì tool trả cho học sinh (giai đoạn đầu)

> **Học sinh không đánh giá gì cả** — chỉ đọc nhận xét và luyện. **Chỉ giáo viên review**, và review **từng thứ** tool đưa cho học sinh, đúng nguyên văn.
> Mọi câu trả lời + toàn bộ nhận xét đều được lưu (học sinh được báo trên trang nhập bài).
> Một vòng = kéo dữ liệu → đọc + chấm → `score.py` → sửa **một** thứ → ghi `EXPERIMENTS.md`.

## 0. Xem nhanh trên app: trang 📊 Thống kê
Đăng nhập bằng mã reviewer → thanh bên trái chọn **📊 Thống kê**: số câu / bộ / người dùng, chi phí, thời gian chờ,
**học sinh hay bí ở đâu** (chỗ tiếng Việt xuất hiện nhiều nhất), chiến lược tool gợi ý, tỉ lệ bấm nâng cấp / nói lại,
bảng từng học sinh (số câu, chỗ bí / câu, trình độ, hôm nay đã dùng bao nhiêu), tiến bộ theo tuần, và tỉ lệ ✓ phần bạn chấm trên app.
Dùng để theo dõi hằng ngày; còn review chi tiết từng nhận xét thì làm theo các bước dưới.

## 1. Kéo dữ liệu về
```powershell
cd "C:\Users\Vu Dam\OneDrive\Desktop\AI Agents\Project_Portfolio\speaking-coach"
C:\venvs\writing-coach\Scripts\Activate.ps1
python evaluation/pull_sheet.py                       # tất cả
python evaluation/pull_sheet.py --since 2026-10-15    # chỉ từ ngày này
```
→ `evaluation/results/live-<ngày-giờ>/`
| File | Là gì |
|---|---|
| `raw/<set_id>.md` | **1 file / 1 bộ câu hỏi học sinh làm** — đúng trang học sinh thấy: tổng kết bộ → từng câu → nâng cấp → bài nói lại. Mỗi mục có nhãn `[S1.w2]`… khớp với dòng trong CSV |
| `raw/review_items.csv` | **1 dòng = 1 thứ học sinh được thấy**, nguyên văn → bạn chấm ở 4 cột cuối |
| `summary.csv` | Số liệu từng câu (không có chữ) → commit được |

## 2. Cách đọc + chấm
1. Mở file `.md` của một bộ → đọc như học sinh đọc.
2. Mở `review_items.csv` (Excel), lọc theo `set_id` của bộ đó → chấm từng dòng.
3. Lưu: **File → Save as → CSV UTF-8** (giữ tên file).
4. Chạy:
```powershell
python evaluation/score.py evaluation/results/live-<ngày-giờ>/raw/review_items.csv
```
→ bảng ✓ % theo từng nhóm → dán vào `evaluation/EXPERIMENTS.md` → báo Claude **"đọc review speaking"**.

> Chấm trên app (mã reviewer) cũng được: ✓/~/✗ ở từng thẻ → tự hiện thành cột `<tên>_verdict` trong CSV. Tiện khi ngồi thử cùng học sinh.

## 3. Các dòng trong CSV (item_id)

| item_id | Học sinh thấy gì | Câu hỏi khi chấm |
|---|---|---|
| `ANSWER` | (câu trả lời của học sinh + chỗ tiếng Việt code tìm thấy) | Chỉ để đọc — không cần chấm |
| `L` | Trình độ ước lượng | Đúng với học sinh bạn biết không? (`should_be` = trình độ đúng) |
| `SUM.strength` | Câu khen 👍 | Có cụ thể, có thật không? |
| `S1` | Chỗ bí: «tiếng Việt» → "Ý bạn muốn nói" + "Vì sao hay bí" | Hiểu **đúng ý** học sinh chưa? Giải thích "vì sao bí" có đúng cách bạn nghĩ không? |
| `S1.w1`, `S1.w2`, `S1.w3` | **Từng cách nói đơn giản** + nhãn chiến lược + 1 câu giải thích | **Phần quan trọng nhất.** Có thật sự dễ với học sinh này? Đúng tinh thần "dùng từ đã biết"? Nhãn chiến lược đúng không? |
| `S1.adv` | ⭐ Từ xịn + câu ví dụ | Đúng nghĩa, tự nhiên không? |
| `E1` | Đoạn tiếng Anh → loại nhận xét → vì sao → câu tốt hơn | Có đáng nhận xét không, hay bắt bẻ lỗi nhỏ? |
| `O` / `O.w1`, `O.w2` | Ý chính / 2 cách nói khác | Có khác nhau **về cách nghĩ** không, hay chỉ đổi vài từ? |
| `SUM.habit` | 🎯 Thói quen cần luyện | Có đúng điều học sinh này cần nhất? |
| `X1` | (không thấy gì — code thấy tiếng Việt nhưng tool **không dạy**) | ✗ = tool bỏ sót thật |
| `UP` | Cả bài trước ⟶ sau nâng cấp | Còn là bài **của học sinh**? Lên đúng +1? |
| `U1`–`U4` | Từng chỗ nâng cấp + loại + vì sao | Tự nhiên hơn mà **không** dùng từ khó? Học sinh nói lại được không? |
| `UP.task` | Nhiệm vụ nói lại | Rõ ràng, làm được không? |
| `RETELL` | (học sinh gõ lại sau nâng cấp, nếu gửi) | Học sinh có dùng được chỗ nâng cấp không? → ghi ở `comment` |
| `M1`… | **Bạn tự thêm dòng** | Điều quan trọng tool bỏ sót |

## 4. Cột bạn điền
- **verdict**: `✓` đúng, dùng được ngay · `~` đúng nhưng cần chỉnh · `✗` sai / gây hại / học sinh sẽ học sai
- **problem** (khi `~` / `✗`): `wrong_meaning` hiểu sai ý · `too_hard` vượt trình độ · `not_simple` vẫn "đi tìm từ khó" · `unnatural` người bản xứ không nói vậy · `wrong_strategy` gắn sai nhãn chiến lược · `too_many_changes` nâng cấp đổi quá nhiều · `unclear_vi` giải thích tiếng Việt khó hiểu · `missed` bỏ sót · `other`
- **comment**: 1 câu **vì sao** — dữ liệu quan trọng nhất để sửa prompt
- **should_be**: câu bạn sẽ dạy trên lớp

## 5. Thứ tự ưu tiên (giai đoạn đầu: chấm hết; khi nhiều bài: theo thứ tự này)
1. `S*.w*` — cách nói đơn giản (lõi của tool)
2. `X*` — tool bỏ sót
3. `S*` — hiểu đúng ý học sinh chưa
4. `U*`, `UP` — nâng cấp
5. Còn lại

Nếu cùng một lỗi lặp lại ≥ 3 lần → đó là thứ sửa ở vòng sau. Mỗi vòng sửa **một** thứ.

## 6. Eval offline (thử thay đổi trước khi đưa lên app)
```powershell
python evaluation/run_eval.py --tag v2                     # data/samples
python evaluation/run_eval.py --tag v2 --dir data/gold     # bộ câu thật cố định (gitignore)
python evaluation/score.py evaluation/results/v2/raw/review_items.csv
```
`data/gold/`: chọn 10–15 câu trả lời thật, đa dạng (format: câu hỏi, dòng `---`, câu trả lời) → giữ cố định qua các vòng để so sánh.
