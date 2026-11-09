from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from survey_clean.io import read_qualtrics_csv
from survey_clean.pipeline import (
    VARIABLE_NAMES,
    build_clean_frame,
    select_analysis_sample,
)


@pytest.fixture
def clean(mini_export: Path) -> pd.DataFrame:
    return build_clean_frame(read_qualtrics_csv(mini_export).data)


def test_builds_exactly_the_documented_columns(clean: pd.DataFrame) -> None:
    assert list(clean.columns) == list(VARIABLE_NAMES)
    assert len(clean) == 6


def test_system_columns_are_parsed(clean: pd.DataFrame) -> None:
    assert clean.loc[0, "response_id"] == "R_1"
    assert clean.loc[0, "started_at"] == "2019-03-12 10:01"
    assert clean.loc[0, "duration_seconds"] == 1500
    assert clean.loc[0, "finished"] is True or clean.loc[0, "finished"] == True  # noqa: E712


def test_top_codes_and_ordinals_are_numeric(clean: pd.DataFrame) -> None:
    assert clean.loc[0, "vehicles"] == 6
    assert clean.loc[0, "prior_evacuations"] == 6
    assert clean.loc[2, "household_size"] == 10
    assert clean.loc[0, "compassion_1"] == 5
    assert clean.loc[4, "compassion_5"] == 1


def test_locations_are_standardised(clean: pd.DataFrame) -> None:
    assert clean["state"].tolist() == ["CA"] * 6
    assert clean.loc[0, "county"] == "Shasta"
    assert clean.loc[0, "city"] == "Shasta Lake"
    assert clean.loc[4, "city"] == "Shasta Lake"


def test_prefer_not_to_answer_is_missing_not_a_level(clean: pd.DataFrame) -> None:
    assert pd.isna(clean.loc[1, "income_band"])
    assert clean.loc[0, ["race_asian", "race_black"]].tolist() == [0, 0]
    assert clean.loc[2, ["race_asian", "race_white"]].isna().all()


def test_race_multiselect_is_expanded(clean: pd.DataFrame) -> None:
    assert clean.loc[0, "race_white"] == 1
    assert clean.loc[0, "race_asian"] == 0
    assert clean.loc[1, "race_white"] == 1
    assert clean.loc[1, "race_asian"] == 1


def test_insurance_question_is_split_into_two_constructs(clean: pd.DataFrame) -> None:
    assert clean.loc[5, "already_insured"] == True  # noqa: E712
    assert pd.isna(clean.loc[5, "insurance_intent"])
    assert clean.loc[0, "already_insured"] == False  # noqa: E712
    assert clean.loc[0, "insurance_intent"] == "Somewhat likely"


def test_quality_flags(clean: pd.DataFrame) -> None:
    assert clean.loc[1, "flag_speeder"] == True  # noqa: E712
    assert clean.loc[2, "flag_long_session"] == True  # noqa: E712
    assert clean.loc[3, "flag_incomplete"] == True  # noqa: E712
    assert clean.loc[0, "flag_straightline"] == True  # noqa: E712
    assert clean.loc[4, "flag_straightline"] == False  # noqa: E712


def test_duplicate_flag_needs_identical_answers_not_just_a_similar_profile(
    clean: pd.DataFrame,
) -> None:
    # R_5 shares age, gender, county, city, household size and ownership with
    # R_1 but answers the compassion items differently: not a duplicate.
    assert clean["flag_possible_duplicate"].tolist() == [False] * 6


def test_analysis_ready_applies_the_documented_filter(clean: pd.DataFrame) -> None:
    assert clean["analysis_ready"].tolist() == [True, False, False, False, True, True]
    sample = select_analysis_sample(clean)
    assert len(sample) == 3
    assert sample["response_id"].tolist() == ["R_1", "R_5", "R_6"]


def test_no_free_text_columns_are_carried_into_the_clean_frame(clean: pd.DataFrame) -> None:
    assert not any(name.endswith("_text") for name in clean.columns)
