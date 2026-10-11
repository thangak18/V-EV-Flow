# Tham khảo LMAO và phạm vi áp dụng

So sánh read-only ngày 11/10/2026 với checkout LMAO-Web tại
`/Users/mac/KhoChua/WEB-TLBB/LMAO-Web`, HEAD
`c685767a3988ee951b99f26322e6e3d0e15a7fe0` (tracked files sạch; có local
untracked artifacts không dùng cho adaptation). Không chạy sync/setup/hooks/skills
hoặc sửa repository tham khảo. Đây là provenance thiết kế; không chứng nhận
runtime tương thích hoặc thay [workflow](workflow.md)/[policy](policy.json).

| Cơ chế tham khảo | Bằng chứng nguồn LMAO | Áp dụng tại V-EV |
| --- | --- | --- |
| Canonical skills/agents/hooks cho hai tool | `.agents/README.md:7–20`, `scripts/harness/sync.mjs:85–164` | `.agents/` là source; Python generator trong `.github/scripts/harness_assets.py`; Codex đọc skills trực tiếp, Claude nhận bản generated |
| Drift/missing/extra và bảo toàn Claude settings | `scripts/harness/sync.mjs:181–220` | `harness.py sync --check` và harness gate; chỉ hook key của settings do generator quản lý |
| Metadata skill và invocation policy | `scripts/harness/sync.mjs:60–82,95–102` | JSON frontmatter hợp lệ YAML; vev alias explicit-only, stage skills discoverable |
| Normalize shell/file edits trước guard chung | `scripts/harness/hooks/normalize.mjs:6–38,55–84` | Guard adapter dùng chung, paths/exceptions đọc từ V-EV policy; tests theo payload hai provider |
| Touched packages và consumer checks | `scripts/harness/verify.mjs:30–56` | `verify --issue N` chọn fixed Make gates; full `make ci` vẫn là final requirement |
| Plan, read-only reviewer và independent QA judge | `task-start/SKILL.md:50–63`, `agents/code-reviewer.md:11–23,38–50`, `agents/qa-dispatcher.md:12–38` dưới `.agents/` | AC plan/handoff có sẵn; shared review/QA prompts read-only, evidence/revision và human review giữ nguyên |
| Coverage, reproduction và evidence-relative paths | `.agents/skills/epic-qa/references/findings-schema.md:14–40,57–78` | QA report gắn AC/assertion/artifact; caller giữ evidence theo schema V-EV hiện có, không thêm format cạnh tranh |

## Cơ chế giữ theo V-EV

- **Con người giao việc và manual merge.** Không nhập auto-claim, pick-next,
  `issue-N-slug` branch creation (`task-start:25–48`, `gh/claim.mjs:34–46`), bulk
  `issue-batch`, standing-rule auto-merge (`issue-batch:71–86`) hoặc Epic auto-close
  (`epic-qa:64–75`). Bốn owner lanes/Foundation origin và tooling/contract
  exceptions tiếp tục đọc từ policy.
- **Portable per-issue state.** LMAO member loop dùng plan comment và output/PR
  table; local resume state của `gh/apply-plan.mjs:28,150–158` phục vụ backlog
  import, QA directory phục vụ Epic run. V-EV giữ issue snapshots, tracked handoff,
  issue hash, tested HEAD/base, dirty fingerprint và artifact hashes hiện có.
- **Execution proof.** LMAO case-ID PASS chỉ tra registry (`verify.mjs:148–154`),
  và `PARTIAL`/`NOT RUN` vẫn exit 0 (`verify.mjs:158–168`). V-EV cần AC assertions,
  đúng revision, honest statuses và fresh clean-revision full CI. Canary tùy chọn
  chỉ chứng minh một PreToolUse observation, không thay core readiness.
- **Product rules.** Không nhập Go/Supabase/payments/borrowed-asset/reference-site
  constraints (`AGENTS.md:34–51,92–103`), visual cloning hoặc accessibility warning
  exception (`qa-accessibility.md:18–23`). V-EV là Python/React mock vertical slice
  với contracts và data-origin requirements của chính repo.
- **Local environment.** LMAO blanket env-write ban (`hooks/rules.mjs:68,118–120`)
  không áp dụng: V-EV cho phép copy `.env.example` sang `.env` local, nhưng cấm
  commit env/credentials. Guard là heuristic supplementary CI/review, không là
  security boundary hoặc lý do tự trust/override.
- **Optional capabilities.** Không vendor bulk skills, cài personal plugins,
  thêm paid API hoặc chọn model. `project-init` là onboarding, không backlog
  creation. Named roles có canonical-prompt fallback; runtime mới giữ `NOT RUN`
  tới khi có probe thật, mặc định một QA subagent đồng thời.

Nguồn kiểm chứng thực tế nằm trong [compatibility](compatibility.md),
[pilot](pilot.md) và PR evidence. Generator/unit checks không thay native
discovery/trust/guard/role execution trên đúng surface/version.
