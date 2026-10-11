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
| Desktop | Chuẩn chung | Codex desktop cần probe riêng | Claude Desktop Code tab chưa kiểm tra | NOT RUN |
| IDE/cloud | Chuẩn chung | Profile riêng | Profile riêng | NOT RUN |

## Read-only CLI probes — 11/10/2026

Các probe chạy trên checkout bootstrap chưa commit (HEAD Foundation `27d421265fe57736d3070c241544e3756772e52b`, dirty). Đây là quan sát discovery, không phải bằng chứng gate của final commit hoặc pilot coding.

- Codex CLI 0.160.0: một phiên ephemeral, sandbox read-only, exit 0; đọc được root AGENTS, skill `vev-issue`, workflow và policy, nêu đúng Foundation review BLOCKED. Không chạy issue workflow.
- Claude Code CLI 2.1.78: init event liệt kê `vev-issue`; native SessionStart hook chạy exit 0 và đưa đúng context. Model call retry rồi bị dừng cả process group sau 120 giây; phản hồi model **BLOCKED**, nguyên nhân API chưa xác định. Stop chưa được quan sát.
- Log local ignored: `.harness/probes/codex.jsonl`, `.harness/probes/claude.jsonl`. Không cần các log cá nhân này để chạy workflow; PR ghi summary, CI cung cấp kiểm chứng độc lập của script/tests.

Fixtures kiểm tra protocol, stale evidence, worktree và clone mới đều thuộc automated tests; chúng không thay cho thành viên khác chạy pilot P1–P3. Native trust/discovery phải kiểm tra lại khi đổi surface/version.

## Cấu hình và trust

Repo không chọn model/tài khoản, nới quyền, ghi credentials hay sửa global config. Người dùng tự đăng nhập công cụ và `gh`; setup cài theo lockfiles. MCP/plugin cá nhân là tùy chọn; Git/gh + scripts là fallback.

Runner lưu version tự phát hiện ở `tool.cli_version`. `tool.version` chỉ dùng giá trị đó cho surface `cli`; surface khác ghi `NOT VERIFIED` cho tới khi engine/profile được kiểm chứng riêng. Không dùng binary CLI trên máy để chứng nhận desktop engine.

Codex hooks được bật bằng `.codex/config.toml`, định nghĩa JSON ở cùng lớp project. Người dùng phải trust project và review/trust hook definitions trong UI/prompt của công cụ; không tự ghi trust vào global config. Hook commands dùng Git root được quote để hoạt động từ subdirectory. [Tài liệu Codex hooks](https://learn.chatgpt.com/docs/hooks).

Claude hooks dùng `CLAUDE_PROJECT_DIR`; JSON stdin cho state reader có cwd. SessionStart đưa context, Stop chỉ `systemMessage` exit 0: không blocking decision, không yêu cầu thêm turn, không dùng `Stop.additionalContext` của bản mới cho baseline 2.1.78. [Hooks docs](https://code.claude.com/docs/en/hooks), [ví dụ 2.1.78](https://github.com/anthropics/claude-code/blob/v2.1.78/plugins/explanatory-output-style/hooks/hooks.json).

Hooks chỉ đọc Git/state, không network/write/setup/tests/commit; timeout 5 giây, output khoảng 1 KB. Lỗi/malformed input/missing script không là PASS của task. Khi hook không chạy, đọc workflow và gọi script thủ công, giữ gate cuối như cũ.

Fallback prompt cho cả hai công cụ:

> Đọc AGENTS.md áp dụng, docs/harness/workflow.md và nearest SPEC/plan. Chạy python3 .github/scripts/harness.py doctor, rồi start --issue N. Theo workflow chung và dùng evidence theo revision; không tự claim/merge hoặc đánh dấu kiểm tra chưa chạy là PASS.

## Probe khi nâng version

1. Phiên mới từ root/backend/frontend đọc đúng instructions và locate skill.
2. Gọi skill explicit cho issue fixture/read-only probe; giữ URL/hash đúng.
3. SessionStart/Stop từ subdirectory/worktree, hook tắt/thiếu script/malformed JSON/timeout; không tạo turn tiếp hoặc tests.
4. Hai công cụ dùng cùng failure fixture và stale-evidence fixture, kết quả như nhau.
5. Resume từ handoff không có lịch sử chat; kiểm tra issue/base/HEAD.

Ghi từng profile PASS/FAIL/BLOCKED/NOT RUN tại [pilot](pilot.md). Không suy ra CLI PASS cho desktop/IDE/cloud hoặc bản nâng cấp. Usage subscription chỉ ghi nếu có số liệu; không tự dùng API trả phí khi quota hết.

Tham khảo chính thức: [Codex AGENTS](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [Codex config](https://learn.chatgpt.com/docs/config-file/config-basic), [Claude memory](https://code.claude.com/docs/en/memory), [Claude skills](https://code.claude.com/docs/en/skills), [Claude settings](https://code.claude.com/docs/en/settings).
