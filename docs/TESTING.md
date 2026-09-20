# Verification record — 2026-09-19

Tests use isolated temporary databases and independent Codex threads. The production `.workbench` administrator remains unset for the owner to configure.

## Executed checks

| Check | Actual result | Evidence |
|---|---|---|
| TypeScript | `tsc --noEmit` passed | `npm run typecheck` |
| Production frontend | Vite built public and private assets | `npm run build`, `tmp/build.log` |
| Backend/security | 12 pytest tests passed | `backend/test_auth.py`, `test_features.py`, `test_security.py` |
| 12 lesson notebooks | 12/12 ran in fresh isolated kernels | `output/notebook-test-results.json` |
| Actual server integration | Kernel state, isolation, chart, interrupt, restart, backup, AI and persistence passed | `output/live-test-results.json` |
| Browser main workflow | Login, tasks, chapter, note autosave, language, Notebook WebSocket, upload/search, publish and responsive layout passed | `tests/workbench.spec.ts` |
| Browser advanced workflow | ipynb import/run/export/reorder, dark mobile, sanitized Markdown/diagrams, backup restore, legacy import and keyboard passed | `tests/advanced.spec.ts` |
| Real Codex | Independent thread, actual stream, restart/resume, multi-turn marker, document citation, denied write, cancellation passed | `tools/probe_codex.py`, `tools/verify_live.py` |

Browser plugin was not available; regular Playwright Chromium was used. Desktop viewport: 1440×1000. Mobile viewport: 390×844. Runtime page errors were checked; the main flow reported none. Screenshots were inspected, not just generated:

- `output/workbench-desktop.png`
- `output/workbench-mobile.png`
- `output/notebook-mobile-dark.png`
- `output/public-project.png`

## Security coverage

- Unauthenticated requests cannot read private records, documents, notebooks, chats or backups, execute Python, open a kernel WebSocket, or call Codex.
- Foreign Origin and Host are denied. Unsafe authenticated requests require CSRF. Login throttles after 10 failed attempts.
- Invalid notebook output schemas, oversized uploads, wrong file types and malformed PDFs are rejected. A real PDF was parsed with retained pages; duplicate bytes under another name were recognized.
- Backup preview and confirmation are required; malformed backup rows fail validation. Auth data is excluded. Source IDs survive restore.
- Importing a chat ID does not grant ownership of a desktop Codex conversation.
- HTML/JavaScript Markdown payloads are not executed; unsafe links are removed; Mermaid SVG is sanitized.
- Missing Codex authentication and process failures produce real unavailable/error states. Unit tests emulate failures without changing the user's authentication; success checks call the actual configured Codex.

## Specific fixes found during verification

1. Retired both branches of the old unauthenticated Python endpoint, including its query-string bypass.
2. Selected the installed CLI's native executable and drained its reader before restart; this fixed premature EOF during Codex reinitialization.
3. Added explicit Jupyter interpreter selection to avoid inheriting global Anaconda kernels.
4. Added a bounded stop fallback for Windows blocking code; the affected kernel is terminated with an explicit variable-loss message.
5. Made chapter checkboxes update immediately and notes save through a serialized queue.
6. Used stable source IDs instead of allocation-order row numbers.
7. Verified Windows process-tree termination and a changed service instance ID before counting restart persistence as passed.
8. Disabled Mermaid HTML labels so sanitized SVG retains readable node text, and added a browser assertion for diagram labels.

## Limits and unverified external work

- No domain purchase, DNS change, public hosting or TLS deployment was performed.
- No real job application, GitHub CI run or demo video is claimed. These are course assignments to complete later.
- The 12 existing PDF URLs remain valid; the old PDFs were not rewritten into comprehensive textbooks in this implementation.
- Notebook lessons are reproducible teaching projects. Week 7 uses a clearly labeled TF-IDF/SVD baseline; Week 8's 30 regression questions are synthetic, not a human-labeled production benchmark.
- Notebook Python runs with administrator OS permissions; it is not a hostile-code sandbox. The server stays bound to loopback.
- Current JSON backups cover application data and notebook cells/outputs, not arbitrary files produced by kernels. Copy kernel artifacts separately while stopped.
- HTTPS/public deployment, distributed workers, cloud sync, multi-user accounts and OCR are outside this local implementation.
- Jupyter emits a Windows Proactor/selector compatibility warning and uses its supported extra selector thread. Backend tests also emit a dependency deprecation warning; neither failed the verified flows.
