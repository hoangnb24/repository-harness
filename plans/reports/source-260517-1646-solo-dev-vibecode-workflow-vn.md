# Quy trình tối thiểu cho Solo Dev dùng Vibe Coding khi làm việc với khách hàng

Với solo dev dùng **vibe coding / AI coding**, quy trình tối thiểu nên không quá nặng như agency lớn, nhưng vẫn phải có đủ **scope, acceptance criteria, approval, UAT, handover** để làm việc được với khách hàng.

Flow đề xuất:

```text
Lead → Discovery → Proposal/SOW → PRD-lite → UX Flow → Tech Plan → Backlog → Build → QA/UAT → Deploy → Handover → Support
```

---

## 1. Client Intake / Khảo sát ban đầu

**Mục tiêu:** hiểu khách hàng muốn gì, có đáng nhận không, budget/time có hợp lý không.

**Output cần có:**

- Project Brief 1–2 trang
- Problem cần giải quyết
- User chính
- Feature mong muốn
- Deadline
- Budget range
- Platform: web / mobile / internal tool / automation / AI app

**Prompt:**

```markdown
Bạn là Senior Business Analyst hỗ trợ solo dev nhận dự án client.

Hãy phân tích thông tin khách hàng dưới đây và tạo “Client Intake Summary”.

Yêu cầu output:
1. Tóm tắt nhu cầu khách hàng
2. Business problem
3. Target users
4. Mục tiêu dự án
5. Tính năng khách hàng đang yêu cầu
6. Những điểm chưa rõ cần hỏi lại
7. Rủi ro ban đầu
8. Đề xuất có nên nhận dự án hay không
9. Dự án này phù hợp loại nào:
   - Landing page
   - Web app
   - SaaS MVP
   - Internal tool
   - Automation
   - AI app
   - E-commerce
   - Dashboard
10. Ước lượng độ phức tạp: Low / Medium / High

Thông tin khách hàng:

[PASTE NỘI DUNG TRAO ĐỔI VỚI KHÁCH HÀNG]
```

---

## 2. Discovery Questions / Hỏi rõ yêu cầu

**Mục tiêu:** không để khách nói “làm app quản lý đơn giản thôi” rồi sau đó phát sinh vô hạn.

**Output cần có:**

- Danh sách câu hỏi gửi khách
- Phân nhóm: business, user, feature, data, payment, admin, deadline

**Prompt:**

```markdown
Bạn là BA 10 năm kinh nghiệm. Dựa trên thông tin dự án bên dưới, hãy tạo danh sách câu hỏi discovery để tôi gửi khách hàng trước khi báo giá.

Yêu cầu:
- Hỏi ngắn gọn, dễ hiểu cho non-tech client
- Chia theo nhóm:
  1. Business goal
  2. User & role
  3. Feature
  4. Data cần lưu
  5. Workflow
  6. Admin/permission
  7. Payment/billing nếu có
  8. Content/media/file upload nếu có
  9. Integration bên thứ ba
  10. Deadline/budget
  11. Success criteria
- Ưu tiên câu hỏi giúp chốt scope và tránh phát sinh

Thông tin dự án:

[PASTE PROJECT BRIEF]
```

---

## 3. Scope & Proposal / Báo giá và phạm vi

**Mục tiêu:** chốt rõ **làm gì / không làm gì / bao nhiêu tiền / bao lâu / điều kiện phát sinh**.

Với solo dev, đây là bước cực kỳ quan trọng.

**Output cần có:**

- Proposal
- Scope of Work
- Timeline
- Payment milestone
- Out of scope
- Change request rule

**Prompt:**

```markdown
Bạn là Product Consultant kiêm Software Delivery Manager.

Hãy tạo Proposal / Scope of Work cho dự án dưới đây để gửi khách hàng.

Yêu cầu output:
1. Tóm tắt dự án
2. Mục tiêu dự án
3. Phạm vi MVP
4. Danh sách tính năng sẽ làm
5. Danh sách không bao gồm trong scope
6. Deliverables bàn giao
7. Timeline theo milestone
8. Quy định feedback/revision
9. Payment milestone đề xuất
10. Điều kiện nghiệm thu
11. Change request policy
12. Rủi ro và giả định
13. Những thứ khách hàng cần cung cấp

Viết bằng tiếng Việt, chuyên nghiệp, dễ hiểu cho khách hàng non-tech.

Thông tin dự án:

[PASTE CLIENT REQUIREMENTS]
```

---

## 4. PRD-lite / Tài liệu yêu cầu sản phẩm tối thiểu

**Mục tiêu:** chuyển ý tưởng thành yêu cầu sản phẩm rõ ràng để bạn code bằng AI không bị lệch.

**Output cần có:**

- Product overview
- User roles
- Core user flow
- Feature list
- Acceptance criteria
- Edge cases

**Prompt:**

```markdown
Bạn là Senior Product Manager và Business Analyst.

Hãy tạo PRD-lite cho dự án bên dưới. Đây là tài liệu tối thiểu để solo dev có thể build MVP bằng AI coding tool nhưng vẫn đủ rõ để khách hàng review.

Cấu trúc output:

# 1. Product Overview
- Tên sản phẩm
- Mục tiêu
- User chính
- Vấn đề cần giải quyết
- Giá trị mang lại

# 2. User Roles
Liệt kê các role:
- Guest
- User
- Admin
- Super admin nếu cần

Với mỗi role, mô tả quyền hạn.

# 3. MVP Scope
Chia thành:
- Must have
- Should have
- Could have
- Out of scope

# 4. Core User Flow
Mô tả từng flow chính theo step-by-step.

# 5. Feature Requirements
Với mỗi feature, viết:
- Feature name
- Description
- User story
- Functional requirements
- Acceptance criteria theo Given / When / Then
- Edge cases
- Priority

# 6. Data Requirements
Liệt kê dữ liệu cần lưu.

# 7. Non-functional Requirements
- Performance
- Security
- Mobile responsive
- Browser support
- Backup
- Logging

# 8. Open Questions
Các câu hỏi còn cần khách xác nhận.

Thông tin dự án:

[PASTE APPROVED SCOPE]
```

---

## 5. UX Flow / Wireframe text

**Mục tiêu:** chưa cần Figma phức tạp, nhưng phải biết có những màn nào và user bấm gì.

**Output cần có:**

- Sitemap
- Screen list
- User flow
- Field trên từng màn
- Button/action trên từng màn

**Prompt:**

```markdown
Bạn là Senior UX Designer.

Dựa trên PRD-lite bên dưới, hãy tạo UX Flow và Wireframe Specification dạng text để solo dev có thể build UI.

Yêu cầu output:

# 1. Sitemap
Liệt kê toàn bộ page/screen.

# 2. Navigation Structure
Mô tả menu, sidebar, header, footer nếu có.

# 3. Screen-by-screen Specification
Với mỗi màn hình, mô tả:
- Mục đích màn hình
- User role được truy cập
- Component chính
- Form fields
- Buttons/actions
- Empty state
- Loading state
- Error state
- Success state
- Validation rules

# 4. Main User Flows
Mô tả step-by-step:
- Đăng ký / đăng nhập
- Tạo dữ liệu
- Xem danh sách
- Tìm kiếm / filter
- Chỉnh sửa
- Xóa
- Admin quản lý

# 5. UX Notes
Đề xuất cách làm UI đơn giản, nhanh build, phù hợp MVP.

PRD-lite:

[PASTE PRD-LITE]
```

---

## 6. Tech Spec-lite / Kế hoạch kỹ thuật tối thiểu

**Mục tiêu:** chọn stack, database, architecture, API, auth, deployment trước khi code.

Với solo dev vibe coding, bạn không cần tech spec 50 trang, nhưng cần đủ để AI tool không sinh lung tung.

**Output cần có:**

- Stack
- Architecture
- Database schema
- API endpoints
- Folder structure
- Auth/permission
- Deployment plan

**Prompt:**

```markdown
Bạn là Senior Full-stack Architect hỗ trợ solo dev build MVP nhanh nhưng maintainable.

Dựa trên PRD-lite và UX spec bên dưới, hãy tạo Technical Spec-lite.

Context:
- Tôi là solo dev dùng AI coding tool.
- Ưu tiên build nhanh, ít phức tạp, dễ deploy, dễ maintain.
- Không over-engineering.
- Cần đủ rõ để chia task và code.

Yêu cầu output:

# 1. Recommended Tech Stack
Đề xuất stack phù hợp, ví dụ:
- Frontend
- Backend
- Database
- Auth
- File storage
- Email
- Payment nếu có
- AI provider nếu có
- Hosting

# 2. System Architecture
Mô tả kiến trúc đơn giản.

# 3. Database Schema
Liệt kê tables/entities:
- Field
- Data type
- Relationship
- Index cần có

# 4. API Endpoints
Với mỗi API:
- Method
- Endpoint
- Purpose
- Request body
- Response body
- Auth required
- Error cases

# 5. Permission Model
Mô tả role và quyền.

# 6. Folder Structure
Đề xuất cấu trúc thư mục source code.

# 7. Background Jobs nếu cần
Ví dụ email, AI processing, file processing.

# 8. Security Requirements
- Auth
- Input validation
- Rate limit
- File upload safety
- Data privacy

# 9. Deployment Plan
- Environment
- Env variables
- Database migration
- Backup
- Monitoring/logging

# 10. Technical Risks
Liệt kê rủi ro và cách giảm thiểu.

PRD-lite:

[PASTE PRD-LITE]

UX Spec:

[PASTE UX SPEC]
```

---

## 7. Backlog / Chia task để code bằng AI

**Mục tiêu:** biến spec thành task nhỏ để feed vào Cursor, Claude Code, Windsurf, Copilot, v.v.

**Output cần có:**

- Epic
- Story
- Task
- Acceptance criteria
- Suggested order

**Prompt:**

```markdown
Bạn là Technical Project Manager cho solo dev.

Dựa trên PRD-lite, UX Spec và Technical Spec-lite bên dưới, hãy chia thành development backlog.

Yêu cầu:
1. Chia theo Epic → Story → Task
2. Mỗi task đủ nhỏ để AI coding tool có thể implement trong 1 lần
3. Mỗi task có:
   - Task title
   - Goal
   - Files/modules likely affected
   - Implementation notes
   - Acceptance criteria
   - Test cases
   - Dependency
4. Sắp xếp thứ tự build hợp lý
5. Tách rõ:
   - Foundation
   - Auth
   - Database
   - Core feature
   - Admin
   - UI polish
   - QA
   - Deployment
6. Đánh dấu priority:
   - P0: bắt buộc
   - P1: nên có
   - P2: có thì tốt

PRD-lite:

[PASTE PRD-LITE]

UX Spec:

[PASTE UX SPEC]

Technical Spec-lite:

[PASTE TECH SPEC]
```

---

## 8. AI Coding Prompt cho từng task

**Mục tiêu:** dùng vibe coding nhưng vẫn có kiểm soát. Không bảo AI “build toàn bộ app”. Hãy bắt nó làm từng task nhỏ.

**Prompt dùng cho mỗi task:**

```markdown
Bạn là Senior Full-stack Developer.

Tôi đang build dự án theo spec bên dưới. Hãy implement task này một cách clean, maintainable, không over-engineering.

Nguyên tắc:
- Chỉ làm đúng task được giao
- Không tự ý thay đổi architecture nếu không cần
- Không xoá code đang có nếu không được yêu cầu
- Viết code rõ ràng, dễ đọc
- Có xử lý loading/error/empty state nếu liên quan
- Có validation nếu liên quan form/API
- Có basic test hoặc hướng dẫn test thủ công
- Sau khi code xong, giải thích ngắn gọn đã thay đổi gì

Project context:

[PASTE TECH SPEC SUMMARY]

Current task:

[PASTE TASK DETAIL]

Acceptance criteria:

[PASTE ACCEPTANCE CRITERIA]

Existing code context:

[PASTE FILES / FOLDER STRUCTURE / RELEVANT CODE]
```

---

## 9. Code Review Prompt

**Mục tiêu:** sau khi AI code xong, bắt AI review lại để giảm bug.

**Prompt:**

```markdown
Bạn là Senior Code Reviewer.

Hãy review phần code / diff bên dưới.

Tập trung vào:
1. Có đúng requirement không?
2. Có thiếu acceptance criteria nào không?
3. Có bug logic không?
4. Có lỗi security không?
5. Có lỗi performance không?
6. Có edge case chưa xử lý không?
7. Có code smell không?
8. Có phần nào over-engineering không?
9. Có ảnh hưởng module khác không?
10. Cần test thêm gì?

Output:
- Summary
- Issues found theo mức độ: Critical / Major / Minor
- Suggested fixes
- Final recommendation: Approve / Request changes

Requirement:

[PASTE TASK REQUIREMENT]

Code / diff:

[PASTE CODE OR DIFF]
```

---

## 10. QA Test Case / Kiểm thử trước khi gửi khách

**Mục tiêu:** không gửi bản lỗi cơ bản cho khách.

**Output cần có:**

- Test scenarios
- Manual test cases
- Edge cases
- Regression checklist

**Prompt:**

```markdown
Bạn là QA Engineer.

Dựa trên PRD-lite và danh sách feature đã build, hãy tạo test cases cho MVP.

Yêu cầu output:
1. Test plan tổng quan
2. Test cases theo từng module
3. Với mỗi test case:
   - Test case ID
   - Scenario
   - Preconditions
   - Steps
   - Expected result
   - Priority
4. Edge cases
5. Negative test cases
6. Regression checklist
7. UAT checklist cho khách hàng non-tech

PRD-lite:

[PASTE PRD-LITE]

Built features:

[PASTE LIST FEATURES BUILT]
```

---

## 11. UAT / Gửi khách nghiệm thu

**Mục tiêu:** khách test theo checklist, tránh feedback cảm tính kiểu “em thấy chưa đúng ý”.

**Output cần có:**

- UAT guide
- Checklist nghiệm thu
- Bug report template
- Feedback deadline

**Prompt:**

```markdown
Bạn là Delivery Manager.

Hãy tạo UAT Guide để gửi khách hàng nghiệm thu MVP.

Yêu cầu:
- Viết dễ hiểu cho khách hàng non-tech
- Có checklist từng tính năng
- Có hướng dẫn cách test
- Có format báo bug
- Có quy định phân loại:
  - Bug
  - Change request
  - New feature
  - UX improvement
- Có deadline phản hồi
- Có điều kiện nghiệm thu

Thông tin dự án:

[PASTE PROJECT SCOPE]

Danh sách tính năng đã hoàn thành:

[PASTE COMPLETED FEATURES]
```

---

## 12. Deployment & Release Note

**Mục tiêu:** mỗi lần deploy phải biết bản này có gì, sửa gì, còn lỗi gì.

**Output cần có:**

- Release note
- Known issues
- Deployment checklist
- Rollback plan

**Prompt:**

```markdown
Bạn là Release Manager.

Hãy tạo Release Note và Deployment Checklist cho version bên dưới.

Yêu cầu output:

# 1. Release Summary
# 2. New Features
# 3. Bug Fixes
# 4. Improvements
# 5. Known Issues
# 6. Deployment Checklist
# 7. Post-deployment Testing Checklist
# 8. Rollback Plan
# 9. Client Communication Message

Version:

[VERSION]

Changes included:

[PASTE CHANGELOG / COMPLETED TASKS]

Environment:

[DEV/STAGING/PRODUCTION]
```

---

## 13. Handover / Bàn giao dự án

**Mục tiêu:** bàn giao chuyên nghiệp dù bạn là solo dev.

**Output cần có:**

- Admin account
- Source code
- Deployment info
- Env variables guide
- Database guide
- User guide
- Maintenance note

**Prompt:**

```markdown
Bạn là Technical Writer.

Hãy tạo bộ tài liệu handover cho dự án bên dưới.

Yêu cầu output:

# 1. Project Overview
# 2. Features Delivered
# 3. User Guide
Hướng dẫn khách sử dụng từng chức năng.

# 4. Admin Guide
Hướng dẫn quản trị nếu có admin panel.

# 5. Technical Handover
- Tech stack
- Repo structure
- Environment variables
- Database
- Third-party services
- Deployment process
- Backup
- Monitoring/logging

# 6. Account & Access Checklist
Liệt kê những tài khoản/access cần bàn giao.

# 7. Maintenance Guide
- Cách xử lý lỗi thường gặp
- Cách update content/data
- Cách deploy version mới

# 8. Limitations
Những giới hạn hiện tại.

# 9. Recommended Next Phase
Đề xuất tính năng nên làm tiếp.

Thông tin dự án:

[PASTE FINAL SPEC]

Thông tin kỹ thuật:

[PASTE TECH SPEC]

Danh sách tính năng đã bàn giao:

[PASTE COMPLETED FEATURES]
```

---

## 14. Change Request / Khi khách muốn thêm tính năng

**Mục tiêu:** phân biệt rõ bug với phát sinh. Đây là thứ giúp solo dev không bị “scope creep”.

**Prompt:**

```markdown
Bạn là Business Analyst.

Khách hàng vừa yêu cầu thay đổi/phát sinh bên dưới. Hãy phân tích đây là:
- Bug
- Change request
- New feature
- UX improvement
- Clarification

Yêu cầu output:
1. Tóm tắt yêu cầu
2. Phân loại yêu cầu
3. Có nằm trong scope ban đầu không?
4. Ảnh hưởng tới module nào?
5. Độ phức tạp: Low / Medium / High
6. Rủi ro
7. Ước lượng effort
8. Đề xuất xử lý:
   - Làm trong scope hiện tại
   - Đưa vào phase sau
   - Báo giá phát sinh
   - Từ chối / cần làm rõ
9. Viết message phản hồi khách hàng chuyên nghiệp

Scope ban đầu:

[PASTE APPROVED SCOPE]

Yêu cầu mới từ khách:

[PASTE CLIENT REQUEST]
```

---

## 15. Maintenance / Bảo trì sau bàn giao

**Mục tiêu:** biến dự án thành doanh thu dài hạn, không chỉ làm xong rồi mất khách.

**Prompt:**

```markdown
Bạn là Software Maintenance Consultant.

Hãy đề xuất gói bảo trì cho dự án bên dưới.

Yêu cầu:
1. Các hạng mục nên bao gồm trong bảo trì
2. Các hạng mục không bao gồm
3. SLA đề xuất
4. Số giờ hỗ trợ mỗi tháng
5. Quy trình báo lỗi
6. Quy trình xử lý bug
7. Quy trình yêu cầu feature mới
8. Các gói đề xuất:
   - Basic
   - Standard
   - Premium
9. Viết nội dung proposal ngắn gọn để gửi khách

Thông tin dự án:

[PASTE PROJECT INFO]
```

---

## Bộ tài liệu tối thiểu bạn nên luôn có

Với solo dev, không cần quá nặng, nhưng nên có tối thiểu:

| Tài liệu | Khi nào cần | Ai duyệt |
|---|---|---|
| Client Intake Summary | Sau buổi nói chuyện đầu tiên | Bạn |
| Proposal / SOW | Trước khi nhận tiền | Khách |
| PRD-lite | Trước khi code | Khách |
| UX Flow / Screen list | Trước khi code UI | Khách |
| Tech Spec-lite | Trước khi build | Bạn |
| Backlog | Trước khi vibe code | Bạn |
| UAT Checklist | Trước khi nghiệm thu | Khách |
| Handover Doc | Khi bàn giao | Khách |
| Change Request Log | Trong suốt dự án | Hai bên |

---

## Quy trình tối thiểu thực tế nên dùng

Đây là bản gọn nhất nên áp dụng:

```text
1. Nhận brief khách
2. Hỏi discovery questions
3. Tạo Proposal/SOW và chốt scope
4. Nhận deposit
5. Tạo PRD-lite
6. Tạo UX flow/screen list
7. Tạo Tech Spec-lite
8. Chia backlog
9. Build từng task bằng AI coding
10. Review code + tự QA
11. Gửi staging cho khách UAT
12. Fix bug trong scope
13. Deploy production
14. Bàn giao tài liệu
15. Đề xuất maintenance hoặc phase 2
```

Nguyên tắc quan trọng nhất khi dùng vibe coding cho khách hàng:

> AI có thể giúp bạn code nhanh, nhưng không thay bạn chốt scope, acceptance criteria, UAT và change request. Muốn làm dự án khách hàng ổn định, hãy để AI tăng tốc phần build, còn quy trình delivery vẫn phải rõ ràng.
