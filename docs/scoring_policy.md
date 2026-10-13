# Scoring and review policy

This note records explicit design decisions that are easy to miss during a dashboard demonstration.

## 1. What is measured

The final number is a **job-criteria matching score**. It is not a predicted probability of success, a measure of overall applicant quality, an AI opinion, or a hiring approval. It uses only normalized skills, supplied experience years and a configured job-related education rubric. Name, email and extra protected/irrelevant columns do not enter component calculations. Candidate ID is a deterministic tie-break identifier, not a component feature.

The formula is a weighted **sum** of 0–100 components. The configured percentages total 100; active observed percentages are renormalized when needed. The final value is stored to six decimals. Display rounding to two decimals can make different stored scores look tied; the algorithms sort stored values, then lexical candidate ID.

## 2. Missing job components versus unknown candidate evidence

| Situation | Component treatment | Evidence status |
|---|---|---|
| Job has no required skills | Unconfigured; excluded | Does not make a candidate provisional |
| Job has no additional skills | Unconfigured; excluded | Does not make a candidate provisional |
| Experience scoring disabled | Unconfigured; excluded | Does not make a candidate provisional |
| Empty education rubric / disabled education | Unconfigured; excluded | Does not make a candidate provisional |
| Configured component has zero weight | Excluded from final score | Unknown data in it alone does not make a candidate provisional |
| Experience/education unknown in a configured positive-weight component | `None`, never zero; exclude and renormalize available weights | Provisional |
| All positive-weight evidence unknown | No numeric score or rank | Unscored; retained for human review |
| Candidate explicitly supplies zero experience | Observed score of zero | Complete with respect to experience evidence |
| Supplied education label does not match the rubric | Configured unmatched-label score | Observed, not missing |
| Blank skill cell | Reported empty set; no assumed matches | A source warning; matching percentage is honestly zero if configured skills are unmatched |

Renormalization can inflate apparent matches on incomplete evidence. The UI presents warnings and effective candidate weights so a recruiter can assess comparability. Do not rank provisional evidence as verified qualification simply because the number is high.

## 3. Example of renormalization

Configured weights: required 50, experience 25, education 15, additional 10.

An applicant has unknown experience but matches all other components. Available configured weight is 75. Effective weights become:

- Required: 50/75 × 100 = 66.666…%
- Experience: 0% (unavailable; component score remains None)
- Education: 15/75 × 100 = 20%
- Additional: 10/75 × 100 = 13.333…%

The matching score is 100 **Provisional**, not a fabricated complete-evidence score. Sample `C004` deliberately demonstrates this. Its minimum-experience gate is unknown and must be reviewed.

## 4. Education criteria

The rubric is a recruiter-configured exact normalized label → score map, plus a separate unmatched-provided-label score. It is not a universal degree hierarchy. Criteria should be relevant and justified for the role. The system cannot certify that a user's chosen criteria are appropriate, unbiased or legally compliant. Disable the component if no defensible education requirement is configured.

No graduation year, institution prestige, sensitive characteristic or inferred qualification is extracted. Missing education is not confused with a provided but unmatched label.

## 5. Minimum experience and threshold

These affect **automatic suggestions**, not the numeric ranking itself:

- Known experience below minimum: not auto-suggested; explicit reason; still ranked and manually reviewable.
- Unknown experience: minimum cannot be verified; numeric/provisional records remain eligible for a **review-pending suggestion**, not verified eligibility.
- Optional score threshold: known scores below it are not auto-suggested; equality qualifies.
- No available score: cannot enter numeric heap selection; retained as unscored.
- K=0: no automatic suggestions.
- K greater than eligible count: return all eligible candidates, never invent rows.

No missing optional value silently discards an otherwise valid applicant.

## 6. Human review fields

`final_score`/`rank` and `review_status`/`review_note` are independent.

- Automatic: follow the suggested heap subset.
- Shortlisted: manual inclusion with a required reason, possibly bypassing gates or exceeding K.
- Not shortlisted: explicit exclusion with a required reason.
- Needs review: explicit hold, not on the final review shortlist, with a required reason.

Every record keeps its original suggestion, final membership, source and reason. Manual exclusions/holds do not auto-fill freed slots with K+1 candidates: the model suggestion and human action remain distinct. Increase K or record another explicit inclusion if necessary.

Changing job criteria recalculates scores and automatic suggestions, retains saved human decisions, and warns that they must be reviewed against the new criteria. Importing a different dataset resets decisions so notes cannot accidentally transfer to a different applicant with a reused identifier. Ordinary navigation preserves the current saved workspace.

## 7. Invalid input versus incomplete evidence

Missing experience is an accepted unknown; a supplied negative, nonnumeric, infinite or >80 experience value is invalid and reported. Missing education is accepted unknown; a supplied nontext value is invalid. Blank email is allowed; a supplied malformed email is reported for correction. All occurrences in a duplicate candidate/application-ID group are rejected. Names alone are never deduplication criteria.

Invalid records are retained in reports with source rows and explanations. Unscored valid records are retained in the candidate table. These are deliberately different categories.

## 8. Reports and classroom use

Standard analytics omit email and arbitrary source fields. The correction download can contain supplied known fields that need repair. Exported notes are intentional report content; do not put credentials or irrelevant sensitive information into notes. Formula-leading string cells are escaped only at export time, never by changing a score or ranking.

Use the provided synthetic data for faculty demonstrations. There is no production authentication, persistent audit log, legal certification or automated hiring capability.
