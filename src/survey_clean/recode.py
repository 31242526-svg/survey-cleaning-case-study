"""Small, testable recoding helpers for survey exports.

Every function is pure: it returns a new series and never mutates its input.
Values that a respondent chose not to answer become missing, never a category.
"""

from __future__ import annotations

import re

import pandas as pd

PREFER_NOT_TO_ANSWER = "prefer not to answer"

TRUE_VALUES = {"yes", "y", "true", "1"}
FALSE_VALUES = {"no", "n", "false", "0"}

US_STATES: dict[str, str] = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}

STATE_CODES = set(US_STATES.values())

# Spellings actually present in this export that no rule can infer.
STATE_ALIASES: dict[str, str] = {
    "calif": "CA",
    "californis": "CA",
}

SMALL_WORDS = {"of", "the", "and", "on", "in", "at", "for"}


def as_text(series: pd.Series) -> pd.Series:
    """Trim, collapse whitespace, and turn blank or 'Prefer not to answer' into missing."""
    text = series.astype("string").str.replace(r"\s+", " ", regex=True).str.strip()
    text = text.mask(text.str.lower() == PREFER_NOT_TO_ANSWER)
    return text.mask(text.str.len().eq(0))


def as_integer(
    series: pd.Series,
    top_codes: dict[str, int] | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> pd.Series:
    """Parse counts, including open-ended top codes such as '10 or more'.

    A top code becomes the smallest value it can represent: 'More than 5' -> 6,
    '10 or more' -> 10. The choice is documented in the data dictionary.
    """
    text = as_text(series)
    numeric = pd.to_numeric(text, errors="coerce").astype("Float64")

    if top_codes:
        mapping = {str(key).lower(): value for key, value in top_codes.items()}
        coded = text.str.lower().map(mapping).astype("Float64")
        numeric = numeric.fillna(coded)

    result = numeric.round().astype("Int64")
    if minimum is not None:
        result = result.mask(result < minimum)
    if maximum is not None:
        result = result.mask(result > maximum)
    return result


def as_ordinal(
    series: pd.Series,
    mapping: dict[str, int] | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> pd.Series:
    """Map labelled scales to integers, keeping plain numbers as they are.

    Handles both ``"4"`` and anchor-labelled answers such as ``"5 (very true)"``.
    """
    text = as_text(series)
    result = pd.Series(pd.NA, index=text.index, dtype="Int64")

    if mapping:
        lowered = {str(key).lower(): value for key, value in mapping.items()}
        result = result.fillna(text.str.lower().map(lowered).astype("Int64"))

    leading = pd.to_numeric(text.str.extract(r"^(\d+)", expand=False), errors="coerce")
    result = result.fillna(leading.astype("Int64"))

    if minimum is not None:
        result = result.mask(result < minimum)
    if maximum is not None:
        result = result.mask(result > maximum)
    return result


def as_boolean(
    series: pd.Series,
    true_values: set[str] = TRUE_VALUES,
    false_values: set[str] = FALSE_VALUES,
) -> pd.Series:
    """Map yes/no text to nullable booleans; anything else stays missing."""
    text = as_text(series).str.lower()
    result = pd.Series(pd.NA, index=text.index, dtype="boolean")
    result = result.mask(text.isin(true_values), True)
    result = result.mask(text.isin(false_values), False)
    return result


def as_datetime_text(series: pd.Series, fmt: str = "%m/%d/%Y %H:%M") -> pd.Series:
    """Parse a date and return it as a sortable ISO-8601 string."""
    parsed = pd.to_datetime(as_text(series), format=fmt, errors="coerce")
    return parsed.dt.strftime("%Y-%m-%d %H:%M").astype("string")


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned


def multiselect_flags(
    series: pd.Series,
    categories: dict[str, str],
    prefix: str,
) -> pd.DataFrame:
    """Expand a comma-separated 'check all that apply' answer into 0/1 columns.

    ``categories`` maps an output suffix to the label as it appears in the data.
    Rows that skipped the question stay missing in every indicator; they are not
    silently coded as "none of these".
    """
    text = as_text(series)

    def tokens(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        if pd.isna(value):
            return []
        return [str(value).strip().lower()]

    split = text.str.split(",").apply(tokens)

    columns: dict[str, pd.Series] = {}
    for suffix, label in categories.items():
        wanted = label.lower()
        values = [
            pd.NA if pd.isna(source) else int(wanted in choices)
            for source, choices in zip(text, split, strict=True)
        ]
        columns[f"{prefix}_{suffix}"] = pd.array(values, dtype="Int8")
    return pd.DataFrame(columns, index=series.index)


def canonical_state(series: pd.Series) -> pd.Series:
    """Reduce state answers to two-letter USPS codes; unknown values become missing."""
    text = as_text(series)

    def one(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        key = " ".join(str(value).replace(".", "").split()).lower()
        if key in STATE_ALIASES:
            return STATE_ALIASES[key]
        if key in US_STATES:
            return US_STATES[key]
        if len(key) == 2 and key.upper() in STATE_CODES:
            return key.upper()
        return pd.NA

    return text.apply(one).astype("string")


def _title_case(value: str) -> str:
    words = value.split(" ")
    result: list[str] = []
    for position, word in enumerate(words):
        if position > 0 and word.lower() in SMALL_WORDS:
            result.append(word.lower())
        elif word.isupper() and len(word) <= 3:
            result.append(word)
        else:
            result.append(word[:1].upper() + word[1:])
    return " ".join(result)


def clean_place(
    series: pd.Series,
    drop_suffix: str | None = None,
    aliases: dict[str, str] | None = None,
) -> pd.Series:
    """Standardise free-text place names without guessing at misspellings."""
    text = as_text(series)
    lowered_aliases = {key.lower(): value for key, value in (aliases or {}).items()}

    def one(value: object) -> object:
        if pd.isna(value):
            return pd.NA
        cleaned = " ".join(str(value).split())
        if drop_suffix and cleaned.lower().endswith(drop_suffix.lower()):
            cleaned = cleaned[: -len(drop_suffix)].strip()
        if cleaned.lower() in lowered_aliases:
            return lowered_aliases[cleaned.lower()]
        return _title_case(cleaned)

    return text.apply(one).astype("string")
