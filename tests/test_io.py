from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd
import pytest

from conftest import ROWS, SOURCES
from survey_clean.io import read_qualtrics_csv


def test_separates_header_rows_from_responses(mini_export: Path) -> None:
    export = read_qualtrics_csv(mini_export)
    assert export.shape == (len(ROWS), len(SOURCES))
    assert export.variable_names == SOURCES
    assert export.labels["Q32.2"] == "What is your age?"
    assert export.import_ids["Q32.4"] == "Q32.4"


def test_no_header_row_survives(mini_export: Path) -> None:
    export = read_qualtrics_csv(mini_export)
    assert list(export.data["ResponseId"]) == [f"R_{index}" for index in range(1, 7)]
    assert "Response ID" not in set(export.data["ResponseId"])


def test_blank_cells_become_missing(mini_export: Path) -> None:
    export = read_qualtrics_csv(mini_export)
    assert pd.isna(export.data.loc[3, "Q32.2"])
    assert export.data.loc[0, "Q32.2"] == "45 - 54"


def test_keeps_question_text_with_line_breaks_on_one_line(mini_export: Path) -> None:
    export = read_qualtrics_csv(mini_export)
    for label in export.labels.values():
        assert "\n" not in label


def _manual_export(path: Path, names: list[str], third_row: list[str]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(names)
        writer.writerow(names)
        writer.writerow(third_row)
        writer.writerow(["x"] * len(names))
    return path


def test_rejects_duplicate_variable_names(tmp_path: Path) -> None:
    path = _manual_export(
        tmp_path / "dupe.csv",
        ["A", "A"],
        [json.dumps({"ImportId": "A"}), json.dumps({"ImportId": "A"})],
    )
    with pytest.raises(ValueError, match="repeats variable names"):
        read_qualtrics_csv(path)


def test_rejects_a_file_without_import_ids(tmp_path: Path) -> None:
    path = _manual_export(tmp_path / "plain.csv", ["A", "B", "C"], ["a", "b", "c"])
    with pytest.raises(ValueError, match="import-ID"):
        read_qualtrics_csv(path)


def test_rejects_a_file_too_short_to_hold_headers(tmp_path: Path) -> None:
    path = tmp_path / "short.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="too few"):
        read_qualtrics_csv(path)
