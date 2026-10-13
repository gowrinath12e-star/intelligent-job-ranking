# Delivered acceptance checklist

Evidence for the supplied build: `docs/test_results.txt`, `docs/browser_verification.txt`, actual screenshots, and inspectable source. These checks refer to the delivered Linux/Python 3.13 environment; the Windows execution commands are documented but native Windows execution was not available.

| # | Acceptance item | Delivered evidence |
|---|---|---|
| 1 | Application launches | Live Streamlit server returned HTTP 200; Chromium rendered actual pages without exceptions |
| 2 | Upload and validate applicant data | Browser verified CSV, `.xlsx`, custom heading mapping, 5 valid/7 invalid validation-demo accounting and correction download |
| 3 | Configure job requirements | Editable validated Streamlit form; invalid weights leave saved criteria intact; UI tests |
| 4 | Calculate actual scores | Deterministic scoring engine, actual-file dashboard, range and explanation tests |
| 5 | Merge Sort works | Genuine bottom-up divide-and-conquer merge implementation, reference/boundary/large-input tests |
| 6 | Quick Sort works | Genuine median-of-three partition implementation, explicit stack, reference and ordered-input tests |
| 7 | Built-in baseline works | Shared score/ID key, reference checks on actual and generated inputs |
| 8 | Heap top-K works | Real bounded `heapq` selection; K=0/1/N/N+ and duplicate dictionary payload tests |
| 9 | Dictionary candidate lookup works | Live candidate-ID index, existing/missing ID tests, browser/UI laboratory |
| 10 | Set skill matching works | Real normalization/intersection/difference/inverted-index filters and tests |
| 11 | Ranking and shortlist integrate | Reusable pipeline, heap suggestions before complete sorting, eligibility/threshold/manual-review tests |
| 12 | Score explanations exist | Component/status/weight/contribution/skill/rubric reasoning; actual provisional-candidate screenshot |
| 13 | CSV and Excel exports work | OpenPyXL workbook-content tests and real browser downloads of rankings, shortlist and reports |
| 14 | Performance can be measured | `perf_counter`, warmups, rotated repeated equivalent calls and median/min/max output |
| 15 | Measurements are real | Every timed result verified; measured charts/screenshots; no fabricated defaults |
| 16 | Automated tests cover main workflows | Executed unit/export/benchmark/pipeline/AppTest suite; saved verbose output |
| 17 | Complete installation/execution instructions | README Command Prompt/PowerShell/direct-interpreter/macOS/Linux/test commands and troubleshooting |
| 18 | Modular understandable code | Small `app.py`; focused `core`, `algorithms`, `utils` and `ui` modules; type hints/docstrings/pseudocode |
| 19 | No essential placeholder implementations | Required controls call working services; empty states show real absence rather than fake data |
| 20 | Ready for college demonstration | 72-row synthetic CSV/XLSX, deliberate invalid demo, actual screenshots, faculty speaking guide and viva questions |

## Scope disclosures

- Modern Excel `.xlsx` is supported; legacy `.xls` is intentionally excluded.
- The optional custom hash table is omitted; actual application hashing uses built-in dictionaries and sets.
- Resume parsing, external AI, persistence/authentication, durable audit logs, production hardening and fairness/legal certification are not implemented and are documented as limitations/future enhancements.
- No benchmark result establishes a universal speed ranking. Theoretical memory figures are not presented as measured peak memory.
- Unknown experience/education is explicitly provisional/unscored, not zero; unknown minimum experience is human-review pending, not verified eligibility.
