<!-- Synced from ../gap-analysis.md @ 2026-05-17. Re-sync after default updates. -->

# Phân tích khoảng cách (Gap Analysis) — <tên dự án>

Ngày: YYYY-MM-DD · Trạng thái: nháp | khách đã review | đã duyệt · Lượt: 1

> Brief do vendor sản xuất, so sánh trạng thái hiện tại (As-Is) của khách với trạng thái tương lai mong muốn (To-Be) và cấu trúc các khoảng cách + giải pháp. Đóng băng trước khi SOW § 4 in-scope chốt.
>
> Sống tại `docs/intake/YYYY-MM-DD-gap-analysis.md`. Sản xuất bằng `docs/playbooks/gap-analysis.md` sau khi `docs/playbooks/discovery-interview-playbook.md` đã đưa ra REQ list.

## 1. To-Be (Trạng thái tương lai)

Khách muốn thế giới trông như thế nào sau khi dự án ship.

### Mục tiêu kinh doanh

- Mục tiêu 1 (một dòng, đo lường được nếu có thể).
- Mục tiêu 2.

### Tiêu chí thành công

Khách biết "đã đạt" bằng cách nào.

| Chỉ số | Hôm nay (baseline) | Mục tiêu | Đo lúc |
| --- | --- | --- | --- |
| <e.g. thời gian xử lý đơn> | <e.g. TB 24h> | <e.g. < 4h TB> | <e.g. 30 ngày sau launch> |

### Người dùng mục tiêu × hành động mục tiêu

| Vai trò | Sẽ làm được gì (To-Be) |
| --- | --- |
| Customer | Tự kiểm tra trạng thái đơn hàng 24/7 trên app |
| Staff | Nhận thông báo đơn hàng + cập nhật trạng thái từ dashboard |

### Ràng buộc

- Deadline: <ngày>
- Khoảng ngân sách: <range>
- Quy định pháp lý: <e.g. PCI-DSS, GDPR, không>
- Hệ thống đang chạy phải giữ: <list>

## 2. As-Is (Trạng thái hiện tại)

Khách đang làm gì hôm nay. Capture từ discovery interview, source docs, và `docs/discovery/` raw inputs.

### Bản đồ quy trình hiện tại

Các bước đánh số, ai làm gì, đâu là điểm đau. Nếu có hoặc sẽ có Mermaid flowchart của quy trình hiện tại, trích về: `docs/visuals/diagrams/business-workflow-as-is.md`. Ở stage 3 (brief này), văn bản là đủ — sơ đồ chính thức xuất hiện ở stage 6.

1. <Actor X> làm <hành động> qua <kênh> → kết quả.
2. <Actor Y> làm <hành động> → bàn giao cho <Actor Z>.
3. ...

### Hệ thống hiện tại

| Hệ thống | Mục đích | Sở hữu bởi | Tích hợp với | Điểm đau |
| --- | --- | --- | --- | --- |
| <e.g. Excel sổ đơn hàng> | Theo dõi đơn hàng thủ công | Nhân viên sale | Không có — nhập thủ công | Trùng entry, mất đơn |

### Điểm đau (nguyên văn nếu có thể)

Trích nguồn: `docs/discovery/2026-05-17-kickoff-notes.md § 4`.

- Đau 1: <một dòng>. Trích: <nguồn>.
- Đau 2: <một dòng>. Trích: <nguồn>.

### Workaround user tự nghĩ ra

- <e.g. khách gọi tổng đài nhiều lần để check trạng thái vì không có trang tracking>.

### Stakeholder trong As-Is

| Vai trò | Trách nhiệm hiện tại | Bị ảnh hưởng bởi thay đổi? |
| --- | --- | --- |
| CSKH | Xử lý cuộc gọi check trạng thái | có — workload giảm khi tự phục vụ |
| Nhân viên sale | Nhập đơn thủ công vào Excel | có — thay bằng capture tự động |

## 3. Khoảng cách (The Gap)

Phân loại. Mỗi hàng có token `GAP-NNN` local-to-brief. Token trace tiếp tới REQ khi cắt stories.

### Khoảng cách chức năng (thiếu tính năng)

| GAP ID | Mô tả | Mức độ | As-Is touch | To-Be touch |
| --- | --- | --- | --- | --- |
| GAP-001 | Không có giao diện cho khách check trạng thái đơn | Cao | Khách gọi tổng đài | Khách mở app, xem trạng thái |
| GAP-002 | Không có realtime notification cho staff khi có đơn mới | Trung bình | Staff poll email | Push notification trên điện thoại |

### Khoảng cách quy trình (workflow thiếu hoặc hỏng)

| GAP ID | Mô tả | Mức độ | Liên kết Plan-of-action |
| --- | --- | --- | --- |
| GAP-010 | Order intake không có bước validation trước khi chuyển kho | Cao | Thêm bước validation + UI gate |

### Khoảng cách công nghệ (hệ thống không tích hợp)

| GAP ID | Mô tả | Mức độ | Liên kết Plan-of-action |
| --- | --- | --- | --- |
| GAP-020 | Excel sổ đơn hàng không kết nối với hệ thống tồn kho | Cao | Thay Excel + tích hợp với inventory API mới |

### Khoảng cách dữ liệu (dữ liệu không được capture / không truy cập được)

| GAP ID | Mô tả | Mức độ | Liên kết Plan-of-action |
| --- | --- | --- | --- |
| GAP-030 | Customer satisfaction không được track ở đâu | Trung bình | Thêm NPS survey sau fulfillment |

### Khoảng cách vai trò / kỹ năng (người không có quyền hoặc training)

| GAP ID | Mô tả | Mức độ | Liên kết Plan-of-action |
| --- | --- | --- | --- |
| GAP-040 | Staff không có admin account trên tool hiện tại — chỉ chủ có | Thấp | Thêm staff role + buổi training khi handover |

### Khoảng cách tuân thủ (quy định chưa đáp ứng)

| GAP ID | Mô tả | Mức độ | Liên kết Plan-of-action |
| --- | --- | --- | --- |
| GAP-050 | Không có consent capture cho email marketing | Cao (pháp lý) | Thêm consent checkbox + retention policy |

Thang mức độ: **Cao** = chặn To-Be / rủi ro pháp lý. **Trung bình** = chặn mục tiêu nhưng có workaround. **Thấp** = nên có.

## 4. Plan of Action (Kế hoạch hành động)

Mỗi gap có một hàng giải pháp. Ưu tiên MoSCoW trực tiếp dẫn quyết định SOW § 4 in-scope.

| GAP ID | Hình thức giải pháp | Chủ trách nhiệm | Effort | Ưu tiên (MoSCoW) | Story candidate | Trong SOW § 4? |
| --- | --- | --- | --- | --- | --- | --- |
| GAP-001 | Build trang "Trạng thái đơn" trên app khách + status API | Vendor | L (16-40h) | **Must** | `US-001-order-status-view` | có |
| GAP-002 | Push notification cho điện thoại staff qua FCM | Vendor | M (4-16h) | **Should** | `US-002-staff-order-notif` | có |
| GAP-010 | Thêm bước validation trong workflow order-intake | Vendor | M | **Must** | `US-003-order-validation-gate` | có |
| GAP-020 | Inventory API mới + migrate dữ liệu Excel | Vendor | XL (> 40h) | **Should** | `US-004-inventory-integration` | một phần — phase 1 read-only, phase 2 write |
| GAP-030 | NPS survey sau fulfillment | Vendor | S (1-4h) | **Could** | `US-005-nps-survey` | không — phase 2 |
| GAP-040 | Staff role + buổi training | Cả hai | S | **Must** | `US-006-staff-role-handover` | có (trong scope handover) |
| GAP-050 | Consent capture + retention policy doc | Vendor | M | **Must** | `US-007-consent-capture` | có |

Chú giải MoSCoW:

- **Must** — chặn tầm nhìn To-Be HOẶC quy định pháp lý. Bắt buộc trong SOW § 4.
- **Should** — giá trị đáng kể nhưng không chặn. SOW § 4 nếu ngân sách cho phép.
- **Could** — nên có. Mặc định vào SOW § 5 (out-of-scope) hoặc phase 2.
- **Won't** — rõ ràng ngoài dự án này. Document lý do trong `docs/decisions/`.

## Out-of-Scope từ brief này

Gap khách nhắc nhưng team chọn không xử lý bây giờ. Mỗi gap trích lý do và sẽ đi đâu (phase 2, vendor khác, từ chối).

| GAP ID | Mô tả | Tại sao out | Định hướng |
| --- | --- | --- | --- |
| GAP-099 | UI đa ngôn ngữ (5 thứ tiếng) | Vượt ngân sách phase 1 | SOW phase 2 (sau launch) |

## Rủi ro phát hiện

Rủi ro gap analysis bóc tách (khác với gap — là điều kiện có thể derail việc đóng gap).

| Rủi ro | Khả năng | Ảnh hưởng | Biện pháp giảm thiểu |
| --- | --- | --- | --- |
| Chất lượng dữ liệu Excel tệ hơn khách nói | Trung bình | Cao | Spike tuần 1 — lấy mẫu 100 hàng, báo cáo |
| Staff kháng cự training | Thấp | Trung bình | Handover bao gồm 2 buổi + tài liệu hướng dẫn |

## Câu hỏi mở

Câu hỏi gap analysis KHÔNG giải quyết được. Hoặc trả lời trước khi ký SOW, hoặc log vào `docs/HARNESS_BACKLOG.md`.

- Q1: PIM hiện tại có export API không hay phải scrape?
- Q2: Cơ quan quy định yêu cầu giữ dữ liệu đơn hàng bao lâu?

## Ký nghiệm thu

| Mốc | Ngày | Người duyệt | Ghi chú |
| --- | --- | --- | --- |
| Vendor draft xong | YYYY-MM-DD | <vendor> | Lượt 1 |
| Khách review | YYYY-MM-DD | <tên khách> | Lượt 1 — chấp nhận với chỉnh sửa ưu tiên GAP-020 |
| Đóng băng (pre-SOW § 4) | YYYY-MM-DD | <vendor + khách> | Final |

Sau khi đóng băng, thay đổi gap đi qua `docs/templates/change-request-log.md`. Không sửa analysis tại chỗ — ghi chú trỏ tới CR.

## Cross-References

- Đầu ra discovery interview: `docs/intake/YYYY-MM-DD-discovery-summary.md` (nguồn REQ list).
- Client intake brief: `docs/intake/YYYY-MM-DD-intake-brief.md` (nguồn business problem).
- Raw inputs trích dẫn: `docs/discovery/YYYY-MM-DD-<slug>.{ext}` rows.
- Forward: SOW § 4 in-scope (`docs/templates/proposal-sow.md`).
- Forward: cắt story (`docs/stories/epics/`).
- Sơ đồ quy trình As-Is (stage 6, nếu dự án UI): `docs/visuals/diagrams/business-workflow-as-is.md`.
- Bản gốc tiếng Anh: `docs/templates/gap-analysis.md`.
