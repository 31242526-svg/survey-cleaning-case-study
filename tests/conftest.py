"""A tiny Qualtrics export with the same three header rows as the real file."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

SOURCES: tuple[str, ...] = (
    "StartDate",
    "EndDate",
    "Progress",
    "Duration (in seconds)",
    "Finished",
    "RecordedDate",
    "ResponseId",
    "DistributionChannel",
    "UserLanguage",
    "Q9.1",
    "Q32.2",
    "Q32.3",
    "Q32.4",
    "Q32.5",
    "Q32.6",
    "Q32.7",
    "Q32.8_1",
    "Q32.8_2",
    "Q32.8_3",
    "Q32.8_4",
    "Q32.8_5",
    "Q32.11",
    "Q32.13",
    "Q33.1",
    "Q33.2",
    "Q33.3",
    "Q33.6",
    "Q33.7",
    "Q33.9",
    "Q33.10",
    "Q34.1_1",
    "Q34.1_2",
    "Q34.1_3",
    "Q34.2",
    "Q34.3",
    "Q35.2",
    "Q35.4",
    "Q35.6_1",
    "Q35.6_2",
    "Q35.6_3",
    "Q35.6_4",
    "Q35.6_5",
    "Q35.7",
    "Q35.9",
    "Q35.10",
    "Q35.11",
    "Q35.12",
    "Q35.13",
)

DEFAULTS: dict[str, str] = {
    "StartDate": "3/12/2019 10:01",
    "EndDate": "3/12/2019 10:26",
    "Progress": "100",
    "Duration (in seconds)": "1500",
    "Finished": "TRUE",
    "RecordedDate": "3/12/2019 10:26",
    "DistributionChannel": "anonymous",
    "UserLanguage": "EN",
    "Q9.1": "Yes",
    "Q32.2": "45 - 54",
    "Q32.3": "Female",
    "Q32.4": "White",
    "Q32.5": "Not Hispanic or Latino or Spanish Origin",
    "Q32.6": "4 year degree (bachelor's)",
    "Q32.7": "Employed full time",
    "Q32.8_1": "2",
    "Q32.8_2": "1",
    "Q32.8_3": "0",
    "Q32.8_4": "0",
    "Q32.8_5": "0",
    "Q32.11": "2",
    "Q32.13": "$50,000 - $74,999",
    "Q33.1": "California",
    "Q33.2": "Shasta",
    "Q33.3": "Redding",
    "Q33.6": "Yes",
    "Q33.7": "More than 10 years",
    "Q33.9": "Site build (single home)",
    "Q33.10": "Yes",
    "Q34.1_1": "0",
    "Q34.1_2": "1",
    "Q34.1_3": "2",
    "Q34.2": "1",
    "Q34.3": "Somewhat likely",
    "Q35.2": "Yes",
    "Q35.4": "It is possible to trust most people.",
    "Q35.6_1": "5 (very true)",
    "Q35.6_2": "4",
    "Q35.6_3": "3",
    "Q35.6_4": "2",
    "Q35.6_5": "1 (not at all true)",
    "Q35.7": "No",
    "Q35.9": "No",
    "Q35.10": "Yes, offered but did not provide",
    "Q35.11": "Yes, provided",
    "Q35.12": "No",
    "Q35.13": "No",
}


def make_row(response_id: str, **overrides: str) -> dict[str, str]:
    row = dict(DEFAULTS)
    row["ResponseId"] = response_id
    row.update(overrides)
    return row


ROWS: list[dict[str, str]] = [
    # 1. Complete and usable; straight-lines the compassion battery.
    make_row(
        "R_1",
        **{
            "Q32.4": "White",
            "Q33.1": "California ",
            "Q33.2": "Shasta County",
            "Q33.3": "City of Shasta Lake",
            "Q32.11": "More than 5",
            "Q34.2": "More than 5",
            "Q35.6_1": "5 (very true)",
            "Q35.6_2": "5 (very true)",
            "Q35.6_3": "5 (very true)",
            "Q35.6_4": "5 (very true)",
            "Q35.6_5": "5 (very true)",
        },
    ),
    # 2. Speeder; two race categories; income withheld.
    make_row(
        "R_2",
        **{
            "Duration (in seconds)": "120",
            "Q32.2": "25 - 34",
            "Q32.3": "Male",
            "Q32.4": "White,Asian",
            "Q32.13": "Prefer not to answer",
        },
    ),
    # 3. Browser left open; race withheld; top-coded household size.
    make_row(
        "R_3",
        **{
            "Duration (in seconds)": "30000",
            "Q32.2": "65 - 74",
            "Q32.4": "Prefer not to answer",
            "Q32.8_1": "10 or more",
            "Q33.1": "californis",
        },
    ),
    # 4. Abandoned at 26%.
    make_row(
        "R_4",
        **{
            "Progress": "26",
            "Finished": "FALSE",
            "Duration (in seconds)": "900",
            "Q9.1": "",
            "Q32.2": "",
            "Q32.3": "",
            "Q32.4": "",
            "Q32.5": "",
            "Q32.6": "",
            "Q32.7": "",
            "Q32.13": "",
        },
    ),
    # 5. Same demographic and housing profile as R_1: duplicate flag.
    make_row(
        "R_5",
        **{
            "Q33.1": "CA",
            "Q33.3": "Shasta Lake",
            "Q32.11": "6",
        },
    ),
    # 6. Already insured; the likelihood scale does not apply.
    make_row(
        "R_6",
        **{
            "Q32.2": "85 or older",
            "Q32.3": "Other",
            "Q34.3": "I already have a type of insurance for natural disasters",
            "Q33.10": "No",
        },
    ),
]

LABELS: dict[str, str] = {
    "StartDate": "Start Date",
    "EndDate": "End Date",
    "Progress": "Progress",
    "Duration (in seconds)": "Duration (in seconds)",
    "Finished": "Finished",
    "RecordedDate": "Recorded Date",
    "ResponseId": "Response ID",
    "DistributionChannel": "Distribution Channel",
    "UserLanguage": "User Language",
    "Q9.1": "Did you evacuate from the Carr Wildfire?",
    "Q32.2": "What is your age?",
    "Q32.3": "What gender do you identify with? - Selected Choice",
    "Q32.4": "What race do you identify with? Check all that apply. - Selected Choice",
    "Q32.5": "What ethnicity do you identify with?",
    "Q32.6": "What is the highest level of education you have completed?",
    "Q32.7": "What is your current employment status?",
    "Q32.8_1": "Number of individuals in your household",
    "Q32.8_2": "Number of household members employed",
    "Q32.8_3": "Number of children under 18",
    "Q32.8_4": "Number of adults over 65",
    "Q32.8_5": "Number of household members with a disability",
    "Q32.11": "How many automobiles does your household have?",
    "Q32.13": "What was your total household income in 2018?",
    "Q33.1": "In which state do you live currently?",
    "Q33.2": "In which county do you live currently?",
    "Q33.3": "In which city do you live currently?",
    "Q33.6": "Did you live in a Very High or High fire severity zone?",
    "Q33.7": "How long did you live in your residence?",
    "Q33.9": "What type of building was your residence?",
    "Q33.10": "Did you own your residence?",
    "Q34.1_1": "Disasters experienced - Earthquake",
    "Q34.1_2": "Disasters experienced - Flood",
    "Q34.1_3": "Disasters experienced - Wildfire",
    "Q34.2": "Evacuations before this disaster",
    "Q34.3": "How likely are you to buy natural-disaster insurance?",
    "Q35.2": "Are you part of a community organisation?",
    "Q35.4": "Can most people be trusted?",
    "Q35.6_1": "Compassion item 1",
    "Q35.6_2": "Compassion item 2",
    "Q35.6_3": "Compassion item 3",
    "Q35.6_4": "Compassion item 4",
    "Q35.6_5": "Compassion item 5",
    "Q35.7": "Did you volunteer during the relief efforts?",
    "Q35.9": "Offered transport before evacuating",
    "Q35.10": "Offered transport during the evacuation",
    "Q35.11": "Offered transport after the evacuation",
    "Q35.12": "Offered shelter for a fee",
    "Q35.13": "Offered shelter for free",
}


def write_export(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(SOURCES)
        writer.writerow([LABELS.get(source, source) for source in SOURCES])
        writer.writerow([json.dumps({"ImportId": source}) for source in SOURCES])
        for row in rows:
            writer.writerow([row.get(source, "") for source in SOURCES])
    return path


@pytest.fixture
def mini_export(tmp_path: Path) -> Path:
    return write_export(tmp_path / "mini.csv", ROWS)
