# Runtime V2 artifact pin

**Data type: simulated. No partner histories or real booking.**

| Item | Pin |
|---|---|
| Model | `lightgbm-0e9c6bb20db734dd` |
| Model SHA-256 | `0e9c6bb20db734ddffa8c171e3e0a94ae33459e8fc5b943c2b3366ea511a1ca8` |
| Calibrator | isotonic |
| Horizons evaluated | 15 / 30 / 60 / 90 / 120 / 180 minutes |
| Maximum horizon | 180 minutes |
| Base history | 169,344 snapshots, 14 stations × 3 scenarios × 14 days |
| Temporal split labels | 571,788 train / 208,656 calibration / 213,318 test |
| Boundary embargo | 180 minutes |
| Capacity model S001 +2 | `lightgbm-f01a2875bada1b0d` |
| Capacity model SHA-256 | `f01a2875bada1b0dea21f9a459a1ed25a4dce2d52b1b486ac8529e07e55f2683` |
| Base ZIP SHA-256 | `54d2b92dbd07dd25571cb8b2a0a0fe77f920558b45318db30d0e3794386d360e` |
| Capacity ZIP SHA-256 | `312f0e29f5062f0005d2de8d2f3bf9c1c280905c40c03ebfcd9f7505fc46ae6c` |

[Private draft release](https://github.com/thangak18/V-EV-Flow/releases/tag/untagged-5b6c7684302cfd5114e5) has simulator-v2-180m.zip and S001-plus2.zip.
Unpack the base ZIP into a new directory. Unpack the capacity ZIP into
`capacity-v2/S001-plus2/`. Verify each CHECKSUMS.sha256 before loading trusted
joblib. Keep binaries, SQLite, histories, generated fixtures and caches outside Git.
The release is an integration preview, not a certification of real-world accuracy.

[Runtime instructions](../../../../../docs/runbooks/runtime-completion.md) and
[simulated evaluation](../../../../../docs/runbooks/runtime-v2-evidence.md) record
commands, assumptions, multiple-seed results and rollback to V1. V1 remains intact.
