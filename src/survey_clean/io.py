"""Read a Qualtrics CSV export the way it was published, header rows included.

Qualtrics writes three header rows before the first respondent:

1. the short variable names used in the export (``Q32.2``);
2. the full question text;
3. an ``ImportId`` JSON object per column.

Reading such a file with the default settings silently turns rows 2 and 3 into
respondents. This module splits the header off and returns the labels, so the
rest of the pipeline works on a frame of real responses only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HEADER_ROWS = 3

SYSTEM_COLUMNS: tuple[str, ...] = (
    "StartDate",
    "EndDate",
    "Progress",
    "Duration (in seconds)",
    "Finished",
    "RecordedDate",
    "ResponseId",
    "DistributionChannel",
    "UserLanguage",
)


@dataclass(frozen=True)
class QualtricsExport:
    """A parsed export: responses, question labels and import identifiers."""

    data: pd.DataFrame
    labels: dict[str, str]
    import_ids: dict[str, str]
    variable_names: tuple[str, ...]

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def duplicate_variable_names(self) -> list[str]:
        seen: set[str] = set()
        duplicates: list[str] = []
        for name in self.variable_names:
            if name in seen and name not in duplicates:
                duplicates.append(name)
            seen.add(name)
        return duplicates


def _clean_label(value: str) -> str:
    return " ".join(str(value).replace("\xa0", " ").split())


def read_qualtrics_csv(path: str | Path) -> QualtricsExport:
    """Read a Qualtrics export and separate its three header rows from the data."""
    path = Path(path)
    frame = pd.read_csv(
        path,
        header=None,
        dtype=str,
        keep_default_na=False,
        na_values=[],
        low_memory=False,
    )

    if len(frame) <= HEADER_ROWS:
        raise ValueError(f"{path} has {len(frame)} rows, too few for a Qualtrics export")
    if frame.shape[1] == 0:
        raise ValueError(f"{path} has no columns")

    variables = [str(value).strip() for value in frame.iloc[0].tolist()]
    labels = [_clean_label(value) for value in frame.iloc[1].tolist()]
    import_cells = frame.iloc[2].tolist()

    if len(set(variables)) != len(variables):
        duplicates = sorted({name for name in variables if variables.count(name) > 1})
        raise ValueError(f"{path} repeats variable names: {', '.join(duplicates[:5])}")

    import_ids: dict[str, str] = {}
    parsed = 0
    for variable, cell in zip(variables, import_cells, strict=True):
        try:
            payload = json.loads(cell)
        except (json.JSONDecodeError, TypeError):
            payload = None
        if isinstance(payload, dict) and "ImportId" in payload:
            import_ids[variable] = str(payload["ImportId"])
            parsed += 1
        else:
            import_ids[variable] = ""

    if parsed < max(1, len(variables) // 2):
        raise ValueError(
            f"{path}: row 3 does not look like a Qualtrics import-ID row "
            f"({parsed} of {len(variables)} cells parsed)"
        )

    data = frame.iloc[HEADER_ROWS:].copy()
    data.columns = variables
    data = data.reset_index(drop=True)
    data = data.astype("string")

    blank = data.apply(lambda column: column.str.strip().eq(""))
    data = data.mask(blank)

    return QualtricsExport(
        data=data,
        labels=dict(zip(variables, labels, strict=True)),
        import_ids=import_ids,
        variable_names=tuple(variables),
    )
