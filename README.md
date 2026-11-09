# Survey data cleaning: 2018 Carr Wildfire Evacuation Survey

[![CI](https://github.com/31242526-svg/survey-cleaning-case-study/actions/workflows/ci.yml/badge.svg)](https://github.com/31242526-svg/survey-cleaning-case-study/actions/workflows/ci.yml)

A public Qualtrics export, cleaned by code rather than by hand. The repository
starts from the file exactly as the authors published it — three header rows,
500 columns, free-text places, open-ended top codes — and ends with a documented
table a researcher can open and use.

This is a working case study, not a tutorial: every decision is written down,
the outputs are committed, and CI re-runs the pipeline to prove they still match.

## The short version

| | |
| --- | --- |
| Raw export | 647 responses × 500 columns, 650 lines |
| Curated columns | 57, defined once in `src/survey_clean/pipeline.py` |
| Analysis-ready rows | 273 |
| Tests | 41 |
| Licence | Code MIT, data CC BY 4.0 |

The export is not a table. Its first three rows are variable names, question
text and JSON import IDs; reading it with default settings turns two of them
into respondents. After the header is removed, the pipeline repairs the values
that would otherwise distort an analysis:

- **Missing codes.** `Prefer not to answer` becomes null in every curated column
  (132 cells). `I don't know` is kept, because it answers a factual question.
- **Open-ended top codes.** `More than 5` becomes 6 and `10 or more` becomes 10 —
  the smallest value the band can represent, never a guessed midpoint.
- **Labels in values.** The compassion battery stores anchors such as
  `5 (very true)`. They are stripped to integers 1–5.
- **Multi-select answers.** Race is a comma-separated `check all that apply`
  field, expanded into six 0/1 indicators. A skipped question stays missing in
  all six rather than becoming "no race selected".
- **Typed place names.** 25 state spellings become 8 codes; four values that no
  rule maps (a bare number, `Califirnia`, `shasta`, `United States`) stay missing
  and are listed for the owner.
- **One question, two constructs.** The insurance item mixes "I already have
  insurance" with a likelihood scale, so it is split into `already_insured` and
  `insurance_intent`.
- **Response quality.** Incomplete responses, speeders, six-hour sessions,
  straight-lined batteries and exact duplicates are flagged, never silently
  deleted: 312, 69, 40, 68 and 2 rows respectively.
- **Narrative withheld.** 14 free-text columns are excluded from the clean files
  because they contain names, streets and employers. The raw file is public; a
  tidy file that joins those comments to a household's demographics is a
  re-identification risk this pipeline will not take.

The full reasoning, with counts generated from the data, is in
[`reports/cleaning-report.md`](reports/cleaning-report.md). Every column is
described in [`reports/data-dictionary.md`](reports/data-dictionary.md).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

survey-clean
```

Or without installing the entry point:

```bash
PYTHONPATH=src python -m survey_clean.cli
```

The raw files are committed, so no download is needed. To fetch them again from
Zenodo and verify their checksums:

```bash
python scripts/fetch_data.py --force
```

### Outputs

| Path | Contents |
| --- | --- |
| `data/clean/carr_wildfire_2018_clean.csv` | All 647 responses, 57 curated columns, quality flags |
| `data/clean/carr_wildfire_2018_analysis.csv` | The 273 rows where `analysis_ready` is true |
| `docs/variable-map.csv` | One row per column: source, type, values, transformation |
| `reports/cleaning-report.md` | What arrived, what changed, what was left alone |
| `reports/data-dictionary.md` | Column-level documentation |

Missing values are written as empty fields, never as `0`, `NA` or a label.
Integers are nullable: a blank means unanswered, not zero.

## The rules the code follows

1. **Deterministic only.** No fuzzy matching, no LLM calls, no "probably the
   same" merges. A wrong merge of two places is worse than a visible duplicate.
2. **Flags are not deletions.** Every quality judgement is a column the analyst
   can accept or override. The clean file keeps all 647 responses.
3. **One source of truth.** `VARIABLES` in `pipeline.py` defines the output
   columns; the CSV, variable map, data dictionary and tests are generated from
   it and fail if they drift.
4. **No numbers typed by hand.** The report is rendered from the raw export and
   the cleaned frame at run time. Re-running the pipeline reproduces every
   count, and CI asserts the committed files do not change.
5. **Unmapped values stay visible.** Unknown states, out-of-range numbers and
   ambiguous free text become missing and are reported, not guessed.

## Repository map

```text
src/survey_clean/
  io.py         three-row Qualtrics header, duplicate-name and import-ID checks
  recode.py     text, integer, ordinal, boolean, datetime, multi-select, places
  quality.py    incomplete, speeder, long-session, straight-line, duplicate flags
  pipeline.py   the 57-column VARIABLES spec and the sample filter
  report.py     generated cleaning report and data dictionary
  cli.py        read -> clean -> write -> report
tests/          41 tests: io, recode, quality, pipeline, CLI, reproducibility
scripts/        fetch_data.py: re-download the archive and verify checksums
data/           raw export and PDF as published; cleaned and analysis CSVs
reports/        generated Markdown
docs/           generated variable map
```

## Reproducibility

- The raw CSV is checked against the MD5 published on Zenodo
  (`32e450c6c021d023b0d5c9bbc0cea94b`) and recorded by SHA-256 in the report.
- Outputs are deterministic: no timestamps, `\n` line endings, stable column
  order.
- CI runs lint and tests on Python 3.10, 3.12 and 3.13, then re-runs the
  pipeline on the committed raw file and fails if any committed output changes.

## Data and licence

The survey data belongs to Stephen D. Wong, Joan L. Walker and Susan A. Shaheen
(UC Berkeley), published on Zenodo under CC BY 4.0:
[10.5281/zenodo.4408243](https://doi.org/10.5281/zenodo.4408243).

The cleaning code is MIT licensed. The cleaned files are derivative works and
remain CC BY 4.0. Attribution and the exact files redistributed are listed in
[`NOTICE`](NOTICE). No free-text answers are redistributed.

The archive asks users to send a courtesy email to the lead author and to cite
the related papers before reusing the data; see the
[Zenodo record](https://doi.org/10.5281/zenodo.4408243) for that list.

## Citation

If you use the cleaned files, cite the dataset (see `CITATION.cff`) and note
that they were produced by this pipeline.
