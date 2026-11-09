from __future__ import annotations

import pandas as pd

from survey_clean import recode


def series(values: list[object]) -> pd.Series:
    return pd.Series(values, dtype="string")


def test_as_text_trims_and_treats_prefer_not_to_answer_as_missing() -> None:
    result = recode.as_text(series(["  California ", "Prefer not to answer", " CA "]))
    assert result.tolist()[0] == "California"
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == "CA"


def test_as_integer_reads_top_codes_at_their_floor() -> None:
    result = recode.as_integer(
        series(["2", "More than 5", "10 or more", "", "not a number"]),
        {"more than 5": 6, "10 or more": 10},
    )
    assert result.tolist() == [2, 6, 10, pd.NA, pd.NA]


def test_as_integer_clips_values_outside_the_allowed_range() -> None:
    result = recode.as_integer(series(["1", "9", "120"]), maximum=30)
    assert result.tolist() == [1, 9, pd.NA]


def test_as_ordinal_strips_anchor_labels_and_plain_digits() -> None:
    result = recode.as_ordinal(series(["5 (very true)", "4", "1 (not at all true)"]))
    assert result.tolist() == [5, 4, 1]


def test_as_ordinal_uses_a_label_map_before_leading_digits() -> None:
    result = recode.as_ordinal(
        series(["Neither high nor low", "Extremely high"]),
        {"extremely high": 7, "neither high nor low": 4},
        minimum=1,
        maximum=7,
    )
    assert result.tolist() == [4, 7]


def test_as_ordinal_rejects_values_off_the_scale() -> None:
    result = recode.as_ordinal(series(["0", "6"]), minimum=1, maximum=5)
    assert result.tolist() == [pd.NA, pd.NA]


def test_as_boolean_is_nullable() -> None:
    result = recode.as_boolean(series(["Yes", "No", ""]))
    assert result.tolist() == [True, False, pd.NA]
    assert str(result.dtype) == "boolean"


def test_as_datetime_text_returns_iso_strings_and_nat_stays_missing() -> None:
    result = recode.as_datetime_text(series(["3/12/2019 10:01", "not a date"]))
    assert result.iloc[0] == "2019-03-12 10:01"
    assert pd.isna(result.iloc[1])


def test_multiselect_flags_keep_skipped_questions_missing() -> None:
    categories = {"white": "White", "asian": "Asian"}
    result = recode.multiselect_flags(
        series(["White,Asian", "White", "Prefer not to answer", ""]),
        categories,
        "race",
    )
    assert result.columns.tolist() == ["race_white", "race_asian"]
    assert result.loc[0].tolist() == [1, 1]
    assert result.loc[1].tolist() == [1, 0]
    assert result.loc[2].isna().all()
    assert result.loc[3].isna().all()


def test_multiselect_flags_ignore_spacing_and_case() -> None:
    result = recode.multiselect_flags(series([" asian , WHITE "]), {"white": "White"}, "race")
    assert result.iloc[0].tolist() == [1]


def test_canonical_state_merges_observed_variants_and_drops_unknown() -> None:
    result = recode.canonical_state(
        series(["California", "California ", "CA", "ca", "Calif", "Californis", "Oregon", "ZZ"])
    )
    assert result.tolist()[:6] == ["CA"] * 6
    assert result.iloc[6] == "OR"
    assert pd.isna(result.iloc[7])


def test_clean_place_strips_county_suffix_and_uses_aliases() -> None:
    aliases = {"city of shasta lake": "Shasta Lake"}
    counties = recode.clean_place(series(["shasta county", "Shasta "]), drop_suffix="County")
    cities = recode.clean_place(series(["City of Shasta Lake", "shasta lake"]), aliases=aliases)
    assert counties.tolist() == ["Shasta", "Shasta"]
    assert cities.tolist() == ["Shasta Lake", "Shasta Lake"]
