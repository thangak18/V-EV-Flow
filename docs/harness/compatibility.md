# Baseline và kiểm chứng tương thích

Baseline local dự kiến: **Codex CLI 0.160.0**, **Claude Code CLI 2.1.78**. `--version` chỉ chứng minh CLI được cài. Adapter tồn tại/schema fixture đạt không chứng minh phiên agent đã discover/trust/chạy workflow. Các probe runtime thực cần ghi ngày, exact version, surface, task, result, tested SHA và evidence.

| Khả năng | Dùng chung | Codex | Claude Code | Runtime status |
| --- | --- | --- | --- | --- |
| Instructions | Bốn AGENTS, SPEC/contracts | Native AGENTS + đọc subtree | Bốn CLAUDE import `@AGENTS.md` | Codex root PASS; subtree/Claude import runtime NOT RUN |
| Workflow skill | Một workflow và CLI | `.agents/skills/vev-issue`, `$vev-issue` | `.claude/skills/vev-issue`, `/vev-issue` explicit | PASS discovery trong read-only CLI probe; issue workflow NOT RUN |
| Issue/setup/checks | Git/gh, Makefile, runner | Shell | Bash/shell | CLI fixtures/test evidence riêng, agent runtime NOT RUN |
| SessionStart/Stop | Read-only state reader | `.codex/hooks.json` | `.claude/settings.json` | Claude SessionStart PASS; Stop và Codex native hooks NOT RUN |
| Resume | Handoff + Git + issue hash | Native `codex resume` tùy chọn | Native `claude --resume` tùy chọn | NOT RUN bàn giao hai chiều |
| PR/review | Cùng rubric/evidence/gates | CLI/prompt | CLI/prompt | NOT RUN pilot |
| Canonical asset generation | `.agents/` và `harness.py sync --check` | Direct skills; generated roles/hooks | Generated skills/roles/hooks | Claude role discovery PASS; invoking roles/stage skills và Codex roles NOT RUN |
| PreToolUse guard/canary | Shared heuristic guard và optional observation | Generated PreToolUse definition | Generated PreToolUse definition | New native guard/canary runtime NOT RUN |
| Scoped verification | Fixed Make gates + same evidence manifest | `verify --issue N [--full]` | Cùng CLI | Automated checks ở PR; real-issue stage flow NOT RUN |
| Desktop | Chuẩn chung | Codex desktop cần probe riêng | Claude Desktop Code tab chưa kiểm tra | NOT RUN |
| IDE/cloud | Chuẩn chung | Profile riêng | Profile riêng | NOT RUN |

## Read-only CLI probes — 11/10/2026

Các probe chạy trên checkout bootstrap chưa commit (HEAD Foundation `27d421265fe57736d3070c241544e3756772e52b`, dirty). Đây là quan sát discovery, không phải bằng chứng gate của final commit hoặc pilot coding.

- Codex CLI 0.160.0: một phiên ephemeral, sandbox read-only, exit 0; đọc được root AGENTS, skill `vev-issue`, workflow và policy, nêu đúng Foundation review BLOCKED. Không chạy issue workflow.
- Claude Code CLI 2.1.78: init event liệt kê `vev-issue`; native SessionStart hook chạy exit 0 và đưa đúng context. Model call retry rồi bị dừng cả process group sau 120 giây; phản hồi model **BLOCKED**, nguyên nhân API chưa xác định. Stop chưa được quan sát.
- Log local ignored: `.harness/probes/codex.jsonl`, `.harness/probes/claude.jsonl`. Không cần các log cá nhân này để chạy workflow; PR ghi summary, CI cung cấp kiểm chứng độc lập của script/tests.

Fixtures kiểm tra protocol, stale evidence, worktree và clone mới đều thuộc automated tests; chúng không thay cho thành viên khác chạy pilot P1–P3. Native trust/discovery phải kiểm tra lại khi đổi surface/version.

Sau nâng canonical assets theo [LMAO reference](lmao-reference.md), các probe
trên vẫn là historical evidence của skill/hook cũ. Không dùng chúng để ghi PASS
cho `project-init`, stage skills, PreToolUse guard/canary hoặc named review/QA
roles mới. Những native capabilities đó giữ **NOT RUN** tới probe thực trên
tested SHA/surface/version; generator và unit fixtures chỉ chứng minh cơ chế
render/protocol được kiểm tra.

### Probe sau nâng cấp assets — 11/10/2026

Trên working tree nâng cấp chưa commit (HEAD `b68f039`, dirty),
`claude agents --setting-sources project` chạy exit 0 và liệt kê đúng bốn project
roles: `code-reviewer`, `qa-backend`, `qa-dispatcher`, `qa-e2e`, đều inherit model.
Đây là **PASS discovery metadata**, không phải invocation/QA hoặc bằng chứng
gate của final commit. Không gọi model Claude thêm cho probe này.

`codex doctor --json` xác nhận config load/parse được trên CLI 0.160.0; report
có warning về một role global `subagent` thiếu description, không thuộc các
project roles mới. Không chỉnh cấu hình cá nhân để loại warning. Canary gọi
riêng qua tool tại phiên hiện tại trả **BLOCKED**, không có matching receipt;
native guard/trust/invocation vẫn chưa được xác nhận. Automated fixtures kiểm
tra normalize/deny/receipt của cả hai provider và sync drift; core workflow có
thể chạy khi chưa dùng hooks.

## Cấu hình và trust

Repo không chọn model/tài khoản, nới quyền, ghi credentials hay sửa global config. Người dùng tự đăng nhập công cụ và `gh`; setup cài theo lockfiles. MCP/plugin cá nhân là tùy chọn; Git/gh + scripts là fallback.

Runner lưu version tự phát hiện ở `tool.cli_version`. `tool.version` chỉ dùng giá trị đó cho surface `cli`; surface khác ghi `NOT VERIFIED` cho tới khi engine/profile được kiểm chứng riêng. Không dùng binary CLI trên máy để chứng nhận desktop engine.

Codex hooks được bật bằng `.codex/config.toml`, định nghĩa JSON ở cùng lớp project. Người dùng phải trust project và review/trust hook definitions trong UI/prompt của công cụ; không tự ghi trust vào global config. Hook commands dùng Git root được quote để hoạt động từ subdirectory. [Tài liệu Codex hooks](https://learn.chatgpt.com/docs/hooks).

Claude hooks dùng `CLAUDE_PROJECT_DIR`; JSON stdin cho state reader có cwd. SessionStart đưa context, Stop chỉ `systemMessage` exit 0: không blocking decision, không yêu cầu thêm turn, không dùng `Stop.additionalContext` của bản mới cho baseline 2.1.78. [Hooks docs](https://code.claude.com/docs/en/hooks), [ví dụ 2.1.78](https://github.com/anthropics/claude-code/blob/v2.1.78/plugins/explanatory-output-style/hooks/hooks.json).

SessionStart/Stop chỉ đọc Git/state, không network/setup/tests/commit, không
blocking decision hoặc tạo thêm lượt. PreToolUse normalize tool actions rồi
đối chiếu shared guard với policy: generated output edits, force/main push,
committing env/secrets, protected owner paths và harness self-edits ngoài tooling
lane/bootstrap. Tooling/contract exceptions đọc policy, không tự cấp quyền bằng
hook adapter. Copy `.env.example` sang `.env` local được phép. Guard có thể ghi
ephemeral diagnostic observation trong ignored `.harness/`; không là evidence
PASS cho task. Hooks dùng timeout ở policy và bounded output.

Guard là heuristic bổ sung, CI/scope/human review vẫn là backstop. Missing,
untrusted, malformed input hoặc hook error không chứng nhận một action an toàn,
không thay core gates. Khi hook không chạy, đọc workflow và dùng CLI thủ công.
Canary `harness.py canary --provider codex|claude [--session ID]` chỉ kiểm tra một
PreToolUse observation, không chứng minh all-tool coverage, role discovery hoặc
readiness. Không tự trust, override policy, claim/branch/merge để qua diagnostics.

Canonical roles render vào provider folders nhưng native named-role availability
phải probe riêng. Khi thiếu role API, đọc `.agents/agents/<name>.md` và dùng cùng
prompt với read-only subagent hoặc human reviewer. Model inherits phiên; không
chọn model/quyền/paid API từ role. Reviewer/QA không sửa product/tests hoặc ghi
GitHub, caller lưu report. Agent verdict không thay human approval; unavailable
role/check được disclose `NOT RUN` và không làm giả review.

Fallback prompt cho cả hai công cụ:

> Đọc AGENTS.md áp dụng, docs/harness/workflow.md và nearest SPEC/plan. Chạy python3 .github/scripts/harness.py doctor, rồi start --issue N. Theo workflow chung và dùng evidence theo revision; không tự claim/merge hoặc đánh dấu kiểm tra chưa chạy là PASS.

## Probe khi nâng version

1. Phiên mới từ root/backend/frontend đọc đúng instructions và locate skill.
2. Gọi skill explicit cho issue fixture/read-only probe; giữ URL/hash đúng.
3. SessionStart/Stop từ subdirectory/worktree, hook tắt/thiếu script/malformed JSON/timeout; không tạo turn tiếp hoặc tests. PreToolUse kiểm tra safe/blocked payloads, local env copy, generated output, protected scope, canary observation đúng provider/session và fallback khi hooks không chạy.
4. Hai công cụ dùng cùng failure fixture và stale-evidence fixture, kết quả như nhau.
5. Resume từ handoff không có lịch sử chat; kiểm tra issue/base/HEAD.
6. Discover stage skills và explicit-only alias; start/ship thiếu assigned issue/human request không tự pick/claim/branch/ship. Probe named review/QA role hoặc canonical-prompt fallback; reports gắn actual HEAD/base/AC evidence, không ghi GitHub hay giả human approval.

Ghi từng profile PASS/FAIL/BLOCKED/NOT RUN tại [pilot](pilot.md). Không suy ra CLI PASS cho desktop/IDE/cloud hoặc bản nâng cấp. Usage subscription chỉ ghi nếu có số liệu; không tự dùng API trả phí khi quota hết.

Tham khảo chính thức: [Codex AGENTS](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Codex config](https://learn.chatgpt.com/docs/config-file/config-basic), [Claude memory](https://code.claude.com/docs/en/memory), [Claude skills](https://code.claude.com/docs/en/skills), [Claude settings](https://code.claude.com/docs/en/settings).
