"""Response-quality flags.

These functions flag rows; they never drop them. A researcher can then decide
which flags matter for a given analysis, and the decision stays visible in the
output rather than disappearing inside a script.
"""

from __future__ import annotations

import pandas as pd

#: The questionnaire says the survey takes about 25 minutes. A respondent who
#: finished in under 5 minutes answered 20% of that time, which is not enough to
#: read 300 questions, so the row is flagged as a speeder.
SPEEDER_THRESHOLD_SECONDS = 300

#: A browser left open overnight inflates duration. Six hours is far beyond a
#: plausible 25-minute session and marks a likely paused or abandoned tab.
LONG_SESSION_SECONDS = 6 * 60 * 60


def flag_incomplete(finished: pd.Series, progress: pd.Series) -> pd.Series:
    """True unless the response is marked finished and reached 100% progress."""
    complete = finished.fillna(False) & (progress.fillna(0) >= 100)
    return (~complete).astype("boolean")


def flag_speeder(duration_seconds: pd.Series, threshold: int = SPEEDER_THRESHOLD_SECONDS):
    """True when a response was submitted faster than ``threshold`` seconds."""
    return (duration_seconds < threshold).fillna(False).astype("boolean")


def flag_long_session(duration_seconds: pd.Series, threshold: int = LONG_SESSION_SECONDS):
    """True when a response took longer than ``threshold`` seconds."""
    return (duration_seconds > threshold).fillna(False).astype("boolean")


def flag_straightline(battery: pd.DataFrame, min_items: int = 4) -> pd.Series:
    """True when a respondent gave the same answer to every item in a battery.

    Only rows that answered at least ``min_items`` of the battery are considered,
    so a half-empty battery is not mistaken for straight-lining.
    """
    answered = battery.notna().sum(axis=1)
    distinct = battery.nunique(axis=1, dropna=True)
    return ((answered >= min_items) & (distinct <= 1)).astype("boolean")


def flag_exact_duplicates(frame: pd.DataFrame, ignore: list[str]) -> pd.Series:
    """Flag rows whose answers repeat an earlier row exactly.

    Identifier and timing columns must be passed in ``ignore``: a household that
    submits the survey twice shares every answer but never a timestamp.
    """
    answers = frame.drop(columns=[column for column in ignore if column in frame.columns])
    return answers.duplicated(keep="first").astype("boolean")
