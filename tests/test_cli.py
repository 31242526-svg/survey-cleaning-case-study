from __future__ import annotations

from pathlib import Path

import pandas as pd

from survey_clean.cli import main
from survey_clean.pipeline import VARIABLES


def run(raw: Path, out: Path) -> int:
    return main(
        [
            "--raw",
            str(raw),
            "--clean-dir",
            str(out / "data"),
            "--docs-dir",
            str(out / "docs"),
            "--reports-dir",
            str(out / "reports"),
        ]
    )


def test_cli_writes_every_output(mini_export: Path, tmp_path: Path) -> None:
    assert run(mini_export, tmp_path) == 0

    assert (tmp_path / "data" / "carr_wildfire_2018_clean.csv").exists()
    assert (tmp_path / "data" / "carr_wildfire_2018_analysis.csv").exists()
    assert (tmp_path / "docs" / "variable-map.csv").exists()
    assert (tmp_path / "reports" / "cleaning-report.md").exists()
    assert (tmp_path / "reports" / "data-dictionary.md").exists()


def test_clean_csv_round_trips_with_named_columns(mini_export: Path, tmp_path: Path) -> None:
    run(mini_export, tmp_path)
    frame = pd.read_csv(
        tmp_path / "data" / "carr_wildfire_2018_clean.csv",
        dtype=str,
        keep_default_na=False,
    )
    assert list(frame.columns) == [variable.name for variable in VARIABLES]
    assert len(frame) == 6


def test_analysis_csv_holds_only_flagged_rows(mini_export: Path, tmp_path: Path) -> None:
    run(mini_export, tmp_path)
    frame = pd.read_csv(tmp_path / "data" / "carr_wildfire_2018_analysis.csv", dtype=str)
    assert len(frame) == 3
    assert frame["response_id"].tolist() == ["R_1", "R_5", "R_6"]


def test_reports_cover_the_decisions(mini_export: Path, tmp_path: Path) -> None:
    run(mini_export, tmp_path)
    report = (tmp_path / "reports" / "cleaning-report.md").read_text(encoding="utf-8")
    dictionary = (tmp_path / "reports" / "data-dictionary.md").read_text(encoding="utf-8")
    assert "# Cleaning report" in report
    assert "Header repair" in report
    assert "Decisions to confirm with the data owner" in report
    assert "# Data dictionary" in dictionary
    for variable in VARIABLES:
        assert f"`{variable.name}`" in dictionary


def test_variable_map_documents_every_column(mini_export: Path, tmp_path: Path) -> None:
    run(mini_export, tmp_path)
    mapping = pd.read_csv(tmp_path / "docs" / "variable-map.csv", dtype=str)
    assert list(mapping.columns) == [
        "variable",
        "source",
        "source_label",
        "type",
        "description",
        "values",
        "transformation",
    ]
    assert len(mapping) == len(VARIABLES)
    assert mapping["variable"].tolist() == [variable.name for variable in VARIABLES]


def test_two_runs_produce_identical_files(mini_export: Path, tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    run(mini_export, first)
    run(mini_export, second)

    for relative in (
        "data/carr_wildfire_2018_clean.csv",
        "data/carr_wildfire_2018_analysis.csv",
        "docs/variable-map.csv",
        "reports/cleaning-report.md",
        "reports/data-dictionary.md",
    ):
        assert (first / relative).read_bytes() == (second / relative).read_bytes()
