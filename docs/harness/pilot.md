# Pilot và chấp nhận dùng nhóm

## Hiện trạng

Ngày 11/10/2026: harness bootstrap xây bộ workflow/policy/CLI/adapters/checks. Bằng chứng implementation tests thuộc PR bootstrap; tài liệu này không tự chứng nhận PASS. Foundation có historical CI xanh nhưng **review độc lập BLOCKED** chờ người thật, theo [Foundation record](../runbooks/phase-0-handoff.md). H8/pilot và team adoption **NOT RUN**. Chưa triển khai P1/P2 product features trong tooling PR.

| Backlog | Deliverable trong bootstrap | Acceptance còn cần |
| --- | --- | --- |
| H0 | Governance, immutable origin, manual gate | Independent Foundation reviewer và handles thực: BLOCKED |
| H1 | Shared workflow/instructions/onboarding; sửa plan drift | Fresh-user walkthrough: NOT RUN |
| H2 | Discovery/build/smoke/generation gates | Execution evidence trên exact PR SHA |
| H3 | Issue/PR/handoff/evidence formats | Real issue walkthrough: NOT RUN |
| H4 | Stdlib CLI và evidence | Automated fixtures + final gate evidence |
| H5 | Canonical onboarding/stage skills, explicit-only alias, read-only roles và generated hooks | Native discovery/trust của assets mới, PreToolUse/canary, role execution: NOT RUN |
| H6 | Trusted-base scope CI, artifact retention | Hosted PR CI/review gate: NOT RUN trước PR |
| H7 | Scope/stale-evidence/resume/hook regressions | Test/CI evidence tại PR; không suy ra từ docs |
| H8 | Pilot specs và cùng rubric | P1–P3, desktop probe, adoption: NOT RUN |

Người phụ trách tạo issues thật bằng form, giao owner/reviewer, accepted Foundation record trước khi chạy feature lane. Không dùng mã P1/P2/H0 như GitHub Issue ID.

## P1 — Codex: JSON station repository

Tạo issue lane `recommend-api`, phạm vi JSON metadata adapter và conformance tests theo [plan C](../superpowers/plans/2026-10-11-c-kien-backend-recommendation.md). Không lấy toàn bộ file backend/status-window/model integration vào pilot.

- AC-01: fixture JSON nhỏ validate Station model hiện có, thứ tự xác định, giữ nguồn dữ liệu.
- AC-02: duplicate ID/schema/capacity sai bị từ chối; station không tồn tại dùng `StationNotFoundError` sẵn có.
- AC-03: mock/file chạy cùng conformance tests; DTO/OpenAPI unchanged.
- AC-04: scope đúng, focused tests và fresh `make ci`/CI đúng SHA, limitations rõ.

Status: **NOT RUN**. Codex dừng ở checkpoint có regression test và phần còn lại; Claude tiếp tục theo P3.

## P2 — Claude Code: `listStations` envelope

Tạo issue lane `web-map`, phạm vi service/tests và UI error/retry cần thiết theo [plan D](../superpowers/plans/2026-10-11-d-tu-frontend-map.md), không thêm dependency/generated types.

- AC-01: chấp nhận `stations` array rỗng và `mock/simulated/real/mixed`; `source_notes` đúng kiểu.
- AC-02: root null/array, thiếu/sai kiểu trường, enum sai và extra envelope keys trả `ApiError` code `invalid_response`.
- AC-03: network/error/abort behavior giữ như trước; service/error-retry tests và artifacts liên quan.
- AC-04: focused tests, build, fresh `make ci`/CI, scope/HEAD evidence; ghi rõ chưa validate đầy đủ từng Station.

Status: **NOT RUN**. Claude bàn giao phần kiểm chứng/AC còn lại để Codex tiếp tục.

## P3 — Bàn giao, checkout mới, runtime hooks

Hai chiều dùng phiên mới không lịch sử chat; đọc handoff, lấy issue mới, đối chiếu hash/branch/base/HEAD/diff/dependencies trước sửa. Thành viên khác clone checkout mới bằng quyền/tài khoản của mình, chỉ làm theo onboarding repo. Test stale PASS sau commit/base đổi, scope violation và missing prerequisite; readiness phải fail/block.

Codex desktop cần probe riêng cho instructions/skill/hooks/check. Claude Desktop/IDE/cloud giữ NOT RUN cho tới profile thực được chạy. Diễn tập hook malformed input, timeout, missing script/Python, subdirectory/worktree, hooks disabled; Stop không tạo lượt mới. Tích hợp hai lane tuần tự, merge base mới và chạy lại gate.

Probe canonical stage skills và alias invocation policy riêng, rồi optional
PreToolUse canary theo provider/session: PASS chỉ chứng minh một observation.
Diễn tập generated edits, protected owner paths, force/main push, staged
env/secret commit và safe `.env.example` copy. Tooling/contract exception phải
khớp policy, guard unavailable không thay scope/evidence/full CI. Named roles
hoặc read-only canonical-prompt fallback phải báo actual HEAD/base, AC evidence,
`BLOCKED`/`NOT RUN`; không có GitHub writes hoặc fabricated human approval.
QA mặc định một agent phụ đồng thời, chỉ chạy khi requested/plan warranted.

Status: **NOT RUN**.

## Record và rubric dùng chung

Mỗi lượt ghi tool/surface/version, issue/branch/head/base, start/end/active/wait time, questions do thiếu context, số vòng sửa, agent phụ, usage khi có, clarification tách khỏi yêu cầu mới, AC artifacts, false PASS/stale evidence/scope violations, review findings và resume time. Không đo được token/usage phải ghi “không đo được”.

| Probe | Tool/surface/version | HEAD/base | Result | Evidence | Blocker/next step |
| --- | --- | --- | --- | --- | --- |
| P1 | Codex CLI 0.160.0 dự kiến | Chưa chạy | NOT RUN | Chưa có | Tạo/giao issue sau review |
| P2 | Claude Code CLI 2.1.78 dự kiến | Chưa chạy | NOT RUN | Chưa có | Tạo/giao issue sau review |
| P3 Codex → Claude | Local CLI | Chưa chạy | NOT RUN | Chưa có | Hai tài khoản hoạt động |
| P3 Claude → Codex | Local CLI | Chưa chạy | NOT RUN | Chưa có | Hai tài khoản hoạt động |
| Fresh checkout member | Máy/thành viên mới | Chưa chạy | NOT RUN | Chưa có | Quyền clone/thành viên thực |
| New stage skills / alias policy | Codex và Claude native profiles | Chưa chạy | NOT RUN | Chưa có | Discover assets mới và human-request gating |
| PreToolUse guard / canary | Codex và Claude native profiles | Chưa chạy | NOT RUN | Chưa có | Safe/blocked calls và one-observation diagnostic |
| Review / QA roles / fallback | Runtime role API hoặc read-only prompt | Chưa chạy | NOT RUN | Chưa có | Scoped evidence, không write/approve GitHub |
| Codex desktop probe | Engine/version cần ghi | Chưa chạy | NOT RUN | Chưa có | Trust/discovery runtime |
| Claude Desktop/IDE/cloud | Profile riêng | Chưa chạy | NOT RUN | Chưa có | Chưa trong baseline |

Read-only probes trong lượt bootstrap: Codex CLI 0.160.0 đọc instructions/skill/workflow thành công; Claude Code 2.1.78 discover skill và chạy SessionStart hook thành công, nhưng model response BLOCKED sau API retries/timeout 120 giây. Xem [compatibility](compatibility.md) để biết phạm vi quan sát và logs. P1/P2/P3 vẫn NOT RUN.

Các probe cũ được giữ nguyên. Chúng không chứng nhận các generated assets,
stage skills, guard/canary hoặc QA roles mới. Comparison/provenance của thay đổi
harness theo [LMAO reference](lmao-reference.md) không phải runtime evidence.

Chấm cùng rubric: đúng AC, đủ evidence, đúng scope, tái hiện được, handoff đủ để tiếp tục. P1/P2 khác task chỉ chứng minh dùng chung workflow. Muốn đánh giá thời gian/usage, baseline vs harness phải cùng tình huống/base/công cụ/rubric; không kết luận nhân quả từ task khác nhau.

## Điều kiện team adoption

1. Thành viên khác setup được từ checkout mới, không cần bước ngoài tài liệu.
2. Hai công cụ mỗi bên hoàn thành ít nhất một issue bằng cùng workflow/evidence.
3. Hai chiều resume thành công không cần lịch sử chat.
4. Scope/stale-evidence/missing-prerequisite tests không thể thành review-ready; false PASS = 0.
5. Lane integration/base change kích hoạt kiểm chứng lại.
6. Exact revision sạch có local `make ci`, CI và reviewer non-author thật; integrator merge thủ công.
7. Matrix chỉ ghi PASS cho surface/version đã chạy; hook disabled fallback giữ cùng chất lượng.

Logs/traces giữ 14 ngày; PR giữ summary/SHA/results/limitations lâu dài. Nếu GitHub protection chưa khả dụng, integrator ghi manual checklist. Khi gói/quyền thay đổi, bật policy protection và test lại gate; không tự giả định được cưỡng chế.
