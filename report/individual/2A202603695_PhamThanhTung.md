# Báo cáo cá nhân — Day 6

**Học viên:** Phạm Thanh Tùng
**MSSV:** 2A202603695

## Dữ liệu và pipeline

- Corpus: Bộ luật Lao động số 45/2019/QH14; 94 trang vật lý, 93 trang có text.
- Nguồn, quyền và quy tắc đếm trang: xem `starter/data/manifest.json`.
- Pipeline: `pypdf` → Unicode/whitespace normalization → chunking → `paraphrase-multilingual-MiniLM-L12-v2` → Qdrant local (cosine search).
- Metadata: `document_id`, `source`, `page`, `document_type`, `year`, `chapter`.

## Cấu hình và benchmark

- A: fixed-size 500 ký tự, overlap 50, không filter.
- B: paragraph-aware, tối đa 500 ký tự, không filter.
- C: giống B, filter `chapter` khi câu hỏi cung cấp filter.
- Benchmark: 20 câu, 15 dev / 5 test; gold evidence và trang nằm tại `starter/data/questions.json`.
- Tiêu chí chọn: ưu tiên Evidence Hit@3 trên dev, sau đó grounding và chi phí.

## Kết quả tự động

| Strategy | Split | Hit@1 | Evidence Hit@3 |
|---|---|---:|---:|
| A | Dev | 1/15 | 1/15 |
| A | Test | 0/5 | 0/5 |
| B | Dev | 1/15 | 1/15 |
| B | Test | 0/5 | 0/5 |
| C | Dev | 1/15 | 1/15 |
| C | Test | 0/5 | 0/5 |

Trace: `starter/results/traces.json`. Metrics: `starter/results/metrics.json`.

## Audit thủ công và phân tích

Đã audit 10 vị trí nguồn giống nhau cho cả ba chiến lược. Điểm coherence trung bình: A = **1.2/2**, B = **1.1/2**, C = **1.1/2**. Phần lớn chunk có chủ đề đúng nhưng bị cắt giữa câu hoặc giữa một danh sách; A có hai chunk trọn ý ở trang 10 (Điều 21) và trang 12 (Điều 28), nên điểm trung bình cao hơn một chút. C dùng cùng ranh giới chunk với B nên coherence của hai chiến lược là tương đương.

Audit top-3 của 5 câu test cho mỗi chiến lược cho thấy metadata `document_id`, `source` và `page` đều có mặt (15/15 lượt kiểm tra). Với C, filter chương được tuân thủ cho q16 (Chương VI) và q17 (Chương VII). Tuy nhiên grounding của cả A/B/C là **0/2 cho 5 câu test**, phù hợp với Evidence Hit@3 = 0/5: không có top-3 nào chứa evidence vàng tương ứng.

Hai ví dụ lỗi từ trace:

- **q16, chiến lược A**: gold evidence ở trang 44 (Điều 98 khoản 3), nhưng top-1 là `bo-luat-lao-dong-2019:p42:fixed_size:0001`; top-3 chỉ thuộc trang 41–42. Chunk gần chủ đề tiền lương/làm thêm nhưng không chứa quy định trả thêm 20%.
- **q20, chiến lược B**: gold evidence ở trang 17 (Điều 35 khoản 2 điểm b), nhưng top-1 là `bo-luat-lao-dong-2019:p18:paragraph:0003`, sau đó là các chunk trang 19. Kết quả không chứa câu evidence về việc không được trả đủ lương hoặc trả lương không đúng hạn.

Nguyên nhân chính quan sát được là văn bản PDF có khoảng trắng/tách ký tự bất thường sau khi trích xuất, làm giảm chất lượng embedding; thêm vào đó, evidence có thể bị chia qua ranh giới chunk. Cần cải thiện bước làm sạch văn bản và thử thông số chunk trên tập dev trước khi đánh giá lại test. Không dùng kết quả test hiện tại để tinh chỉnh.

## Artifact nộp kèm

- Manifest: `starter/data/manifest.json`
- Benchmark + gold: `starter/data/questions.json`
- Experiment log: `artifacts/experiment_log.csv`
- Trace top-3: `starter/results/traces.json`
- Metrics: `starter/results/metrics.json`
- Mẫu nhãn thủ công: `starter/results/manual_audit_template.md`

## Giới hạn

- Audit thủ công do một người thực hiện nên có thể có thiên lệch đánh giá.
- Kết quả retrieval hiện thấp và không nên được diễn giải là hệ thống trả lời pháp lý đáng tin cậy.
- `gold_page` phải tiếp tục được đối chiếu với quy tắc đánh số trang trong manifest trước khi dùng để tinh chỉnh hoặc so sánh kết quả mới.
