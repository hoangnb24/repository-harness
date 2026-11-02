# Yêu cầu bổ sung cho repository-harness

Status: research, not a release gate.

Phạm vi: thêm bốn khả năng vào payload của `repository-harness`, theo cách vẫn giữ nguyên triết lý của nó. Mỗi yêu cầu có một cột **Kiểm** là cách chứng minh đã đạt. Câu chữ nằm trong repo (template, thông báo lỗi, SKILL.md) viết bằng tiếng Anh để khớp với phần còn lại của repo. Phần giải thích viết bằng tiếng Việt.

Bốn khả năng, theo thứ tự nên làm:

1. **TOK**: ngân sách context, giữ phần agent phải nạp ở mỗi phiên nhỏ và đo được.
2. **AUTH**: dấu hiệu máy kiểm được cho "thẩm quyền đã được duyệt".
3. **GATE**: cổng "xong" fail-closed, dạng template.
4. **RCPT**: biên nhận cuối mỗi skill, kèm lệnh đo mức tuân thủ và token.

Lý do thứ tự: TOK làm trước vì ba khả năng sau đều thêm chữ vào skill và tài liệu, nên cần có ngưỡng chặn trước khi chúng phình ra. AUTH nối thẳng vào cổng thẩm quyền của `$encode-invariant`. GATE độc lập. RCPT đo hành vi của các khả năng trước nên làm sau cùng.

Kèm một tài liệu hướng dẫn (DOC) về khi nào nâng một lời dặn thành cổng chặn.

## Hiện trạng đã đối chiếu với repo (commit `485fd40`, 2026-11-02)

Các con số dưới đây đo trực tiếp trên repo, dùng làm mốc cho TOK-5 và để người hiện thực không giả định sai.

| Điểm | Hiện trạng | Ảnh hưởng tới yêu cầu |
| --- | --- | --- |
| `AGENTS.md` ở payload | Không phải file nguyên khối: harness chỉ sở hữu khối `<!-- HARNESS:BEGIN -->…<!-- HARNESS:END -->`, lấy từ `scripts/agent-harness-block.md` (1.241 byte). Khối Claude là `scripts/claude-harness-block.md` (241 byte) | TOK-1 phải đo khối harness, không đo cả `AGENTS.md` của repo dùng harness |
| Ngưỡng đã tồn tại | `tests/installer/assert-agent-authority-contract.sh` đã chặn khối agent ≤ 1600 byte, và tổng số từ của khối agent cộng `docs/WORKFLOW.md` ≤ 1000 | TOK-5 phải chuyển các ngưỡng này về chỗ khai duy nhất, không thêm bản thứ hai |
| Kích thước `SKILL.md` | `onboard-repository` 27.040 B; `audit-onboarding-proposal` 15.967 B; `improve-harness` 4.442 B; `engineering-wisdom` 3.640 B; `encode-invariant` 2.669 B | Nếu lấy "số đo cộng biên" làm một ngưỡng chung thì sẽ khóa cứng mức 27 KB. Xem TOK-7 |
| Độ dài `description` | 222 đến 298 ký tự. Mọi description đều mở đầu bằng câu bắt buộc "Use only when the user explicitly invokes `$…`" (khoảng 60 ký tự) | Ngưỡng TOK-2 phải chừa chỗ cho câu này |
| Skill được phân phối | Có hai manifest: `scripts/harness-install-files.txt` (core) và `scripts/engineering-wisdom-install-files.txt` (add-on, bật bằng `--with-engineering-wisdom` / `-WithEngineeringWisdom`) | "Mọi skill được phân phối" trong TOK-2, TOK-3, RCPT-1 phải duyệt cả hai manifest |
| Nhúng payload | Payload được nhúng vào binary bằng `include_bytes!` trong `crates/harness/src/infrastructure/embedded_distribution.rs` | Khai trong manifest thôi chưa đủ. Xem CON-8 |
| Template decision | `docs/templates/decision.md` không có frontmatter. Trạng thái nằm ở mục `## Status` trong thân, với bốn giá trị `Proposed \| Accepted \| Superseded \| Rejected`. Cả 7 decision hiện có (0020 đến 0028) đều dùng dạng này | AUTH-1 đang thiếu `rejected` và chưa nói gì về việc có hai nơi cùng ghi trạng thái. Xem AUTH-10, AUTH-11 |
| Windows | Có `scripts/install-harness.ps1` và `tests/installer/test-install-harness-modes.ps1` | Script mới viết bằng bash sẽ không chạy được trên máy chỉ có PowerShell. Xem CON-7 |
| CHANGELOG | `CHANGELOG.md` được sinh cho từng PR bởi `scripts/render-changelog-files.py`, không viết tay | DONE-3 cần sửa lại. Xem DONE-3 |
| Ví dụ GATE | Thư mục chứa file này **không có** `done-gate.sh` và `test-done-gate.sh` | Cần đính kèm hai file đó, hoặc bỏ câu tham chiếu ở cuối mục GATE |

## Ràng buộc chung (áp cho mọi khả năng)

| ID | Ràng buộc | Kiểm |
| --- | --- | --- |
| CON-1 | Không có gì tự kích hoạt khi cài. Mọi khả năng mới chỉ chạy khi người dùng gọi rõ ràng. | Cài mới vào repo trống, không có lệnh hay skill nào chạy. Test cài đặt hiện có vẫn pass |
| CON-2 | Không thêm trạng thái ẩn. Mọi artifact mới là file thường, đọc được, nằm trong repo. | Liệt kê file mới, không có file nằm ngoài repo hay trong thư mục ẩn mới |
| CON-3 | Không thêm orchestration, tiến trình nền, hook mặc định, telemetry. | Không có hook hay service mới trong payload |
| CON-4 | Mọi file mới nằm trong payload phải được khai trong `scripts/harness-install-files.txt`. | `tests/installer/assert-install-manifest-links.sh` pass |
| CON-5 | Không đặt sẵn lệnh validation của ứng dụng. Lệnh và đường dẫn cụ thể do repo dùng harness quyết định. | Đọc file mới, không có lệnh build/test cụ thể của một stack nào |
| CON-6 | Tương thích ngược. Tài liệu cũ không có trường mới vẫn đọc được và không bị tự ý sửa. | Chạy `harness update` trên repo mẫu có decision cũ, không file nào bị ghi đè ngoài vùng harness quản lý |
| CON-7 | Lệnh mới phải chạy được trên cả macOS/Linux và Windows: hoặc viết trong binary Rust `harness`, hoặc có bản bash kèm bản PowerShell cho cùng hành vi. Nếu có nền tảng không hỗ trợ thì phải ghi rõ trong `docs/product/`. | Test chạy trên cả hai shell, hoặc có tài liệu ghi rõ giới hạn |
| CON-8 | Mọi file payload mới phải được nhúng trong `embedded_distribution.rs`, liệt kê trong `docs/product/installation-profiles.md`, và đi qua cơ chế update/conflict hiện có. Không có đường ghi riêng. | `cargo test` pass; cài bằng binary vừa build có đủ file mới; update trên bản cài cũ gặp đúng conflict flow khi file đã bị sửa |
| CON-9 | Mỗi khả năng có một decision mới trong `docs/decisions/` (từ 0029 trở đi). Lý do: các khả năng này thay đổi hành vi bên ngoài nhìn thấy được, và `AGENTS.md` đòi phải có thẩm quyền trước khi làm. Decision mới dùng chính frontmatter của AUTH. | Có decision ở trạng thái accepted, được dẫn trong PR; lệnh AUTH chạy trên decision đó cho exit 0 |
| CON-10 | Không thêm phụ thuộc runtime mới ngoài những gì payload hiện đã yêu cầu. Nếu cần parse YAML thì chỉ hỗ trợ một tập con được khai báo, không kéo thư viện YAML vào. | So `Cargo.toml` và yêu cầu runtime trước và sau; tài liệu nêu tập con frontmatter được hỗ trợ |

## TOK. Ngân sách context

Vấn đề: mọi thứ nằm trong điểm vào (`AGENTS.md`), trong description của skill, hay trong thân skill đều bị nạp lại ở mỗi phiên và mỗi subagent. Chi phí lớn nhất của agent thường là đọc lại context ở mỗi lượt, không phải phần nó viết ra. Repo hiện tuyên bố `AGENTS.md` "compact", nhưng chưa có gì giữ nó compact.

| ID | Yêu cầu | Kiểm |
| --- | --- | --- |
| TOK-1 | `AGENTS.md` của payload không vượt một ngưỡng byte cố định. | Test pass với file hiện tại; fixture vượt ngưỡng làm test fail và thông báo nêu kích thước thật, ngưỡng, và cách sửa |
| TOK-2 | `description` trong frontmatter của mọi skill được phân phối không vượt một ngưỡng ký tự. Description chỉ nói khi nào dùng skill, chi tiết để trong thân skill. | Test duyệt mọi skill trong manifest; fixture có description vượt ngưỡng làm test fail và nêu tên skill |
| TOK-3 | `SKILL.md` của mọi skill được phân phối không vượt một ngưỡng byte. Nội dung dài nằm trong `references/`, và `SKILL.md` nêu rõ mỗi reference được mở ở bước nào, không mở trước. | Test kích thước; đọc từng `SKILL.md`, mọi file trong `references/` đều được nhắc kèm điều kiện mở |
| TOK-4 | Cài đặt và cập nhật chỉ ghi vào trong repo đích, không ghi vào thư mục home hay cấu hình toàn cục của agent. | Chạy cài và cập nhật với một thư mục home giả, so danh sách file trong thư mục home trước và sau, không có thay đổi |
| TOK-5 | Các ngưỡng của TOK-1 đến TOK-3 khai ở một chỗ duy nhất, và được đặt bằng kích thước đo được của bản hiện tại cộng một biên. Số đo và biên được ghi lại trong tài liệu. | Đọc file khai ngưỡng; test đọc ngưỡng từ đúng chỗ đó; tài liệu có bảng số đo và biên |
| TOK-6 | Nâng ngưỡng là một thay đổi có chủ đích: phải sửa file khai ngưỡng và ghi lý do trong cùng thay đổi. | Đọc pattern doc hoặc `CONTRIBUTING.md`, có quy định này |
| TOK-7 | Ngưỡng `SKILL.md` gồm hai lớp. Lớp một là một mức trần chung áp cho skill mới. Lớp hai là bảng ngoại lệ ghi ngưỡng riêng cho từng skill đang vượt trần (hiện là `onboard-repository` và `audit-onboarding-proposal`). Ngưỡng trong bảng ngoại lệ chỉ được giảm, không được tăng. | Fixture skill mới vượt trần thì fail; test từ chối thay đổi làm tăng một ngưỡng ngoại lệ mà không kèm lý do (theo TOK-6) |
| TOK-8 | Phần chữ mà AUTH, GATE, RCPT thêm vào skill (lệnh, dòng biên nhận) phải được tính vào ngưỡng TOK-3. Không được nâng ngưỡng chỉ để có chỗ cho chúng. | Đo lại sau khi xong RCPT, mọi skill vẫn trong ngưỡng đã chốt ở TOK-5 |
| TOK-9 | Ngưỡng TOK-1 áp cho khối harness (`scripts/agent-harness-block.md`, `scripts/claude-harness-block.md`), không áp cho phần `AGENTS.md` do repo dùng harness sở hữu. | Fixture `AGENTS.md` có nội dung lớn nằm ngoài khối harness, test vẫn pass |

## AUTH. Thẩm quyền đã duyệt kiểm được bằng máy

Vấn đề: `$encode-invariant` bắt buộc dẫn nguồn đã duyệt, nhưng hiện chỉ agent tự đánh giá nguồn đó có "đã duyệt" hay không.

| ID | Yêu cầu | Kiểm |
| --- | --- | --- |
| AUTH-1 | Template decision định nghĩa frontmatter gồm `status` (một trong `proposed`, `accepted`, `superseded`), `approved_by`, `approved_at` (ngày ISO 8601). | Đọc `docs/templates/decision.md`, đủ ba trường. Trường đã có từ trước không bị đổi nghĩa |
| AUTH-2 | Có một lệnh kiểm nhận một hoặc nhiều đường dẫn tài liệu, và chỉ trả exit 0 khi mọi tài liệu có `status: accepted`, `approved_by` không rỗng, `approved_at` hợp lệ. | Fixture hợp lệ cho exit 0 |
| AUTH-3 | Tài liệu không có frontmatter bị tính là **không đạt**, không bị bỏ qua (fail-closed). | Fixture không frontmatter cho exit khác 0 |
| AUTH-4 | Mỗi lỗi in ba phần: ERROR (file nào, thiếu trường nào), WHY (vì sao quan trọng), FIX (sửa thế nào). | Test khớp cả ba nhãn trên stderr cho từng loại lỗi |
| AUTH-5 | Phân biệt mã thoát: tài liệu không đạt khác lỗi dùng sai lệnh. | Hai trường hợp cho hai exit code khác nhau |
| AUTH-6 | Khi truyền nhiều đường dẫn mà một cái hỏng, lệnh fail và chỉ rõ cái hỏng, đồng thời vẫn báo các cái còn lại. | Fixture hai đường dẫn, một hỏng, đầu ra nêu đúng tên file hỏng |
| AUTH-7 | Bước "Pass The Authority Gate" của `$encode-invariant` chạy lệnh này trên nguồn nó dẫn, và dừng trước mọi chỉnh sửa nếu không đạt. | Đọc `SKILL.md`, bước 2 nêu rõ lệnh và hành vi dừng |
| AUTH-8 | Lệnh có chế độ chỉ liệt kê: quét thư mục decisions và in tài liệu nào thiếu trường, không sửa gì. Dùng cho việc chuyển đổi thủ công các tài liệu cũ. | Chạy trên repo mẫu có decision cũ, in danh sách, working tree không đổi |
| AUTH-9 | Tài liệu của harness nói rõ giới hạn: dấu hiệu này chứng tỏ có người điền trường, không chứng tỏ cuộc duyệt đã diễn ra. Bằng chứng thật là lịch sử review. | Đọc docs, có đoạn nêu giới hạn này |
| AUTH-10 | Tập giá trị của `status` giữ đủ bốn giá trị của template hiện tại: `proposed`, `accepted`, `superseded`, `rejected`. Chỉ `accepted` được tính là đạt. | Fixture cho từng giá trị, chỉ `accepted` cho exit 0 |
| AUTH-11 | Trạng thái chỉ có một nguồn sự thật: mục `## Status` trong thân template bị bỏ, hoặc được giữ nhưng lệnh kiểm báo lỗi khi nó khác frontmatter. Decision cũ chỉ có `## Status` trong thân thì AUTH-8 liệt kê là "cần chuyển đổi", không tự đọc thay frontmatter. | Fixture frontmatter `accepted` nhưng thân ghi `Superseded` thì fail; decision cũ có trong danh sách của AUTH-8 |
| AUTH-12 | `approved_at` không được là ngày trong tương lai so với ngày chạy lệnh, và không được sớm hơn ngày tạo tài liệu nếu tài liệu có ghi ngày tạo. | Fixture ngày tương lai thì fail |
| AUTH-13 | Khi `status: superseded`, tài liệu phải có `superseded_by` trỏ tới một file tồn tại. Lỗi ERROR/FIX phải chỉ người dùng sang tài liệu thay thế. | Fixture superseded thiếu hoặc trỏ sai thì fail, thông báo nêu đường dẫn thay thế |
| AUTH-14 | Đường dẫn truyền vào phải nằm trong repo. Đường dẫn tuyệt đối ra ngoài repo, `..` thoát ra ngoài, hoặc symlink trỏ ra ngoài đều bị từ chối với mã thoát "dùng sai lệnh", theo đúng cách xử lý symlink của update. | Ba fixture tương ứng |

Câu hỏi để người hiện thực chốt: lệnh kiểm là subcommand của binary `harness` hay script trong payload. Tài liệu trong `docs/product/` có tính là nguồn thẩm quyền không. Có coi `superseded` là thẩm quyền hay không (đề xuất: không).

Đề xuất cho câu hỏi thứ nhất: làm thành subcommand của binary `harness`, ví dụ `harness check-authority`. Binary đã có sẵn ở mọi repo đã cài, chạy được trên cả hai nền tảng nên đạt CON-7 mà không cần viết hai bản script, và tái dùng được logic kiểm đường dẫn và symlink của update. Điểm phải cân nhắc: cách này làm tăng bề mặt CLI, và mỗi lần đổi luật phải phát hành binary mới. Việc chốt vẫn thuộc về người duyệt decision của CON-9.

## GATE. Cổng "xong" fail-closed

Vấn đề: "không thấy lỗi" bị đọc nhầm thành "đã kiểm và sạch". Cổng phải coi việc thiếu bằng chứng là thất bại.

| ID | Yêu cầu | Kiểm |
| --- | --- | --- |
| GATE-1 | Cung cấp một template cổng "xong" trong `docs/templates/` và một tài liệu pattern ngắn về cổng fail-closed. | Hai file tồn tại, được khai trong manifest (CON-4) |
| GATE-2 | Cổng nhận một mã tác vụ và chỉ chấp nhận ký tự `A-Z a-z 0-9 . _ -`. Ký tự khác bị từ chối ngay, không cố escape. | Test mã có khoảng trắng, dấu nháy, `../`, và không có tham số, đều bị từ chối với exit code dùng sai |
| GATE-3 | Cổng fail khi file báo cáo bằng chứng của tác vụ không tồn tại **hoặc rỗng**. | Hai test: thiếu file, file rỗng, đều exit 1 |
| GATE-4 | Cổng fail khi tồn tại file đánh dấu chặn của tác vụ. | Test có marker thì exit 1, bỏ marker thì exit 0 |
| GATE-5 | Cổng chỉ pass khi có báo cáo không rỗng và không có marker chặn. | Test ca hợp lệ exit 0 và in một dòng OK |
| GATE-6 | Mọi thông báo thất bại có ba phần ERROR, WHY, FIX; FIX nêu lệnh hoặc hành động chạy lại. | Test khớp ba nhãn |
| GATE-7 | Thư mục bằng chứng cấu hình được qua một biến môi trường, có mặc định. Template không chứa lệnh kiểm chứng riêng của một stack. | Đọc file, đạt CON-5 |
| GATE-8 | Pattern doc nói rõ: thiếu bằng chứng khác với sạch; có script cổng chưa có nghĩa nó đang chạy; việc nối cổng vào CI hay hook do repo dùng harness làm, harness không tự nối. | Đọc pattern doc, có cả ba ý |
| GATE-9 | Có test chứng minh hai chiều: ca sạch pass, và ca có blocker do bên ghi tạo ra thì cổng fail. Không chấp nhận test chỉ kiểm ca pass. | Test suite có đủ cả hai chiều |
| GATE-10 | Thư mục bằng chứng, dù lấy từ mặc định hay từ biến môi trường, phải nằm trong repo. Giá trị trỏ ra ngoài repo, hoặc file báo cáo/marker là symlink, đều bị từ chối. | Test biến môi trường trỏ `/tmp`, và test report là symlink, đều bị từ chối |
| GATE-11 | Báo cáo chỉ toàn khoảng trắng hoặc dòng trống bị tính là rỗng. | Fixture chỉ có `\n` và khoảng trắng thì exit 1 |
| GATE-12 | Template ghi rõ quy ước tên file: báo cáo và marker suy ra từ mã tác vụ theo một mẫu cố định, được ghi trong template. Bên ghi bằng chứng và cổng dùng chung một quy ước đó. | Đọc template; test tạo file theo quy ước và cổng nhận đúng |
| GATE-13 | Có bản tương đương cho Windows, hoặc tài liệu ghi rõ template chỉ dành cho POSIX shell (theo CON-7). | Test `.ps1` hoặc đoạn tài liệu tương ứng |

Ví dụ tham khảo đã chạy được, có thể dùng hoặc viết lại: `done-gate.sh` và `test-done-gate.sh` cùng thư mục với file này (9 ca, pass 9/9).

## RCPT. Biên nhận skill và đo tuân thủ

Vấn đề: không có cách đo agent có thật sự làm theo skill hay không.

Định dạng dòng cuối của mỗi lần chạy skill:

```text
HARNESS_SKILL: <skill-name> | done|stopped|skipped | <reason or artifact path>
```

| ID | Yêu cầu | Kiểm |
| --- | --- | --- |
| RCPT-1 | Mọi skill được phân phối kết thúc câu trả lời bằng đúng dòng biên nhận ở trên. Mỗi `SKILL.md` ghi rõ yêu cầu này. | Duyệt từng `SKILL.md` trong manifest, đủ chỉ dẫn |
| RCPT-2 | Giá trị `stopped` dùng khi skill dừng ở cổng thẩm quyền hoặc thiếu năng lực cần thiết. Trường thứ ba không được rỗng. | Mô tả trong `SKILL.md` và một ví dụ |
| RCPT-3 | Có một lệnh đo đọc file phiên làm việc của Claude Code (JSONL) và báo, theo từng skill: số lần được gọi, số biên nhận tìm thấy, tỷ lệ. | Chạy trên fixture, ra đúng số |
| RCPT-4 | Tên trường trong JSONL phải được xác nhận bằng cách mở một file phiên thật trước khi viết code, không được giả định. | Có ghi chú trong tài liệu nêu trường nào được dùng và đã đối chiếu với file thật nào |
| RCPT-5 | Chỉ tính một lần gọi khi skill được gọi tường minh. Việc nội dung yêu cầu khớp chủ đề skill không được tính. | Fixture có yêu cầu khớp chủ đề nhưng không gọi skill, kết quả không tăng |
| RCPT-6 | Đầu ra có dạng JSON máy đọc được và một bản tóm tắt cho người. | Chạy lệnh, có cả hai |
| RCPT-7 | Xử lý biên: không có lần gọi nào thì báo 0/0 chứ không chia cho 0. Dòng JSONL hỏng bị bỏ qua và được đếm riêng. | Hai fixture tương ứng |
| RCPT-8 | Tài liệu nói rõ giới hạn: biên nhận do agent tự khai, nên đo được định dạng có được tuân thủ, không đo được việc đó có đúng sự thật. Phải kết hợp với AUTH và GATE để có bằng chứng thật. | Đọc docs, có đoạn nêu giới hạn |
| RCPT-9 | Phiên bản đầu chỉ hỗ trợ Claude Code. Định dạng phiên của Codex để ngoài phạm vi và được ghi rõ là chưa hỗ trợ. | Lệnh báo lỗi rõ khi nhận định dạng không hỗ trợ |
| RCPT-10 | Lệnh đo báo thêm token cho từng lần gọi skill và tổng theo skill, tách bốn loại: input mới, cache creation, cache read, output. Tên trường lấy theo RCPT-4. | Fixture có số token đã biết, kết quả cộng đúng từng loại |

| RCPT-11 | Quyền riêng tư: file phiên chứa prompt, đầu ra công cụ, và có thể có secret. Lệnh đo chỉ đọc file phiên ở máy cục bộ và chỉ in số liệu tổng hợp (tên skill, số đếm, token, đường dẫn artifact nếu có). Không in nội dung prompt hay câu trả lời, không gửi gì ra mạng. | Fixture có chuỗi giả làm secret trong prompt; chuỗi đó không xuất hiện trong cả JSON lẫn bản tóm tắt |
| RCPT-12 | Lệnh đo không ghi gì cả, kể cả vào thư mục phiên. Đường dẫn file phiên do người dùng truyền vào; lệnh không tự quét thư mục home (giữ tinh thần của CON-2 và TOK-4). | Chạy với thư mục home giả, danh sách file trước và sau giống nhau; không truyền đường dẫn thì báo lỗi dùng sai lệnh |
| RCPT-13 | Biên nhận phải là dòng không rỗng **cuối cùng** của câu trả lời cuối của lượt gọi skill. Biên nhận nằm giữa câu trả lời không được tính. Tên skill trong biên nhận phải khớp skill đã được gọi. | Fixture biên nhận ở giữa câu trả lời, và fixture biên nhận sai tên skill, đều không được tính |
| RCPT-14 | Ghi rõ cách xử lý phiên của subagent (sidechain): tính chung, tính riêng, hay bỏ qua. Đầu ra phải ghi số dòng đã bị loại vì lý do này. | Fixture có sidechain cho kết quả đúng theo quy tắc đã chốt |
| RCPT-15 | Skill được gọi qua Codex (`agents/openai.yaml`) vẫn phải có chỉ dẫn biên nhận, vì chỉ dẫn nằm trong `SKILL.md` dùng chung. Chỉ phần đo là giới hạn ở Claude Code (RCPT-9). | Đọc `SKILL.md`, chỉ dẫn không phụ thuộc agent nào |

Fixture tối thiểu cho RCPT-3: một file có 3 lần gọi skill và 2 biên nhận phải cho kết quả 2/3.

Lưu ý: fixture cho RCPT phải dựng tay hoặc đã được làm sạch. Không commit file phiên thật vào repo.

## DOC. Khi nào nâng lời dặn thành cổng chặn

Vấn đề: thêm cổng thì dễ, nối dây và giữ cho cổng còn chạy thì tốn. Cổng có file mà không chạy tạo cảm giác an toàn giả.

| ID | Yêu cầu | Kiểm |
| --- | --- | --- |
| DOC-1 | Có một trang pattern nêu tiêu chí nâng một lời dặn thành cổng chặn: đã quan sát được vi phạm thật và có bằng chứng; hậu quả của vi phạm đủ đắt; quy trình cần chặn đã ổn định. Thiếu các điều kiện này thì giữ ở dạng lời dặn. | Đọc trang, có đủ ba tiêu chí |
| DOC-2 | Trang nêu quy tắc: một cổng chỉ được thêm khi nó được nối vào nơi chạy thật và có chứng minh hai chiều ngay trong cùng thay đổi. Cổng chưa nối dây không được thêm. | Đọc trang, có quy tắc này |
| DOC-3 | Trang hướng dẫn dùng số liệu của RCPT (tỷ lệ tuân thủ, token) làm bằng chứng khi quyết định nâng hay giữ. | Đọc trang, có liên kết tới lệnh đo của RCPT |

## Điều kiện hoàn thành chung

| ID | Yêu cầu | Kiểm |
| --- | --- | --- |
| DONE-1 | Mọi test mới được thêm vào danh sách của `scripts/validate-premerge.sh`. | Chạy `scripts/validate-premerge.sh`, pass, và log có tên các test mới |
| DONE-2 | Bản đồ `docs/README.md` có mục cho các tài liệu mới. | Đọc file |
| DONE-3 | Mỗi khả năng nằm trong một PR riêng có tiêu đề conventional (`feat(harness): …`), để `scripts/render-changelog-files.py` tự sinh mục `CHANGELOG.md`. Không viết tay vào `CHANGELOG.md`. | Sau khi merge, `CHANGELOG.md` có một mục cho mỗi PR; `tests/maintenance/test-render-changelog-files.sh` pass |
| DONE-4 | Với mỗi khả năng, có bằng chứng cả hai chiều (ca đúng pass, ca vi phạm cố ý fail) và ca vi phạm không để lại trong cây làm việc. | `git status` sạch sau khi chạy test |
| DONE-5 | `scripts/harness-release-changed.sh` phân loại đúng: thay đổi payload thì cần bản phát hành core mới. | `tests/maintenance/test-harness-release-classification.sh` pass, có thêm ca cho file payload mới |
| DONE-6 | `tests/installer/test-install-harness-modes.ps1` được cập nhật cho file payload mới (theo CON-7 và CON-8). | Test PowerShell pass |

## Backlog, chưa cần làm

| Ý | Điều kiện để đưa vào làm |
| --- | --- |
| Hạn dùng của quyết định: ghi hash của tài liệu nguồn vào quyết định, báo khi nguồn đổi | Khi AUTH đã chạy ổn và có nhu cầu phát hiện quyết định cũ |
| Sổ đăng ký invariant: mỗi luật đã mã hoá ghi nguồn, lệnh kiểm, bốn mức enforcement đã xác minh hay chưa | Khi có từ vài luật trở lên cần theo dõi |
| Sổ bài học giữa các phiên, có giới hạn kích thước | Khi đo được việc mất quyết định giữa các phiên thật sự xảy ra |
| Skill review đối kháng chạy với context mới | Khi RCPT cho thấy skill hiện có được tuân thủ đủ tốt để đáng thêm |

## Ngoài phạm vi

DAG hoặc điều phối nhiều agent, phân luồng theo loại tác vụ, telemetry, hàng loạt hook mặc định, bộ BMAD. Các thứ này trái với CON-1 đến CON-3.
