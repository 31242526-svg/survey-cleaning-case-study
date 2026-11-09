"""Command line entry point: read, clean, write, report."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from survey_clean.io import HEADER_ROWS, read_qualtrics_csv
from survey_clean.pipeline import build_clean_frame, select_analysis_sample
from survey_clean.report import ReportContext, write_reports

DOI = "10.5281/zenodo.4408243"
LICENCE = "CC BY 4.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        path,
        index=False,
        na_rep="",
        lineterminator="\n",
        encoding="utf-8",
    )


def write_variable_map(labels: dict[str, str], path: Path) -> None:
    from survey_clean.pipeline import VARIABLES

    rows = [
        {
            "variable": variable.name,
            "source": variable.source,
            "source_label": labels.get(variable.source, "derived in this pipeline"),
            "type": variable.dtype,
            "description": variable.description,
            "values": variable.values,
            "transformation": variable.transformation,
        }
        for variable in VARIABLES
    ]
    write_csv(pd.DataFrame(rows), path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/raw/Wong_Carr_Wildfire_Dataset.csv"),
        help="Qualtrics CSV export as published",
    )
    parser.add_argument("--clean-dir", type=Path, default=Path("data/clean"))
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--reports-dir", type=Path, default=Path("reports"))
    args = parser.parse_args(argv)

    if not args.raw.exists():
        parser.error(f"raw file not found: {args.raw} (run scripts/fetch_data.py)")

    export = read_qualtrics_csv(args.raw)
    clean = build_clean_frame(export.data)
    sample = select_analysis_sample(clean)

    clean_path = args.clean_dir / "carr_wildfire_2018_clean.csv"
    sample_path = args.clean_dir / "carr_wildfire_2018_analysis.csv"
    write_csv(clean, clean_path)
    write_csv(sample, sample_path)
    write_variable_map(export.labels, args.docs_dir / "variable-map.csv")

    context = ReportContext(
        raw=export.data,
        clean=clean,
        labels=export.labels,
        source_path=args.raw,
        source_doi=DOI,
        source_licence=LICENCE,
        source_sha256=sha256(args.raw),
        header_rows=HEADER_ROWS,
    )
    report_path, dictionary_path = write_reports(context, args.reports_dir)

    print(f"raw        {export.shape[0]:>4} responses x {export.shape[1]:>3} columns")
    print(f"clean      {len(clean):>4} rows x {clean.shape[1]:>3} columns -> {clean_path}")
    print(f"analysis   {len(sample):>4} rows -> {sample_path}")
    print(
        f"flags      {int(clean['flag_incomplete'].sum())} incomplete, "
        f"{int(clean['flag_speeder'].sum())} speeders, "
        f"{int(clean['flag_long_session'].sum())} long sessions, "
        f"{int(clean['flag_straightline'].sum())} straight-lined, "
        f"{int(clean['flag_possible_duplicate'].sum())} duplicates"
    )
    print(f"reports    {report_path}")
    print(f"           {dictionary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
