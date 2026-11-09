"""Turn the raw export into a documented, analysis-ready table.

``VARIABLES`` is the single source of truth: the pipeline builds exactly these
columns, and the generator writes the variable map from the same list. A test
fails if the two drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from survey_clean import recode
from survey_clean.quality import (
    flag_exact_duplicates,
    flag_incomplete,
    flag_long_session,
    flag_speeder,
    flag_straightline,
)


@dataclass(frozen=True)
class Variable:
    """One output column and the decision behind it."""

    name: str
    source: str
    dtype: str
    description: str
    values: str
    transformation: str


RACE_CATEGORIES: dict[str, str] = {
    "white": "White",
    "asian": "Asian",
    "black": "Black or African American",
    "native_american": "American Indian or Alaska Native",
    "pacific_islander": "Native Hawaiian or Pacific Islander",
    "other": "Other",
}

CITY_ALIASES: dict[str, str] = {
    "city of shasta lake": "Shasta Lake",
    "shasta lake city": "Shasta Lake",
}

COMPASSION_ITEMS = tuple(f"compassion_{index}" for index in range(1, 6))

DUPLICATE_IGNORE = [
    "response_id",
    "started_at",
    "finished_at",
    "duration_seconds",
    "progress_percent",
    "finished",
]

ANALYSIS_REQUIRED = ["age_bracket", "gender", "education", "income_band", "evacuated"]

VARIABLES: tuple[Variable, ...] = (
    Variable(
        "response_id",
        "ResponseId",
        "string",
        "Qualtrics response identifier",
        "R_...",
        "kept as text",
    ),
    Variable(
        "started_at",
        "StartDate",
        "datetime",
        "When the response was started",
        "ISO 8601, no timezone",
        "parsed as M/D/YYYY H:MM",
    ),
    Variable(
        "finished_at",
        "EndDate",
        "datetime",
        "When the response was submitted",
        "ISO 8601, no timezone",
        "parsed as M/D/YYYY H:MM",
    ),
    Variable(
        "duration_seconds",
        "Duration (in seconds)",
        "integer",
        "Time between start and submit",
        "seconds",
        "coerced to number",
    ),
    Variable(
        "progress_percent",
        "Progress",
        "integer",
        "Share of the questionnaire reached",
        "0-100",
        "coerced to number",
    ),
    Variable(
        "finished",
        "Finished",
        "boolean",
        "Qualtrics completion marker",
        "true / false / missing",
        "TRUE -> true, FALSE -> false",
    ),
    Variable(
        "evacuated",
        "Q9.1",
        "boolean",
        "Left home because of the Carr Fire",
        "true / false / missing",
        "Yes -> true, No -> false",
    ),
    Variable(
        "age_bracket",
        "Q32.2",
        "string",
        "Age group",
        "18 - 24 ... 85 or older",
        "labels kept; 'Prefer not to answer' -> missing",
    ),
    Variable(
        "gender",
        "Q32.3",
        "string",
        "Gender",
        "Female / Male / Other",
        "labels kept; free text not redistributed",
    ),
    Variable(
        "race_white",
        "Q32.4",
        "integer",
        "Selected White",
        "1 / 0 / missing",
        "multi-select expanded",
    ),
    Variable(
        "race_asian",
        "Q32.4",
        "integer",
        "Selected Asian",
        "1 / 0 / missing",
        "multi-select expanded",
    ),
    Variable(
        "race_black",
        "Q32.4",
        "integer",
        "Selected Black or African American",
        "1 / 0 / missing",
        "multi-select expanded",
    ),
    Variable(
        "race_native_american",
        "Q32.4",
        "integer",
        "Selected American Indian or Alaska Native",
        "1 / 0 / missing",
        "multi-select expanded",
    ),
    Variable(
        "race_pacific_islander",
        "Q32.4",
        "integer",
        "Selected Native Hawaiian or Pacific Islander",
        "1 / 0 / missing",
        "multi-select expanded",
    ),
    Variable(
        "race_other",
        "Q32.4",
        "integer",
        "Selected Other race",
        "1 / 0 / missing",
        "multi-select expanded",
    ),
    Variable(
        "ethnicity",
        "Q32.5",
        "string",
        "Hispanic, Latino or Spanish origin",
        "Yes / No labels",
        "labels kept",
    ),
    Variable(
        "education", "Q32.6", "string", "Highest completed education", "8 labels", "labels kept"
    ),
    Variable(
        "employment", "Q32.7", "string", "Current employment status", "8 labels", "labels kept"
    ),
    Variable(
        "income_band",
        "Q32.13",
        "string",
        "Household income in 2018",
        "10 bands",
        "labels kept, not converted to midpoints",
    ),
    Variable(
        "household_size",
        "Q32.8_1",
        "integer",
        "People in the household",
        "1-9, 10 = '10 or more'",
        "top-coded at 10",
    ),
    Variable(
        "household_employed",
        "Q32.8_2",
        "integer",
        "Household members employed full or part time",
        "0-9, 10 = '10 or more'",
        "top-coded at 10",
    ),
    Variable(
        "children_under_18",
        "Q32.8_3",
        "integer",
        "Children under 18 in the household",
        "0-9, 10 = '10 or more'",
        "top-coded at 10",
    ),
    Variable(
        "adults_over_65",
        "Q32.8_4",
        "integer",
        "Adults over 65 in the household",
        "0+",
        "coerced to number",
    ),
    Variable(
        "household_disabled",
        "Q32.8_5",
        "integer",
        "Household members with a disability",
        "0+",
        "coerced to number",
    ),
    Variable(
        "vehicles",
        "Q32.11",
        "integer",
        "Household automobiles",
        "1-5, 6 = 'More than 5'",
        "top-coded at 6",
    ),
    Variable(
        "state",
        "Q33.1",
        "string",
        "State of residence",
        "two-letter USPS code",
        "free text standardised; unknown values -> missing",
    ),
    Variable(
        "county",
        "Q33.2",
        "string",
        "County of residence",
        "title case, no 'County' suffix",
        "trimmed, title-cased, suffix dropped",
    ),
    Variable(
        "city",
        "Q33.3",
        "string",
        "City of residence",
        "title case",
        "trimmed, title-cased, two aliases merged",
    ),
    Variable(
        "home_type",
        "Q33.9",
        "string",
        "Type of residence before the fire",
        "3 labels + don't know",
        "labels kept",
    ),
    Variable(
        "owns_home",
        "Q33.10",
        "boolean",
        "Owned the pre-fire residence",
        "true / false / missing",
        "Yes -> true, No -> false",
    ),
    Variable(
        "years_in_home",
        "Q33.7",
        "string",
        "Time in the residence before the fire",
        "8 bands",
        "labels kept",
    ),
    Variable(
        "fire_severity_zone",
        "Q33.6",
        "string",
        "Lived in a Very High or High fire severity zone",
        "Yes / No / I don't know",
        "labels kept; 'don't know' kept as a category",
    ),
    Variable(
        "prior_evacuations",
        "Q34.2",
        "integer",
        "Evacuations before this fire",
        "0-5, 6 = 'More than 5'",
        "top-coded at 6",
    ),
    Variable(
        "earthquake_count",
        "Q34.1_1",
        "integer",
        "Earthquakes experienced",
        "0-5, 6 = 'More than 5'",
        "top-coded at 6",
    ),
    Variable(
        "flood_count",
        "Q34.1_2",
        "integer",
        "Floods experienced",
        "0-5, 6 = 'More than 5'",
        "top-coded at 6",
    ),
    Variable(
        "wildfire_count",
        "Q34.1_3",
        "integer",
        "Wildfires experienced",
        "0-5, 6 = 'More than 5'",
        "top-coded at 6",
    ),
    Variable(
        "community_org_member",
        "Q35.2",
        "boolean",
        "Member of a community organisation",
        "true / false / missing",
        "Yes -> true, No -> false",
    ),
    Variable(
        "trusts_most_people",
        "Q35.4",
        "boolean",
        "Says most people can be trusted",
        "true / false / missing",
        "two long options mapped to true and false",
    ),
    Variable(
        "volunteered_during_fire",
        "Q35.7",
        "boolean",
        "Volunteered in relief efforts",
        "true / false / missing",
        "Yes -> true, No -> false",
    ),
    Variable(
        "already_insured",
        "Q34.3",
        "boolean",
        "Already held natural-disaster insurance",
        "true / false / missing",
        "split out of the insurance question",
    ),
    Variable(
        "insurance_intent",
        "Q34.3",
        "string",
        "Likelihood of buying natural-disaster insurance",
        "5 labels",
        "missing when already insured",
    ),
    Variable(
        "transport_before",
        "Q35.9",
        "string",
        "Offered transport to a non-household member before evacuating",
        "No / offered / provided",
        "labels kept",
    ),
    Variable(
        "transport_during",
        "Q35.10",
        "string",
        "Offered transport during the evacuation",
        "No / offered / provided",
        "labels kept",
    ),
    Variable(
        "transport_after",
        "Q35.11",
        "string",
        "Offered transport after the evacuation",
        "No / offered / provided",
        "labels kept",
    ),
    Variable(
        "shelter_paid",
        "Q35.12",
        "string",
        "Offered shelter for a fee",
        "No / offered / provided",
        "labels kept",
    ),
    Variable(
        "shelter_free",
        "Q35.13",
        "string",
        "Offered shelter for free",
        "No / offered / provided",
        "labels kept",
    ),
    Variable(
        "compassion_1",
        "Q35.6_1",
        "integer",
        "Compassion scale, item 1",
        "1-5",
        "anchor labels stripped to integers",
    ),
    Variable(
        "compassion_2",
        "Q35.6_2",
        "integer",
        "Compassion scale, item 2",
        "1-5",
        "anchor labels stripped to integers",
    ),
    Variable(
        "compassion_3",
        "Q35.6_3",
        "integer",
        "Compassion scale, item 3",
        "1-5",
        "anchor labels stripped to integers",
    ),
    Variable(
        "compassion_4",
        "Q35.6_4",
        "integer",
        "Compassion scale, item 4",
        "1-5",
        "anchor labels stripped to integers",
    ),
    Variable(
        "compassion_5",
        "Q35.6_5",
        "integer",
        "Compassion scale, item 5",
        "1-5",
        "anchor labels stripped to integers",
    ),
    Variable(
        "flag_incomplete",
        "derived",
        "boolean",
        "Not finished or never reached 100% progress",
        "true / false",
        "Finished and Progress",
    ),
    Variable(
        "flag_speeder",
        "derived",
        "boolean",
        "Finished in under 300 seconds",
        "true / false",
        "Duration (in seconds)",
    ),
    Variable(
        "flag_long_session",
        "derived",
        "boolean",
        "Session longer than six hours",
        "true / false",
        "Duration (in seconds)",
    ),
    Variable(
        "flag_straightline",
        "derived",
        "boolean",
        "Same answer to all answered compassion items",
        "true / false",
        "compassion_1 to compassion_5, at least 4 answered",
    ),
    Variable(
        "flag_possible_duplicate",
        "derived",
        "boolean",
        "Repeats an earlier completed response on every answer",
        "true / false",
        "exact match on all answer columns among finished responses",
    ),
    Variable(
        "analysis_ready",
        "derived",
        "boolean",
        "Passes the documented sample filter",
        "true / false",
        "finished, 300-21600 s, five key variables present, no exact duplicate",
    ),
)

VARIABLE_NAMES: tuple[str, ...] = tuple(variable.name for variable in VARIABLES)


def _trust(series: pd.Series) -> pd.Series:
    text = recode.as_text(series).str.lower()
    result = pd.Series(pd.NA, index=text.index, dtype="boolean")
    result = result.mask(text.str.startswith("it is possible", na=False), True)
    result = result.mask(text.str.startswith("we can never", na=False), False)
    return result


def build_clean_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Build the curated frame from a header-stripped export."""
    frame = pd.DataFrame(index=raw.index)

    frame["response_id"] = recode.as_text(raw["ResponseId"])
    frame["started_at"] = recode.as_datetime_text(raw["StartDate"])
    frame["finished_at"] = recode.as_datetime_text(raw["EndDate"])
    frame["duration_seconds"] = recode.as_integer(raw["Duration (in seconds)"])
    frame["progress_percent"] = recode.as_integer(raw["Progress"])
    frame["finished"] = recode.as_boolean(raw["Finished"], {"true"}, {"false"})
    frame["evacuated"] = recode.as_boolean(raw["Q9.1"])

    frame["age_bracket"] = recode.as_text(raw["Q32.2"])
    frame["gender"] = recode.as_text(raw["Q32.3"])
    frame = frame.join(recode.multiselect_flags(raw["Q32.4"], RACE_CATEGORIES, "race"))
    frame["ethnicity"] = recode.as_text(raw["Q32.5"])
    frame["education"] = recode.as_text(raw["Q32.6"])
    frame["employment"] = recode.as_text(raw["Q32.7"])
    frame["income_band"] = recode.as_text(raw["Q32.13"])

    ten_or_more = {"10 or more": 10}
    frame["household_size"] = recode.as_integer(raw["Q32.8_1"], ten_or_more)
    frame["household_employed"] = recode.as_integer(raw["Q32.8_2"], ten_or_more)
    frame["children_under_18"] = recode.as_integer(raw["Q32.8_3"], ten_or_more)
    frame["adults_over_65"] = recode.as_integer(raw["Q32.8_4"])
    frame["household_disabled"] = recode.as_integer(raw["Q32.8_5"])
    frame["vehicles"] = recode.as_integer(raw["Q32.11"], {"more than 5": 6})

    frame["state"] = recode.canonical_state(raw["Q33.1"])
    frame["county"] = recode.clean_place(raw["Q33.2"], drop_suffix="County")
    frame["city"] = recode.clean_place(raw["Q33.3"], aliases=CITY_ALIASES)
    frame["home_type"] = recode.as_text(raw["Q33.9"])
    frame["owns_home"] = recode.as_boolean(raw["Q33.10"])
    frame["years_in_home"] = recode.as_text(raw["Q33.7"])
    frame["fire_severity_zone"] = recode.as_text(raw["Q33.6"])

    more_than_five = {"more than 5": 6}
    frame["prior_evacuations"] = recode.as_integer(raw["Q34.2"], more_than_five)
    frame["earthquake_count"] = recode.as_integer(raw["Q34.1_1"], more_than_five)
    frame["flood_count"] = recode.as_integer(raw["Q34.1_2"], more_than_five)
    frame["wildfire_count"] = recode.as_integer(raw["Q34.1_3"], more_than_five)

    frame["community_org_member"] = recode.as_boolean(raw["Q35.2"])
    frame["trusts_most_people"] = _trust(raw["Q35.4"])
    frame["volunteered_during_fire"] = recode.as_boolean(raw["Q35.7"])

    insurance = recode.as_text(raw["Q34.3"])
    already = insurance.str.lower().eq("i already have a type of insurance for natural disasters")
    frame["already_insured"] = already.astype("boolean").mask(insurance.isna())
    frame["insurance_intent"] = insurance.mask(already).mask(insurance.isna())

    frame["transport_before"] = recode.as_text(raw["Q35.9"])
    frame["transport_during"] = recode.as_text(raw["Q35.10"])
    frame["transport_after"] = recode.as_text(raw["Q35.11"])
    frame["shelter_paid"] = recode.as_text(raw["Q35.12"])
    frame["shelter_free"] = recode.as_text(raw["Q35.13"])

    for index, name in enumerate(COMPASSION_ITEMS, start=1):
        frame[name] = recode.as_ordinal(raw[f"Q35.6_{index}"], minimum=1, maximum=5)

    frame["flag_incomplete"] = flag_incomplete(frame["finished"], frame["progress_percent"])
    frame["flag_speeder"] = flag_speeder(frame["duration_seconds"])
    frame["flag_long_session"] = flag_long_session(frame["duration_seconds"])
    frame["flag_straightline"] = flag_straightline(frame[list(COMPASSION_ITEMS)], min_items=4)

    finished = frame["finished"].fillna(False)
    duplicates = pd.Series(False, index=frame.index, dtype="boolean")
    quality_columns = [column for column in frame.columns if column.startswith("flag_")]
    duplicates.loc[finished] = flag_exact_duplicates(
        frame.loc[finished], DUPLICATE_IGNORE + quality_columns
    ).astype("boolean")
    frame["flag_possible_duplicate"] = duplicates

    usable = (
        frame["finished"].fillna(False)
        & ~frame["flag_speeder"].fillna(False)
        & ~frame["flag_long_session"].fillna(False)
        & ~frame["flag_possible_duplicate"].fillna(False)
        & frame[ANALYSIS_REQUIRED].notna().all(axis=1)
    )
    frame["analysis_ready"] = usable.astype("boolean")

    return frame[list(VARIABLE_NAMES)]


def select_analysis_sample(clean: pd.DataFrame) -> pd.DataFrame:
    """Rows that pass the documented filter."""
    return clean.loc[clean["analysis_ready"].fillna(False)].copy()
