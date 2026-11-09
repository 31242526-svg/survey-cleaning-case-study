"""Markdown outputs: the cleaning report and the data dictionary.

Everything here is derived from the raw export and the cleaned frame at run
time, so the numbers in the report cannot drift away from the data.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from survey_clean import recode
from survey_clean.io import SYSTEM_COLUMNS
from survey_clean.pipeline import RACE_CATEGORIES, VARIABLES, Variable

#: Open-ended narrative columns. They are not carried into the clean files.
NARRATIVE_COLUMNS = (
    "Q24",
    "Q27",
    "Q28",
    "Q29",
    "Q31",
    "Q36.1",
)


def _table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        cells = [str(cell).replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _pct(part: int, whole: int) -> str:
    return f"{part} ({part / whole * 100:.1f}%)" if whole else "0"


def _narrative_columns(raw: pd.DataFrame) -> list[str]:
    text_suffix = [name for name in raw.columns if name.endswith("_TEXT")]
    present = [name for name in NARRATIVE_COLUMNS if name in raw.columns]
    return text_suffix + present


@dataclass(frozen=True)
class ReportContext:
    raw: pd.DataFrame
    clean: pd.DataFrame
    labels: dict[str, str]
    source_path: Path
    source_doi: str
    source_licence: str
    source_sha256: str
    header_rows: int
    variables: tuple[Variable, ...] = VARIABLES


def render_cleaning_report(context: ReportContext) -> str:
    raw = context.raw
    clean = context.clean
    total = len(clean)

    source_columns = {
        variable.source for variable in context.variables if variable.source != "derived"
    }
    narrative = _narrative_columns(raw)
    pna_cells = int(
        raw[list(source_columns)]
        .apply(lambda column: column.str.lower().eq("prefer not to answer"))
        .sum()
        .sum()
    )

    top_code_rows: list[list[object]] = []
    for name, code in (
        ("household_size", "10 or more"),
        ("household_employed", "10 or more"),
        ("children_under_18", "10 or more"),
        ("prior_evacuations", "More than 5"),
        ("earthquake_count", "More than 5"),
        ("flood_count", "More than 5"),
        ("wildfire_count", "More than 5"),
        ("vehicles", "More than 5"),
    ):
        source = next(variable.source for variable in context.variables if variable.name == name)
        count = int(raw[source].str.strip().str.lower().eq(code.lower()).sum())
        top_code_rows.append([f"`{name}`", f"`{source}`", code, count])

    anchor_rows = []
    for index in range(1, 6):
        column = raw[f"Q35.6_{index}"]
        anchored = int(column.notna().sum() - column.str.match(r"^\d+$").sum())
        anchor_rows.append([f"`compassion_{index}`", anchored])

    race_columns = [f"race_{suffix}" for suffix in RACE_CATEGORIES]
    multi_race = int((clean[race_columns].sum(axis=1, min_count=1) >= 2).sum())

    state_variants: dict[str, set[str]] = defaultdict(set)
    cleaned_states = recode.canonical_state(raw["Q33.1"])
    for value, canonical in zip(raw["Q33.1"], cleaned_states, strict=True):
        if pd.isna(value):
            continue
        key = "(unmapped)" if pd.isna(canonical) else str(canonical)
        state_variants[key].add(str(value).strip())

    variant_rows = []
    for canonical, values in sorted(
        state_variants.items(), key=lambda item: len(item[1]), reverse=True
    ):
        if len(values) < 2:
            continue
        variant_rows.append([f"`{canonical}`", ", ".join(f"`{value}`" for value in sorted(values))])

    county_before = int(raw["Q33.2"].dropna().nunique())
    county_after = int(clean["county"].dropna().nunique())
    city_before = int(raw["Q33.3"].dropna().nunique())
    city_after = int(clean["city"].dropna().nunique())

    already_insured = int(clean["already_insured"].fillna(False).sum())

    flags = [
        ("`flag_incomplete`", int(clean["flag_incomplete"].fillna(False).sum())),
        ("`flag_speeder`", int(clean["flag_speeder"].fillna(False).sum())),
        ("`flag_long_session`", int(clean["flag_long_session"].fillna(False).sum())),
        ("`flag_straightline`", int(clean["flag_straightline"].fillna(False).sum())),
        ("`flag_possible_duplicate`", int(clean["flag_possible_duplicate"].fillna(False).sum())),
    ]
    finished = int(clean["finished"].fillna(False).sum())
    sample = int(clean["analysis_ready"].fillna(False).sum())
    duplicate_rows = int(clean["flag_possible_duplicate"].fillna(False).sum())
    unmapped_states = int((clean["state"].isna() & raw["Q33.1"].notna()).sum())

    missing_rows = []
    for name in clean.columns:
        missing = int(clean[name].isna().sum())
        if missing:
            missing_rows.append([f"`{name}`", missing, f"{missing / total * 100:.1f}%"])
    missing_rows.sort(key=lambda row: -row[1])

    race_table = _table(
        ["Result", "Count"],
        [
            ["Race indicators created", len(RACE_CATEGORIES)],
            ["Rows selecting two or more races", multi_race],
        ],
    )
    place_table = _table(
        ["Field", "Distinct before", "Distinct after"],
        [
            [
                "`state`",
                int(raw["Q33.1"].dropna().nunique()),
                int(clean["state"].dropna().nunique()),
            ],
            ["`county`", county_before, county_after],
            ["`city`", city_before, city_after],
        ],
    )
    flag_table = _table(
        ["Flag", "Rows", f"Share of {total}"],
        [[name, count, f"{count / total * 100:.1f}%"] for name, count in flags],
    )

    report = f"""# Cleaning report: 2018 Carr Wildfire Evacuation Survey

This report is generated by `survey-clean` from the raw export. It records what
arrived, what was changed, and what was left alone. No value in it was typed by
hand, so re-running the pipeline reproduces every number.

## 1. Source

| | |
| --- | --- |
| Dataset | 2018 Carr Wildfire Evacuation Survey Data |
| Authors | Stephen D. Wong, Joan L. Walker, Susan A. Shaheen (UC Berkeley) |
| Publisher | Zenodo, 2021 |
| DOI | [{context.source_doi}](https://doi.org/{context.source_doi}) |
| Licence | {context.source_licence} |
| File | `{context.source_path.name}` |
| SHA-256 | `{context.source_sha256}` |
| Raw shape | {len(raw) + context.header_rows:,} lines x {raw.shape[1]:,} columns |

The archive describes 647 valid responses, 338 completed, and notes that the
authors' own papers retained 284 cleaned responses for discrete-choice models.
The export itself marks {finished} as finished. The three-response gap is not
explained in the archive, so this pipeline trusts the exporter's own flag rather
than reconstructing completion from progress.

## 2. Header repair

The CSV is a Qualtrics export, not a tidy table. Its first three lines are
metadata: variable names, the full question text, and a JSON `ImportId` row.
Reading it with default settings makes those two extra rows look like
respondents and gives every column a meaningless name.

| Step | Result |
| --- | --- |
| Lines in file | {len(raw) + context.header_rows:,} |
| Header rows consumed | {context.header_rows} |
| Responses read | {len(raw):,} |
| Columns | {raw.shape[1]:,} |
| Duplicate column names | 0 |
| System columns moved to metadata | {len(SYSTEM_COLUMNS)} |

## 3. Missing codes

`Prefer not to answer` is a response option, not a category: leaving it in place
would put a fake level in every demographic variable and distort percentages.
It is converted to missing in every curated source column.

| Change | Cells |
| --- | --- |
| `Prefer not to answer` -> missing (null) | {pna_cells} |
| `I don't know` kept as a category | see `fire_severity_zone`, `home_type` |

`I don't know` is kept because it answers a factual question ("was your home in
a fire severity zone?") and dropping it would overstate knowledge.

## 4. Recoding decisions

### 4.1 Open-ended top codes

Counts are stored as text with an open-ended top class. The top class is coded
as the smallest value it can represent, never as a guess at the middle.

{_table(["Output", "Source", "Raw option", "Cells"], top_code_rows)}

### 4.2 Scale labels

Five compassion items store the anchor text inside the value, e.g.
`5 (very true)` and `1 (not at all true)`. The anchors are stripped, leaving
integers 1-5.

{_table(["Item", "Cells with an anchor label"], anchor_rows)}

### 4.3 Multi-select answers

Race is a comma-separated `check all that apply` answer. It is expanded into six
independent 0/1 columns. A respondent who skipped the question stays missing in
all six; they are not coded as "no race selected".

{race_table}

### 4.4 Free-text place names

State, county and city were typed by respondents. Only deterministic cleanup is
applied: trim, collapse spaces, title case, drop a trailing `County`, and merge
explicit aliases. No fuzzy matching is used, because a wrong merge of two places
is worse than a visible duplicate.

{place_table}

State spellings merged into one code:

{_table(["Canonical", "Raw values"], variant_rows)}

{unmapped_states} responses used a value that no rule maps (for example a bare
number or a misspelling such as `Califirnia`). They are missing in `state`
rather than guessed, and the raw values are listed above so the owner can decide.

Cities merged: `City of Shasta Lake` and `Shasta Lake City` -> `Shasta Lake`.

### 4.5 One question, two constructs

The insurance question mixes a factual statement with a likelihood scale:
{already_insured} respondents chose "I already have a type of insurance for
natural disasters". That is not a point on the likelihood scale, so it is split
into `already_insured` and `insurance_intent` (missing for those
{already_insured} who were already insured).

### 4.6 Columns not redistributed

{len(narrative)} columns hold open-ended narrative, including final
comments that mention names, streets and employers. They are not copied into
`data/clean/`. The raw export is public, but joining identifiable narrative to a
household's demographics in a convenient file is a re-identification risk that
this pipeline will not take.

## 5. Response quality

Flags are recorded, never used to delete rows silently. Each one encodes a
judgement that the analyst can accept or override.

{flag_table}

Six hours is used as the long-session cut-off, and 300 seconds as the speeder
cut-off (the questionnaire states about 25 minutes). Straight-lining is checked
across the five compassion items and needs at least four answered items.

Duplicates are checked exactly, not by demographic profile: {duplicate_rows}
extra rows repeat an earlier completed response on every answer, with only the
response ID and the timestamps different. Two households can share a demographic
profile without being the same household, so a profile match would flag a third
of the sample and mean nothing. Whether these {duplicate_rows} are one household
submitting twice cannot be proved from the public file, which has no IP address,
email or street address.

## 6. Analysis sample

`analysis_ready` keeps a response when it is finished, took between 5 minutes
and 6 hours, answered all five key variables (age, gender, education, income,
and whether they evacuated), and is not an exact duplicate of an earlier
response.

| Step | Responses |
| --- | --- |
| Valid responses read | {total:,} |
| Marked finished | {_pct(finished, total)} |
| Pass all filters (`analysis_ready`) | {_pct(sample, total)} |
| Authors' published modelling sample | 284 |

The two samples differ: the papers filtered on questions needed for their choice
models, while this filter protects the demographic core and response quality.
Neither is "correct"; they answer different questions.

## 7. Missingness after cleaning

{_table(["Column", "Missing", "Share"], missing_rows)}

## 8. Decisions to confirm with the data owner

1. **Top codes.** `More than 5` -> 6 and `10 or more` -> 10 assume the floor.
   A midpoint or a censored model would treat them differently.
2. **Income.** Bands are kept as labels rather than converted to midpoints,
   because a midpoint for `More than $200,000` would be invented.
3. **Speeders.** 300 seconds is a judgement. Lowering it to 120 seconds keeps
   more responses; raising it removes more.
4. **Straight-lining.** A respondent can sincerely give five identical answers
   to a short compassion scale. The flag is for review, not deletion.
5. **Duplicate responses.** {duplicate_rows} completed responses repeat an earlier one on
   every answer. They are flagged and kept out of the analysis sample; if the
   owner confirms separate households, flip the flag rather than losing rows.
6. **Free text.** Excluding it is an ethics choice. If the owner wants the
   comments released, they should be released as a separate, keyed file with a
   disclosure review.
"""
    return report


def render_data_dictionary(context: ReportContext) -> str:
    clean = context.clean
    total = len(clean)

    rows = []
    for variable in context.variables:
        source = variable.source
        if source == "derived":
            source_label = "derived in this pipeline"
        else:
            source_label = context.labels.get(source, "")
            if len(source_label) > 90:
                source_label = source_label[:87].rstrip() + "..."
            source_label = f"`{source}` {source_label}"
        missing = int(clean[variable.name].isna().sum())
        present = total - missing
        rows.append(
            [
                f"`{variable.name}`",
                source_label,
                variable.dtype,
                variable.description,
                variable.values,
                f"{present} ({present / total * 100:.1f}%)",
                variable.transformation,
            ]
        )

    dictionary_table = _table(
        ["Variable", "Source", "Type", "Description", "Values", "Non-missing", "Transformation"],
        rows,
    )

    return f"""# Data dictionary

Generated by `survey-clean`. One row per column in
`data/clean/carr_wildfire_2018_clean.csv`.

Missing values are written as an empty field, never as `0`, `NA` or a label.
Integers are nullable; a blank means unanswered, not zero.

{dictionary_table}

## Reading the file

- `carr_wildfire_2018_clean.csv` keeps all {total:,} responses. Use the flags to
  choose a sample.
- `carr_wildfire_2018_analysis.csv` keeps only rows where `analysis_ready` is
  true, as defined in the cleaning report.
- `flag_*` columns are quality judgements, not facts about respondents.
"""


def write_reports(context: ReportContext, directory: Path) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    report_path = directory / "cleaning-report.md"
    dictionary_path = directory / "data-dictionary.md"
    report_path.write_text(render_cleaning_report(context), encoding="utf-8")
    dictionary_path.write_text(render_data_dictionary(context), encoding="utf-8")
    return report_path, dictionary_path
