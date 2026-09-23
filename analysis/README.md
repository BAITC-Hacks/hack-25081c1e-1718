# Public-data candidate model, v1

This is a hypothesis generator for the synthetic hackathon data, not a fitted
causal response model or a forecast of the judging effects. Owner: Azim.

## Reproduce

```powershell
python -X utf8 analysis/audit_public_data.py
python -X utf8 -m unittest discover -s analysis -v
python -X utf8 scripts/run_agent.py --offline
```

The audit reads only the issued customer/profile and historical CSVs. The runtime
model reads only `data/change_tariff.csv` plus its two DataFrame arguments. It
does not import an environment, use customer IDs, write files, select channels,
or conduct pilots. Tests use temporary synthetic histories and the public CSVs.

## Evidence at checkpoint a78ed41

| Observation | Consequence |
|---|---|
| 14,823 transitions; 6 exact duplicate records; 1,407 nonpositive pre-ARPU values | Deduplicate records and exclude invalid denominators; 13,410 usable observations |
| Target/history ID overlap is zero in each of the three historical files | Transfer aggregate hypotheses only; never join target and history |
| Median target ARPU_3m = 5,930; historical pre-ARPU = 3,163 | Strong population shift; an overall historical average is inappropriate |
| Historical raw ratio mean = 450.57, median = 0.0135 | Near-zero denominators dominate the mean; bound individual ratios and use a median |
| Raw median ratio LOW +154.1%, MID +14.8%, HIGH −12.4% | Condition on pre-ARPU band; LOW gets a zero relative prior |
| 456 pair/band groups; median support 12, only 170 with n≥20 | Strong shrinkage; do not pretend narrow data/call groups have independent history |
| Only 9 of 21 tariffs occur as historical destinations | Include catalog hypotheses with no historical support and zero prior |
| LTE exceeds DATA_VOLUME in 13,337 target rows (56.9% of all rows) | Use DATA_VOLUME and issued segments; never add LTE to total traffic |
| arpu_monthly has 701 rows in repeated ID/month groups | Do not reconstruct outcomes from this ambiguous table; use the supplied pre/post fields |

Examples justify exploration, not final campaigns: MID 4→8 (n408, median +29.2%),
MID 8→10 (n182, +31.8%), MID 13→8 (n234, +40.5%), HIGH 11→12 (n107, +12.1%).
HIGH 8→10 is nearly flat (n283, +0.14%). A pair's overall association must not be
substituted for the association in the target ARPU band. These examples are
documentary; tariff numbers and these values are not hardcoded in the model.

## Implemented choices

1. Group the target by its available current/arpu/data/call columns. Keep only
   recognized, complete, filter-expressible cells with 10–5,000 rows and positive
   total predicted ARPU. Never trim a group to pretend its filter is smaller.
   On the issued input, 160 eligible cells cover 22,660 subscribers.
2. Select at most two different targets per cell: a moderate price/package
   hypothesis and a supported same-band historical alternative or another
   package fit. Use actual tariff prices and packages, median data and off-net
   plus landline minutes; tariff numeric suffixes carry no price meaning.
   Prices up to 1.5×max(current fee, median predicted ARPU) define a soft shortlist;
   if empty, use the catalog. These are transparent heuristics, not acceptance
   predictions. A cheaper offer explicitly carries downsell risk. Equivalent
   price/package offers do not justify an extra switch/alternative without
   distinct positive same-band historical evidence.
3. For each `(from, to, historical pre-ARPU band)` compute the median and mean of
   ratios bounded to [-1, 1]. The prior is
   `0.1 * n/(n+50) * clip(median, -0.25, 0.25)`. Set it to zero for LOW, n<10,
   missing history, or inconsistent median/mean signs. The 90% transfer discount
   and shrinkage towards zero express caution, not a calibrated confidence level.
   Absolute prior is at most 2.5%, before channel scaling.
4. `prior_n` retains the true cleaned group count. Several target data/call cells
   may share this source evidence; their counts must not be added as independent
   observations. The core limits prior influence to five pseudo-observations;
   real pilot outcomes control campaign decisions.
5. Return a bounded deterministic pool, preserving one target per segment before
   second alternatives. Stable IDs match the shared filter/target hash convention.
   Empty input returns `[]`; unusable history yields neutral catalog hypotheses.

No heuristic was selected by inspecting hidden effects or optimizing mock seeds.
The core currently reorders candidates by revenue and positive prior, so the
module's returned ordering is not the eventual pilot ordering. Allocation,
confirmation, stop conditions and final resource checks are implemented in agent.py.

## Verification and limitations

Contract tests cover exact filter counts and sums, input immutability, stable
identifiers under row shuffling, changed customer IDs, missing/malformed history,
duplicate history, nonexpressible large cells and sparse/unknown inputs. Missing
filter values are excluded transparently; this model does not cover all 23,441
subscribers. Package fit is observational, and the supplied total minutes do not
constitute a tariff billing simulation. No claim of economic improvement follows
from passing these tests; official run results are recorded in [VALIDATION](../docs/VALIDATION.md).
