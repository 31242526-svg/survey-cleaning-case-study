from __future__ import annotations

import pandas as pd

from survey_clean.quality import (
    flag_exact_duplicates,
    flag_incomplete,
    flag_long_session,
    flag_speeder,
    flag_straightline,
)


def test_flag_incomplete_requires_finished_and_full_progress() -> None:
    finished = pd.Series([True, True, False, pd.NA], dtype="boolean")
    progress = pd.Series([100, 80, 100, 100], dtype="Int64")
    result = flag_incomplete(finished, progress)
    assert result.tolist() == [False, True, True, True]


def test_speeder_and_long_session_are_separate_flags() -> None:
    duration = pd.Series([120, 1500, 30000, pd.NA], dtype="Int64")
    assert flag_speeder(duration).tolist() == [True, False, False, False]
    assert flag_long_session(duration).tolist() == [False, False, True, False]


def test_a_missing_duration_is_not_flagged_as_a_speeder() -> None:
    assert flag_speeder(pd.Series([pd.NA], dtype="Int64")).tolist() == [False]


def test_flag_straightline_needs_enough_answered_items() -> None:
    battery = pd.DataFrame(
        {
            "a": pd.Series([3, 1, 5, pd.NA], dtype="Int64"),
            "b": pd.Series([3, 2, 5, pd.NA], dtype="Int64"),
            "c": pd.Series([3, 3, pd.NA, pd.NA], dtype="Int64"),
            "d": pd.Series([3, 4, pd.NA, pd.NA], dtype="Int64"),
            "e": pd.Series([3, 5, pd.NA, pd.NA], dtype="Int64"),
        }
    )
    result = flag_straightline(battery, min_items=4)
    assert result.tolist() == [True, False, False, False]


def test_flag_exact_duplicates_ignores_identifier_and_timing_columns() -> None:
    frame = pd.DataFrame(
        {
            "response_id": ["R_1", "R_2", "R_3"],
            "duration_seconds": [1500, 1500, 900],
            "age": pd.Series(["45 - 54", "45 - 54", "45 - 54"], dtype="string"),
            "county": pd.Series(["Shasta", "Shasta", "Shasta"], dtype="string"),
        }
    )
    result = flag_exact_duplicates(frame, ["response_id", "duration_seconds"])
    assert result.tolist() == [False, True, True]
