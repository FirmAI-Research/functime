from typing import List, Optional

import polars as pl
from holidays import country_holidays
from typing_extensions import Literal

from functime.base import transformer
from functime.ranges import make_future_ranges


@transformer
def add_calendar_effects(
    attrs: List[
        Literal["minute", "hour", "day", "weekday", "week", "month", "quarter", "year"]
    ],
):
    """Extract calendar effects from time column, returns calendar effects as categorical columns.

    Parameters
    ----------
    attrs : list of str
        List of calendar effects to be applied to the time column:\n
        - "minute"
        - "hour"
        - "day"
        - "weekday"
        - "week"
        - "month"
        - "quarter"
        - "year"
    """

    def transform(X: pl.LazyFrame) -> pl.LazyFrame:
        time_col = pl.col(X.columns[1])
        X_new = X.with_columns(
            [
                getattr(time_col.dt, attr)()
                .alias(attr)
                .cast(pl.Utf8)
                .cast(pl.Categorical)
                for attr in attrs
            ]
        )
        artifacts = {"X_new": X_new}
        return artifacts

    return transform


@transformer
def add_holiday_effects(country_codes: List[str], freq: str):
    """Extract holiday effects from time column for specified ISO-2 country codes and frequency.

    Parameters
    ----------
    country_codes : List[str]
        A list of ISO-2 country codes.
    freq : str
        Sampling frequency at which to group data.
        Must be specified as an offset alias supported by Polars.
    """

    def transform(X: pl.LazyFrame) -> pl.LazyFrame:

        # Get min and max timestamps
        time_col = X.columns[1]
        timestamps = (
            X.select(time_col)
            .collect(streaming=True)
            .get_column(time_col)
            .unique()
            .to_list()
        )
        min_ts, max_ts = min(timestamps), max(timestamps)
        # Instantiate countries mapping
        years = range(min_ts.year, max_ts.year + 1)
        countries = [country_holidays(code, years=years) for code in country_codes]
        # Add holiday effects and cast as categorical
        holidays = []
        for i, country in enumerate(countries):
            labels = pl.Series(
                values=[country.get(t) for t in timestamps],
                name=f"holiday__{country_codes[i]}",
            ).to_frame()
            holidays.append(labels)
        # Concat
        holidays = (
            pl.concat(holidays, how="horizontal")
            .select(
                pl.all()
                .str.to_lowercase()
                .str.replace_all("'", "")
                .str.replace_all("-", "")
                .str.replace_all(" ", "_")
                .cast(pl.Categorical)
            )
            .with_columns(
                pl.Series(values=timestamps, name=time_col).cast(X.schema[time_col])
            )
            .lazy()
        )
        X_new = X.join(holidays, how="left", on=time_col)
        artifacts = {"X_new": X_new}
        return artifacts

    return transform


def make_future_calendar_effects(
    idx: pl.DataFrame,
    attrs: List[str],
    fh: int,
    freq: Optional[str] = None,
):
    entity_col, time_col = idx.columns[:2]
    cutoffs = idx.groupby(entity_col).agg(pl.col(time_col).max().alias("low"))
    future_idx = make_future_ranges(
        time_col=time_col,
        cutoffs=cutoffs,
        fh=fh,
        freq=freq,
    ).explode(time_col)
    transf = add_calendar_effects(attrs)
    return transf(future_idx)


def make_future_holiday_effects(
    idx: pl.DataFrame,
    country_codes: List[str],
    fh: int,
    freq: Optional[str] = None,
):
    entity_col, time_col = idx.columns[:2]
    cutoffs = idx.groupby(entity_col).agg(pl.col(time_col).max().alias("low"))
    future_idx = make_future_ranges(
        time_col=time_col,
        cutoffs=cutoffs,
        fh=fh,
        freq=freq,
    ).explode(time_col)
    transf = add_holiday_effects(country_codes, freq=freq)
    return transf(future_idx)
