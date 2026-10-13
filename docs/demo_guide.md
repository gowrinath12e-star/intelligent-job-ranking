# Faculty demonstration and viva guide

**Suggested length:** 10–15 minutes. Use synthetic data only. Launch from the project root with `python -m streamlit run app.py`; keep `python -m pytest -v` output ready in a second terminal.

## 1. Introduce the problem (one minute)

Say: “This application matches structured applicant evidence to explicit job criteria. It does not predict performance or automate hiring. My DSA contribution is a complete deterministic sorting workflow, bounded-heap top-K selection, and dictionary/set indexing.”

Open **Dashboard**. Point to uploaded, validated, shortlisted, average and highest score metrics. Explain that these are computed from the current file and current job, not literal dashboard constants. The shipped sample has 72 synthetic records. Exact scores of 100 are included in the last distribution bin.

## 2. Show real data validation (two minutes)

1. Open **Upload Applicants**.
2. Choose `data/validation_demo.csv`.
3. Inspect the preview and mapping form, then click **Validate & import applicants**.
4. Show 12 uploaded, 5 valid, 7 invalid. Open **Invalid records**.
5. Explain both repeated application-ID occurrences and both repeated candidate-ID occurrences are rejected; the system never arbitrarily keeps the first duplicate.
6. Open **Cleaning & duplicate IDs**; identify both groups and source rows.
7. Download rejected rows or the validation workbook. No invalid records were silently discarded.
8. Click **Reload synthetic sample** in the sidebar.

Optional variation: use `sample_applicants.xlsx` to demonstrate modern Excel, or rename `candidate_id` to `My Identifier` in a copy of the CSV and map it manually. Do not edit the bundled sample during the main demonstration.

## 3. Explain criteria and scores (two minutes)

1. Open **Job Requirements**. Show Python/SQL/Pandas/Git, minimum two years, target five years, education rubric, four weights and K.
2. Make weights total 105 and try saving. The form should reject the change; saved criteria remain intact.
3. Restore total 100 and save a valid change, or restore the example configuration.
4. Open **Candidate Ranking → Score explanation**.
5. Inspect `C001`: all four components match and the score is 100.
6. Inspect `C004`: experience is unknown, not zero. The experience component is unavailable; the other weights are renormalized and the score is visibly **Provisional**.
7. Explain why a high provisional score is not verified qualification: incomplete evidence can inflate apparent matches. Minimum experience is also review-pending.
8. Show matched/missing skills, component/status table, education reasoning and shortlist assessment.

If asked for a hand-calculation: Python+SQL → required 50; two years/target five → experience 40; B.Sc Computer Science → education 85; Docker only → additional 25. With 50/25/15/10 weights the result is **50.25**.

## 4. Demonstrate complete sorting (two minutes)

1. Open **Sorting Laboratory**.
2. Select **Merge Sort**, click **Run selected sort & verify**, and point to exact reference agreement.
3. Repeat with **Quick Sort**.
4. Click **Compare all three on this dataset**. Discuss median, min/max and repetition count.
5. Open the source files if needed:
   - Merge Sort repeatedly merges singleton/ordered runs; it does not delegate to `sorted()`.
   - Quick Sort uses a median-of-three pivot and genuine three-way partitioning.
   - The explicit stack avoids Python recursion-limit failures; it does not eliminate O(N²) worst-case inputs.
6. Show tied scores: candidate IDs order them deterministically. IDs are lexical; names never break ties.

## 5. Demonstrate a bounded heap (one minute)

1. Open **Heap Laboratory**.
2. Set K=3, leave the eligibility-gate experiment unchecked for a pure top-K demonstration, and run.
3. Show exactly three results and verified equality to the first three fully sorted records.
4. Explain the heap root is the **worst** of the current best K. A better incoming applicant replaces it.
5. Test K=0 and K>N; explain clamping by available data. Invalid K is rejected by the reusable function.
6. Emphasize that only retained K entries are sorted at the end; all N records were not first sorted to create the heap result.

## 6. Demonstrate hashing (one minute)

1. Open **Hashing Laboratory**.
2. Retrieve `C001`; then try `NOT-FOUND`.
3. Select Python and SQL under **All skills (intersection)**.
4. Switch to **Any skill (union)**; show the change in candidate count.
5. Inspect the inverted index and matched/missing skills.
6. Measure dictionary vs linear ID lookup; explain the timing is an equivalent query batch and index construction is separately measured.

## 7. Show human review separation (one minute)

1. Open **Shortlist Management**.
2. Choose a candidate and note its matching score and ordinal rank.
3. Set **Not shortlisted**, **Shortlisted** or **Needs review**, write a factual synthetic demonstration reason, and save.
4. Navigate to Dashboard/Ranking and back. The decision survives normal navigation; score and rank do not change.
5. Explain a manual inclusion can exceed K or bypass a gate, with a required reason and explicit source.
6. A manual exclusion/hold does not auto-refill a freed slot: the original heap suggestion and human decision remain distinct. Raise K or review another candidate explicitly if necessary.

## 8. Measure scaling (one to two minutes)

1. Open **Performance Analysis → Increasing input sizes**.
2. Choose N=100, 1000, 5000; five or seven repetitions; random order; K=25.
3. Run **Run measured benchmarks** and show actual scaling charts.
4. Repeat sorted or many-ties input if time permits.
5. Open **Complexity & methodology**. Contrast theoretical O(N log N), O(N log K) and average O(1) lookup with this machine's measured milliseconds.
6. Do not claim a universal winner from one test. The built-in baseline is optimized C code; educational Python loops have different constants.

## 9. Finish with exports and tests (one minute)

Open **Export Reports** and download the review shortlist Excel, component explanation report, validation report and benchmark report. Open one workbook: show meaningful headings, deterministic ranks, saved notes, and a job-criteria sheet. Standard analytics exclude email; the correction report can include supplied email only because it may need correction.

In the terminal, run `python -m pytest -v`. Explain the delivered suite covers boundary cases, nonmutation, missing evidence, duplicate IDs, genuine exports, actual measurements, integration and Streamlit controls. Report the actual result, not a promise; the supplied build's saved result is in `docs/test_results.txt`.

## Viva prompts and concise answers

| Question | Answer |
|---|---|
| Why more than one sorting algorithm? | To compare different DSA approaches on the same real ranking task with identical keys and a common reference. |
| What is the sorting key? | `(-final_score, str(candidate_id))`; ascending key order gives descending scores and ascending lexical IDs. |
| Is Merge Sort genuine? | Yes: bottom-up ordered-run merging using comparisons and an explicit workspace. |
| Why iterative Quick Sort? | Avoid recursion-depth failure; process smaller partitions first to limit the pending stack. |
| Is worst-case Quick Sort now O(N log N)? | No. Median-of-three is a practical pivot improvement, not an adversarial worst-case guarantee. |
| Why a min-heap for the best K? | The worst retained candidate must be easy to evict. Reversed rank-key comparison makes that candidate the heap root. |
| Can Python compare candidate dictionaries in this heap? | No. Heap entries compare only keys and unique source position, never payload dictionaries. |
| Why does top-K sort at the end? | It ranks only the retained K outputs; this is not a full N sort. |
| When should I use a heap? | Small K, top subset only, or streaming-style input. Use full sorting when all ranks are required. |
| Are hash lookups always O(1)? | O(1) average; worst-case collisions can make lookup O(N). |
| Why an inverted skill index? | Each normalized skill maps to a set of candidate IDs, so filters combine relevant buckets rather than repeatedly scanning all candidates. |
| Why not deduplicate names? | Different people can share a name. Only ambiguous identifiers are flagged. |
| Why is missing experience not zero? | Unknown evidence differs from known zero years; it is unavailable and causes visible provisional scoring. |
| Can a score be unavailable? | Yes: with no observed positively weighted component, the valid applicant is explicitly unscored and retained for review. |
| Does a recruiter override change the score? | No. Review status, note, shortlist source and score are separate fields. |
| Is the score unbiased or legally certified? | No such guarantee. Criteria appropriateness, incomplete evidence and decisions need human scrutiny. |
| What is benchmarked? | Actual algorithm calls, including key extraction and allocation, excluding I/O, generation, scoring and correctness checking. |
| Does the project require AI/internet? | No external AI or paid service; after dependency installation, the local core workflow works offline. |
| What is a genuine limitation? | Exact labels and structured evidence only; session memory rather than a persistent multi-user database. |

## Preparation checklist

- Install dependencies before the presentation; internet is unnecessary afterward.
- Use a readable browser zoom and keep sidebar navigation open.
- Keep the original sample, validation demo, README and algorithm source files accessible.
- Use 100–5000 generated candidates for a short demonstration; larger suites take longer.
- Clear accidental prior decisions or click **Return all candidates to Automatic** with confirmation.
- Export before closing/restarting because session memory is not a durable audit log.
- Present limitations and missing-evidence handling as design transparency, not as weaknesses to conceal.
