# Chạy một issue bằng harness

Hướng dẫn thao tác cho thành viên. [workflow.md](workflow.md) là quy trình chuẩn;
[policy.json](policy.json) quản lý owner paths, nhánh, Foundation origin và gates.
Codex và Claude dùng cùng snapshot, checkpoint và evidence. Con người giao
issue, bắt đầu phiên, review độc lập và quyết định merge.

## 1. Chuẩn bị checkout

Đọc root `README.md`, `AGENTS.md`, `app/SPEC.md` và instructions/SPEC/owner plan
của phần được giao. Từ root repo:

```bash
cp .env.example .env
python3 .github/scripts/harness.py doctor
make setup
python3 .github/scripts/harness.py sync --check
python3 .github/scripts/harness.py self-check
```

Copy `.env` chỉ cần khi chưa có cấu hình local; không ghi đè cấu hình của thành
viên khác. `make setup` dùng frozen locks. Các lệnh check phải báo kết quả thật;
tool thiếu là blocker cho check cần tool đó. Nếu asset drift, sửa trong assigned
tooling task rồi sync; feature lane không tự sửa harness. `project-init` cũng
có thể hướng dẫn onboarding này; nó không tạo backlog hoặc giao issue.

Đăng nhập công cụ và `gh` bằng tài khoản của mình. Người dùng review/trust
project/hooks trong runtime khi cần; không tự ghi global trust. Xem
[compatibility](compatibility.md) cho surface/version đã kiểm tra. Hooks và named
roles là tiện ích tùy chọn; core workflow vẫn chạy bằng CLI khi thiếu chúng.

## 2. Nhận issue từ người phụ trách

Người phụ trách cung cấp issue thật có một assignee, reviewer và lane, scope,
AC cùng check IDs, dependency, nguồn dữ liệu và rollback. Chỉ mở feature lane
khi Foundation đã được reviewer độc lập chấp nhận và prerequisites đủ. Chọn
checkout/nhánh theo policy; một issue và một writer mỗi lane. Harness không
claim issue, chọn issue tiếp theo hoặc tạo owner branch.

`123` dưới đây chỉ là số minh họa; thay bằng issue được giao. Chọn đúng tool và
surface thực tế; `cli` không đại diện cho desktop.

| Thao tác | Codex | Claude Code |
| --- | --- | --- |
| Onboarding | `$project-init` | `/project-init` |
| Bắt đầu/resume issue | `$task-start 123` | `/task-start 123` |
| Kiểm chứng | `$task-verify 123` | `/task-verify 123` |
| Chuẩn bị draft PR khi được yêu cầu | `$task-ship 123` | `/task-ship 123` |
| Entry point explicit toàn workflow | `$vev-issue 123` | `/vev-issue 123` |

Các stage skills được discover mặc định; start/ship vẫn cần yêu cầu của người
dùng cho issue cụ thể. Nếu runtime chưa discover skill, đọc canonical prompt
trong `.agents/skills/<name>/SKILL.md` và dùng CLI chung:

```bash
python3 .github/scripts/harness.py start --issue 123 --tool codex --surface cli
```

Claude CLI dùng `--tool claude --surface cli`; desktop ghi surface thực tế.
`start` fetch snapshot và đối chiếu assignee/dependencies/base/scope. Offline
snapshot dùng cho replay/test, không thay readiness GitHub. `BLOCKED` nêu rõ
đầu vào cần giải quyết; không chuyển sang issue khác tự động.

## 3. Chốt plan và triển khai

Plan ngắn nêu files được sửa, mỗi AC sẽ được chứng minh bằng check/assertion/
artifact nào, contract/data impact, câu hỏi còn mở và bước tiếp theo. Không dùng
checkbox làm backlog thay GitHub Issue. Tạo checkpoint lần đầu bằng:

```bash
python3 .github/scripts/harness.py handoff --issue 123
```

Cập nhật `docs/harness/handoffs/123.md` theo [template](templates/handoff.md).
Chỉ thay phần issue được giao; policy/contract/tooling cần lane và PR riêng.
Triển khai lát cắt nhỏ có test hành vi. Trước đổi công cụ/máy hoặc hết giới hạn
phiên trong workflow, lưu checkpoint và chuyển pushed commit/draft PR hoặc
patch rõ ràng. Resume lấy issue mới và đối chiếu issue hash, branch, HEAD, diff,
base/dependencies với checkpoint trước sửa.

## 4. Kiểm chứng theo AC và revision

```bash
python3 .github/scripts/harness.py verify --issue 123
```

`verify` chọn fixed Make gates từ packages bị thay đổi và consumer impact,
ghi kết quả theo revision. Dùng focused runner khi cần AC cụ thể, ví dụ:

```bash
python3 .github/scripts/harness.py run --issue 123 --check frontend-test --path app/frontend/src/services/api.test.ts --ac AC-01
```

Test file ở ví dụ phải là file phù hợp issue thực. Chỉ mapping AC không chứng
minh assertion đã chạy. Ghi command/exit, tested HEAD/base, log/artifact path/hash
và `PASS`, `FAIL`, `BLOCKED` hoặc `NOT RUN`. Fix dưới repair limit của workflow;
thiếu môi trường hay evidence stale phải giữ trạng thái thật. UI cần hành vi
loading/error/empty và screenshot/trace liên quan. QA roles chỉ dùng khi được
yêu cầu hoặc plan cần, mặc định một agent phụ đồng thời.

Sau khi code và checkpoint đã commit, working tree sạch:

```bash
python3 .github/scripts/harness.py verify --issue 123 --full
python3 .github/scripts/harness.py ready --issue 123
```

`--full` ghi fresh `make ci`; scoped PASS trước đó không thay final gate.
Các gate AC bổ sung cũng được ghi. Focused evidence ở revision cũ cần chạy lại
qua `run` với đúng `--path`; chỉ evidence thực thi còn hiệu lực được reuse.
Giữ log cuối trong ignored evidence/PR/CI artifacts. Không commit thêm một file
chỉ để chép PASS và khiến SHA đã test cũ đi. Revision/base/issue/dependency đổi
thì đối chiếu và kiểm chứng lại. `ready` không chứng nhận human review hay merge.

## 5. Draft PR và bàn giao review

Khi người dùng yêu cầu shipping, dùng `code-reviewer` hoặc cùng canonical prompt
với read-only subagent/human reviewer. Record unavailable review `NOT RUN`, sửa
findings thực và chạy lại checks liên quan. Agent verdict không là non-author
human approval. Named role files không chứng minh runtime gọi được role.

Push nhánh policy và mở/update draft PR theo `.github/pull_request_template.md`
trong quyền shipping của phiên. PR giữ owner/scope, AC evidence, actual HEAD/base,
commands/results, CI links, data origin, contract impact, screenshot khi cần,
limitations, rollback và checkpoint. Partial checkpoint phải ghi rõ partial;
không gọi implemented là verified.

Reviewer người thật và integrator đối chiếu revision cuối, full local/hosted CI,
scope, evidence và conversations theo workflow/protection runbook. Merge thủ
công; agent không approve, merge, đóng issue/Epic hoặc nhận task tiếp theo.

## Chẩn đoán hook tùy chọn

Trong phiên agent-tool của provider tương ứng, có thể chạy:

```bash
python3 .github/scripts/harness.py canary --provider codex
```

Claude dùng `--provider claude`; `--session <actual-session-id>` thu hẹp chẩn
đoán khi có ID thực. Canary chỉ quan sát một PreToolUse call; PASS không chứng
minh tất cả tool được guard, role discovery, task gates hay human approval.
Khi hook thiếu/untrusted, ghi giới hạn và tiếp tục core CLI/workflow. Guard là
heuristic bổ sung cho policy/scope/CI; không tự trust hoặc tắt guard để bỏ gate.
