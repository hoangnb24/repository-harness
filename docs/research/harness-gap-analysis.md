# Harness cần những tính năng gì, và repository-harness đang ở đâu

Status: research, not a release gate.

Đối chiếu khoá [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) với repo `HustWibu/repository-harness`, nhánh `feat/measure-budget-authority` (commit `1469886`), ngày 2026-11-02.

Phạm vi đã đọc: trang tổng quan, trang Templates, và các bài L4 đến L14. Bài L1 đến L3 chỉ đối chiếu qua tiêu đề và phần tổng quan. Mục "Skills" và "Harness Designs" của khoá chưa đọc.

## Cách đọc

| Trạng thái | Nghĩa |
| --- | --- |
| ✅ Có | Repo đáp ứng, có file hoặc test làm bằng chứng |
| 🟡 Một phần | Có nền tảng nhưng thiếu một mảnh rõ ràng |
| 🔴 Thiếu, nên thêm | Không mâu thuẫn với triết lý của repo, thêm được ở dạng template hoặc hướng dẫn |
| ⚪ Cố ý không có | Repo đã quyết định không làm. Lý do và nguồn nằm ở phần 3 |

## 1. Danh sách tính năng

### A. Context và nguồn sự thật

| ID | Tính năng (bài) | Trạng thái | Bằng chứng trong repo |
| --- | --- | --- | --- |
| A1 | Repo là nguồn sự thật, không dựa vào lịch sử hội thoại (L3) | ✅ | `AGENTS.md`, `docs/WORKFLOW.md`, `docs/README.md` |
| A2 | File điểm vào ngắn, chi tiết tách ra các tài liệu theo chủ đề (L4) | ✅ | Khối harness trong `AGENTS.md` 1.241 byte; skill chỉ nạp khi được gọi; `docs/README.md` là bản đồ |
| A3 | Có cơ chế giữ file điểm vào luôn nhỏ (L4, L13) | ✅ | `scripts/context-budget.tsv` và `tests/docs/test-context-budget.sh`, chạy trong pre-merge |
| A4 | Mỗi chỉ dẫn ghi nguồn gốc, khi nào áp dụng, khi nào hết hạn (L4) | 🟡 | Decision ghi Context và Consequences; pattern encoding có trường Authority. Chưa có quy ước "khi nào xoá chỉ dẫn" |
| A5 | Nhật ký quyết định nhẹ (L5, L6) | ✅ | `docs/decisions/` và `docs/templates/decision.md`, có frontmatter duyệt |
| A6 | Skills đóng gói quy ước và quy trình (L13) | ✅ | 5 skill trong `.agents/skills/`, chỉ chạy khi gọi tường minh |

### B. Khởi tạo và liên tục giữa các phiên

| ID | Tính năng (bài) | Trạng thái | Bằng chứng / chỗ thiếu |
| --- | --- | --- | --- |
| B1 | Lệnh khởi động và kiểm tra chuẩn của repo (L6, `init.sh`) | 🟡 | Template `application-runbook.md` có Start, Readiness, Validation. Không ship `init.sh` (cố ý, xem C-1 ở phần 3) |
| B2 | Kiểm "phiên mới có tự biết cách chạy và test không" (L6) | 🟡 | `$onboard-repository` lần theo một luồng vận hành thật; `$audit-onboarding-proposal` kiểm độc lập. Chưa có checklist sẵn sàng ngắn |
| B3 | File tiến độ và thói quen đọc khi vào phiên, ghi khi ra phiên (L5) | 🟡 | `docs/plans/active/` và `exec-plan.md` có mục Progress, nhưng chỉ dành cho việc dài nhiều phiên. Chưa có template bàn giao ngắn |
| B4 | Chuẩn bị bàn giao khi context đã dùng khoảng 60% (L5) | 🔴 | Chưa có. Thêm được dưới dạng một câu hướng dẫn |
| B5 | Commit mỗi đơn vị việc làm checkpoint (L5, L7) | ⚪ | Quy trình commit do repo dùng harness quyết định (xem C-2) |

### C. Phạm vi và định nghĩa "xong"

| ID | Tính năng (bài) | Trạng thái | Bằng chứng / chỗ thiếu |
| --- | --- | --- | --- |
| C1 | Danh sách feature máy đọc được, có trạng thái (L7, L8) | ⚪ | Lý do ở C-3 |
| C2 | Chỉ một việc đang làm tại một thời điểm, chỉ verifier được đặt `passing` (L7, L8) | ⚪ | Lý do ở C-3 |
| C3 | Định nghĩa "xong" viết thành văn bản (L9) | 🟡 | Decision 0019 mục 7 viết "Completion requires executable or observable evidence"; `WORKFLOW.md` có mục "Trust Through Evidence". **Chưa có mục Definition of Done ngắn, dễ thấy** |
| C4 | Thiếu bằng chứng thì tính là chưa xong (L9) | 🟡 | Mới có nguyên tắc ở `docs/patterns/encoding-invariants.md` mục 6. Không có script cổng (cố ý, xem C-1) |
| C5 | Harness tự chạy bước kiểm kết thúc, không tin lời agent (L9) | ⚪ | Lý do ở C-1 |
| C6 | Ba tầng kiểm: unit, integration, e2e (L9, L10) | ⚪ | Lệnh test do repo dùng harness sở hữu (C-1) |
| C7 | Checklist "phiên kết thúc sạch" (L12) | 🔴 | Chưa có. Thêm được dưới dạng template tuỳ chọn |

### D. Mã hoá luật và kiểm tra

| ID | Tính năng (bài) | Trạng thái | Bằng chứng |
| --- | --- | --- | --- |
| D1 | Mỗi luật kiến trúc có check chạy được, chạy trong CI (L10, L12) | ✅ | `$encode-invariant` và pattern; repo tự áp dụng qua `crates/harness/tests/clean_architecture.rs` |
| D2 | Thông báo lỗi viết cho agent: cái gì sai, vì sao, sửa thế nào (L9, L10) | ✅ | Pattern bước 3; `check-context-budget.sh` in ERROR/WHY/FIX |
| D3 | Chứng minh hai chiều: ca đúng pass, ca vi phạm fail (L10) | ✅ | Pattern bước 4; các test ngân sách và kiến trúc |
| D4 | Biến góp ý review lặp lại thành check tự động (L10, L12) | ✅ | Pattern mục 7 "Promote Guidance To A Gate Deliberately" |
| D5 | Agent kiểm tra độc lập với agent viết code (L9, L13, L14) | 🟡 | Chỉ có cho onboarding (`$audit-onboarding-proposal`). Chưa có skill review chung; nằm trong backlog của REQUIREMENTS, chờ số liệu từ `skill-report` |
| D6 | Rubric chấm điểm đầu ra: Accept, Revise, Block (L9, L11) | 🔴 | Chưa có. Thêm được dưới dạng template tuỳ chọn |
| D7 | Quality document chấm điểm từng module theo thời gian (L12) | 🔴 | Chưa có. Thêm được dưới dạng template tuỳ chọn, ưu tiên thấp |

### E. Đo lường và bảo trì harness

| ID | Tính năng (bài) | Trạng thái | Bằng chứng |
| --- | --- | --- | --- |
| E1 | Tắt thử một thành phần, chạy lại, giữ hoặc bỏ theo kết quả (L12) | ✅ | `$improve-harness`: baseline, chạy lại từ đầu, keep/revise/remove; template `harness-improvement.md` |
| E2 | Đo agent có làm theo skill không, tốn bao nhiêu token (L4, L13) | ✅ | `harness skill-report` và dòng biên nhận `HARNESS_SKILL:` |
| E3 | So sánh trên cùng một bộ task trước và sau khi đổi chỉ dẫn (L4) | 🟡 | `$improve-harness` làm trên một task đại diện. Chưa có bộ task chuẩn để benchmark |
| E4 | Trace từng phiên agent theo chuẩn OpenTelemetry (L11) | ⚪ | Lý do ở C-4 |

### F. Runtime, vòng lặp, đồ thị

| ID | Tính năng (bài) | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| F1 | Quan sát runtime ứng dụng: log, trace, metric, health (L11) | ⚪ | Lý do ở C-5 |
| F2 | Vòng lặp tự động: trigger, giới hạn ngân sách, điều kiện dừng (L13) | ⚪ | Lý do ở C-6 |
| F3 | Đồ thị nhiều agent: state chung, node, edge, checkpoint, veto (L14) | ⚪ | Lý do ở C-6 |

### Ngoài khoá học: điểm mạnh riêng của repo

| Tính năng | Bằng chứng |
| --- | --- |
| Cài và cập nhật an toàn: three-way merge, backup, conflict do người quyết | `crates/harness`, decision 0025 |
| Phân định thứ gì do harness sở hữu, thứ gì do repo dùng harness sở hữu | decision 0020, `docs/ARCHITECTURE.md` |
| Cổng thẩm quyền: không suy ra chính sách từ quy ước có sẵn | `AGENTS.md`, `$encode-invariant` bước 2 |

## 2. Thiếu nhưng nên thêm

Các mục này không mâu thuẫn với triết lý của repo, vì chúng chỉ là chữ hoặc template tuỳ chọn và không thêm bộ máy nào.

| Ưu tiên | Mục | Làm thế nào | Công |
| --- | --- | --- | --- |
| 1 | C3 Definition of Done | Thêm vài dòng vào `docs/WORKFLOW.md`: "xong" nghĩa là có bằng chứng xác minh hợp với hành vi đã đổi; thiếu bằng chứng thì báo là chưa xác minh | Rất nhỏ |
| 2 | B3, B4 Bàn giao giữa phiên | Template `docs/templates/session-handoff.md`: đã xác minh gì, đổi gì, còn hỏng gì, bước tiếp theo, lệnh dùng. Kèm câu "chuẩn bị bàn giao trước khi context đầy" | Nhỏ |
| 3 | C7 Phiên kết thúc sạch | Template `clean-state-checklist.md` | Nhỏ |
| 4 | D6 Rubric | Template `evaluator-rubric.md` với 6 tiêu chí chấm 0–2 | Nhỏ |
| 5 | A4 Hạn dùng chỉ dẫn | Thêm vào pattern: mỗi chỉ dẫn hoặc check ghi điều kiện để gỡ bỏ | Rất nhỏ |
| 6 | D7 Quality document | Template tuỳ chọn | Nhỏ, giá trị thấp lúc đầu |
| 7 | D5, E3 Review độc lập, bộ benchmark | Chờ có số liệu `skill-report` rồi mới quyết | Vừa |

Template mới phải khai trong `scripts/harness-install-files.txt` và được nhúng vào binary. Khối `AGENTS.md` cũng phải nằm trong ngân sách context.

## 3. Cố ý không có: lý do và nguồn

Nguyên tắc gốc nằm trong `AGENTS.md` của repo:

> Consumer repositories own their task workflow and planning. Harness provides context and optional tools, without a task database or orchestration lifecycle.

Và `docs/HARNESS.md`:

> It supplies no fabricated product domains, application commands, credentials, task scheduler, database, or workflow engine.

### C-1. Không ship `init.sh`, script cổng, hay lệnh test (B1, C4, C5, C6)

- **Lý do:** Lệnh build, test và khởi động khác nhau theo từng stack. Harness không biết "bằng chứng" là gì ở repo người dùng. Một script chung mà không ai nối vào CI chỉ tạo cảm giác an toàn giả.
- **Nguồn:**
  - `docs/HARNESS.md`: "Consumer repositories own their workflows, planning, application operation, architecture, and validation commands."
  - Decision 0029, mục "Alternatives Considered" 1 và 2.
- **Thay vào đó:** template `application-runbook.md`, nguyên tắc fail-closed trong pattern, và `$encode-invariant` để mỗi repo tự làm cổng thật.
- **Khi nào xem lại:** nếu harness chỉ phục vụ vài repo cùng một stack mà bạn kiểm soát.

### C-2. Không áp quy trình commit hay checkpoint (B5)

- **Lý do:** Quy trình làm việc thuộc về repo dùng harness. Việc nhỏ và việc lớn cần lượng ghi nhớ và bằng chứng khác nhau.
- **Nguồn:** decision 0019, phương án bị bác 1: "Require one lifecycle for every task. Rejected because work shape, not a global process ladder, determines the memory and proof required."

### C-3. Không có feature list, trạng thái task, giới hạn WIP, verifier đổi trạng thái (C1, C2)

- **Lý do:** Đây chính là "task database / lifecycle" mà repo **đã từng có rồi gỡ bỏ**: SQLite control plane, story packets, protocol v1. Theo decision 0027, bộ máy đó chiếm phần lớn công bảo trì ngay cả khi không thêm tính năng nào, và tạo ra một nguồn sự thật thứ hai song song với repo.
- **Nguồn:**
  - Decision 0027, mục 1: "Protocol v1 and the optional SQLite control plane are end-of-life."
  - Decision 0027, phương án bị bác 2: "its source, data, release, installer, and validation surfaces continue to dominate maintenance even when no features are added."
  - Decision 0020: payload không có "a database, schemas, orchestration, or background processes".
  - Decision 0019, hệ quả: "Complex work remains resumable without duplicate task truth."
- **Thay vào đó:** `docs/plans/active/` cho việc kéo dài nhiều phiên. Repo dùng harness tự chọn công cụ quản lý task.
- **Khi nào xem lại:** chỉ khi đổi hướng sản phẩm. Lúc đó cần một decision mới thay decision 0027.

### C-4. Không có telemetry hay trace của agent (E4)

- **Lý do:** Harness không chạy tiến trình nền và không gửi dữ liệu ra ngoài. Đo lường chỉ diễn ra khi người dùng gọi và đọc log có sẵn ở máy.
- **Nguồn:** decision 0020 (không background process); REQUIREMENTS, ràng buộc CON-3 ("không thêm orchestration, tiến trình nền, hook mặc định, telemetry").
- **Thay vào đó:** `harness skill-report` đọc log phiên của Claude Code. Không ghi gì, chỉ in số liệu tổng hợp.

### C-5. Không quan sát runtime của ứng dụng (F1)

- **Lý do:** Runtime, credentials, fixtures, log và dọn dẹp thuộc về ứng dụng của repo dùng harness. Harness không thể làm cổng phát hành một cách trung thực cho khả năng nó không sở hữu.
- **Nguồn:**
  - Decision 0027, phương án bị bác 4: "application runtime, credentials, fixtures, logs, and cleanup are consumer-owned. They cannot be an honest release gate for capabilities Harness does not own."
  - `docs/ARCHITECTURE.md`: "It does not own the consumer's product, runtime, orchestration, credentials…"
- **Thay vào đó:** mục Runtime Evidence trong `application-runbook.md`.

### C-6. Không có vòng lặp tự động hay đồ thị nhiều agent (F2, F3)

- **Lý do:** Đây là workflow engine hoặc orchestration. Mọi skill của harness phải được người dùng gọi tường minh. Việc chạy lặp lại đã có sẵn trong công cụ agent (ví dụ `/loop`, scheduled tasks của Claude Code).
- **Nguồn:**
  - `docs/HARNESS.md`: "All Harness skills require explicit user invocation" và "no … task scheduler … or workflow engine".
  - Decision 0020 (không orchestration).
  - REQUIREMENTS, mục "Ngoài phạm vi": "DAG hoặc điều phối nhiều agent…".
- **Khi nào xem lại:** khi có nhu cầu thật được đo bằng số liệu, và chấp nhận đổi hướng sản phẩm.

## 4. Tóm tắt

- **Đạt tốt:** context gọn, repo là nguồn sự thật, mã hoá luật thành check, đo lường và bảo trì harness. Đây là các bài L3, L4, L10, L12 và một phần L13.
- **Thiếu nhưng thêm rẻ:** Definition of Done, template bàn giao, clean-state checklist, rubric. Đây là các bài L5, L9, L12.
- **Cố ý không làm:** quản lý task, verifier đổi trạng thái, telemetry, runtime ứng dụng, vòng lặp và đồ thị. Đây là các bài L7, L8, L11, L13, L14. Lý do chung: repo đã thử mô hình control plane, thấy chi phí bảo trì quá lớn và gỡ bỏ nó (decision 0027). Từ đó harness chỉ cung cấp context và công cụ tuỳ chọn; quy trình là việc của repo dùng harness.
