"""Tests for aggregation operations in typewing using DuckDB backend."""

import pytest
import ibis
import pandas as pd
import numpy as np
from typewing import IbisModel


class TestData(IbisModel):
    """Model for test data table."""

    __tablename__ = "test_data"

    id: int
    int_col: int
    double_col: float
    string_col: str
    bool_col: bool
    bigint_col: int
    timestamp_col: str  # Will store timestamp as string for simplicity


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create test table
    con.raw_sql(
        """
        CREATE TABLE test_data (
            id INTEGER,
            int_col INTEGER,
            double_col DOUBLE,
            string_col VARCHAR,
            bool_col BOOLEAN,
            bigint_col BIGINT,
            timestamp_col TIMESTAMP
        )
        """
    )

    # Insert test data - creating a meaningful dataset
    con.raw_sql(
        """
        INSERT INTO test_data VALUES
            (1, 1, 1.5, '1', true, 10, '2009-01-01 00:00:00'),
            (2, 2, 2.5, '2', false, 10, '2009-02-01 00:00:00'),
            (3, 3, 3.5, '3', true, 20, '2009-03-01 00:00:00'),
            (4, 4, 4.5, '4', false, 20, '2009-04-01 00:00:00'),
            (5, 5, 5.5, '5', true, 30, '2009-05-01 00:00:00'),
            (6, 6, 6.5, '6', false, 30, '2009-06-01 00:00:00'),
            (7, 7, 7.5, '7', true, 40, '2009-07-01 00:00:00'),
            (8, 8, 8.5, '8', false, 40, '2009-08-01 00:00:00'),
            (9, 0, 9.5, '9', true, 50, '2009-09-01 00:00:00'),
            (10, 1, 10.5, '1', false, 50, '2009-10-01 00:00:00')
        """
    )

    yield con
    con.disconnect()


@pytest.fixture
def test_table(duckdb_con):
    """Get the bound test table."""
    return TestData.bind(duckdb_con)


@pytest.fixture
def df(duckdb_con):
    """Get the test data as a pandas DataFrame."""
    return duckdb_con.execute(duckdb_con.table("test_data"))


# Basic Aggregation Tests


def test_mean_aggregate(test_table, df):
    """Test mean aggregation."""
    result = test_table.aggregate(mean_val=test_table.double_col.mean()).execute()
    expected = df.double_col.mean()
    assert pytest.approx(result["mean_val"].iloc[0]) == expected


def test_min_aggregate(test_table, df):
    """Test min aggregation."""
    result = test_table.aggregate(min_val=test_table.double_col.min()).execute()
    expected = df.double_col.min()
    assert pytest.approx(result["min_val"].iloc[0]) == expected


def test_max_aggregate(test_table, df):
    """Test max aggregation."""
    result = test_table.aggregate(max_val=test_table.double_col.max()).execute()
    expected = df.double_col.max()
    assert pytest.approx(result["max_val"].iloc[0]) == expected


def test_sum_aggregate(test_table, df):
    """Test sum aggregation."""
    result = test_table.aggregate(sum_val=test_table.double_col.sum()).execute()
    expected = df.double_col.sum()
    assert pytest.approx(result["sum_val"].iloc[0]) == expected


def test_count_aggregate(test_table, df):
    """Test count aggregation."""
    result = test_table.aggregate(count_val=test_table.count()).execute()
    expected = len(df)
    assert result["count_val"].iloc[0] == expected


def test_complex_sum(test_table, df):
    """Test sum with expression."""
    result = test_table.aggregate(sum_val=(test_table.double_col + 5).sum()).execute()
    expected = (df.double_col + 5).sum()
    assert pytest.approx(result["sum_val"].iloc[0]) == expected


# Grouped Aggregation Tests


def test_grouped_mean(test_table, df):
    """Test mean aggregation with group by."""
    result = (
        test_table.group_by("bigint_col")
        .aggregate(mean_val=test_table.double_col.mean())
        .order_by("bigint_col")
        .execute()
    )

    expected = (
        df.groupby("bigint_col")
        .double_col.mean()
        .rename("mean_val")
        .reset_index()
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected, check_dtype=False
    )


def test_grouped_with_by_parameter(test_table, df):
    """Test aggregation using 'by' parameter."""
    result = (
        test_table.aggregate(sum_val=test_table.int_col.sum(), by="bigint_col")
        .order_by("bigint_col")
        .execute()
    )

    expected = (
        df.groupby("bigint_col")
        .int_col.sum()
        .rename("sum_val")
        .reset_index()
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected, check_dtype=False
    )


# Conditional Aggregation Tests (with where clause)


def test_count_with_where(test_table, df):
    """Test count with where condition."""
    where_cond = test_table.string_col.isin(["1", "7"])
    result = test_table.aggregate(
        count_val=test_table.bool_col.count(where=where_cond)
    ).execute()

    expected = len(df.bool_col[df.string_col.isin(["1", "7"])].dropna())
    assert result["count_val"].iloc[0] == expected


def test_sum_with_where(test_table, df):
    """Test sum with where condition."""
    where_cond = test_table.string_col.isin(["1", "7"])
    result = test_table.aggregate(
        sum_val=test_table.double_col.sum(where=where_cond)
    ).execute()

    expected = df.double_col[df.string_col.isin(["1", "7"])].sum()
    assert pytest.approx(result["sum_val"].iloc[0]) == expected


def test_mean_with_where(test_table, df):
    """Test mean with where condition."""
    where_cond = test_table.string_col.isin(["1", "7"])
    result = test_table.aggregate(
        mean_val=test_table.double_col.mean(where=where_cond)
    ).execute()

    expected = df.double_col[df.string_col.isin(["1", "7"])].mean()
    assert pytest.approx(result["mean_val"].iloc[0]) == expected


# Statistical Aggregation Tests


def test_std_aggregate(test_table, df):
    """Test standard deviation aggregation."""
    result = test_table.aggregate(
        std_val=test_table.double_col.std(how="sample")
    ).execute()

    expected = df.double_col.std(ddof=1)
    assert pytest.approx(result["std_val"].iloc[0]) == expected


def test_var_aggregate(test_table, df):
    """Test variance aggregation."""
    result = test_table.aggregate(
        var_val=test_table.double_col.var(how="sample")
    ).execute()

    expected = df.double_col.var(ddof=1)
    assert pytest.approx(result["var_val"].iloc[0]) == expected


def test_std_pop_aggregate(test_table, df):
    """Test population standard deviation."""
    result = test_table.aggregate(
        std_val=test_table.double_col.std(how="pop")
    ).execute()

    expected = df.double_col.std(ddof=0)
    assert pytest.approx(result["std_val"].iloc[0]) == expected


def test_var_pop_aggregate(test_table, df):
    """Test population variance."""
    result = test_table.aggregate(
        var_val=test_table.double_col.var(how="pop")
    ).execute()

    expected = df.double_col.var(ddof=0)
    assert pytest.approx(result["var_val"].iloc[0]) == expected


# Boolean Aggregation Tests


def test_any_aggregate(test_table, df):
    """Test any aggregation."""
    result = test_table.aggregate(any_val=test_table.bool_col.any()).execute()

    expected = df.bool_col.any()
    assert result["any_val"].iloc[0] == expected


def test_all_aggregate(test_table, df):
    """Test all aggregation."""
    result = test_table.aggregate(all_val=test_table.bool_col.all()).execute()

    expected = df.bool_col.all()
    assert result["all_val"].iloc[0] == expected


def test_any_with_where(test_table, df):
    """Test any with where condition."""
    where_cond = test_table.string_col.isin(["1", "7"])
    result = test_table.aggregate(
        any_val=test_table.bool_col.any(where=where_cond)
    ).execute()

    expected = df.bool_col[df.string_col.isin(["1", "7"])].any()
    assert result["any_val"].iloc[0] == expected


def test_all_with_where(test_table, df):
    """Test all with where condition."""
    where_cond = test_table.string_col.isin(["1", "3", "5", "7", "9"])
    result = test_table.aggregate(
        all_val=test_table.bool_col.all(where=where_cond)
    ).execute()

    expected = df.bool_col[df.string_col.isin(["1", "3", "5", "7", "9"])].all()
    assert result["all_val"].iloc[0] == expected


# Distinct Count Tests


def test_nunique(test_table, df):
    """Test nunique (count distinct)."""
    result = test_table.aggregate(nunique_val=test_table.string_col.nunique()).execute()

    expected = df.string_col.nunique()
    assert result["nunique_val"].iloc[0] == expected


def test_nunique_with_where(test_table, df):
    """Test nunique with where condition."""
    where_cond = test_table.bigint_col >= 20
    result = test_table.aggregate(
        nunique_val=test_table.string_col.nunique(where=where_cond)
    ).execute()

    expected = df.string_col[df.bigint_col >= 20].nunique()
    assert result["nunique_val"].iloc[0] == expected


# String Aggregation Tests


def test_group_concat(test_table, df):
    """Test group_concat (string aggregation)."""
    result = (
        test_table.group_by("bigint_col")
        .aggregate(concat_val=test_table.string_col.group_concat(":"))
        .order_by("bigint_col")
        .execute()
    )

    expected = (
        df.groupby("bigint_col")
        .string_col.agg(lambda s: ":".join(s.values))
        .rename("concat_val")
        .reset_index()
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected, check_dtype=False
    )


def test_group_concat_with_where(test_table, df):
    """Test group_concat with where condition."""
    where_cond = test_table.string_col.isin(["1", "3", "5", "7"])

    result = (
        test_table.group_by("bigint_col")
        .aggregate(concat_val=test_table.string_col.group_concat(":", where=where_cond))
        .order_by("bigint_col")
        .execute()
    )

    expected = (
        df.assign(
            string_col=df.string_col.where(df.string_col.isin(["1", "3", "5", "7"]))
        )
        .groupby("bigint_col")
        .string_col.agg(
            lambda s: (np.nan if pd.isna(s).all() else ":".join(s.dropna().values))
        )
        .rename("concat_val")
        .reset_index()
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        result.replace(np.nan, None).reset_index(drop=True),
        expected.replace(np.nan, None),
        check_dtype=False,
    )


# Multiple Aggregations


def test_multiple_aggregations(test_table, df):
    """Test multiple aggregations at once."""
    result = test_table.aggregate(
        mean_val=test_table.double_col.mean(),
        sum_val=test_table.int_col.sum(),
        count_val=test_table.count(),
        max_val=test_table.double_col.max(),
    ).execute()

    assert pytest.approx(result["mean_val"].iloc[0]) == df.double_col.mean()
    assert result["sum_val"].iloc[0] == df.int_col.sum()
    assert result["count_val"].iloc[0] == len(df)
    assert pytest.approx(result["max_val"].iloc[0]) == df.double_col.max()


def test_multiple_grouped_aggregations(test_table, df):
    """Test multiple aggregations with group by."""
    result = (
        test_table.group_by("bigint_col")
        .aggregate(
            mean_val=test_table.double_col.mean(),
            sum_val=test_table.int_col.sum(),
            count_val=test_table.count(),
        )
        .order_by("bigint_col")
        .execute()
    )

    expected = (
        df.groupby("bigint_col")
        .agg(
            mean_val=("double_col", "mean"),
            sum_val=("int_col", "sum"),
            count_val=("id", "count"),
        )
        .reset_index()
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    pd.testing.assert_frame_equal(
        result.reset_index(drop=True), expected, check_dtype=False
    )


# Expression-based Aggregations


def test_aggregate_with_expression(test_table, df):
    """Test aggregation on expression."""
    result = test_table.aggregate(bool_sum=(test_table.int_col > 0).sum()).execute()

    expected = (df.int_col > 0).sum()
    assert result["bool_sum"].iloc[0] == expected


def test_aggregate_modulo_expression(test_table, df):
    """Test aggregation with modulo expression."""
    result = test_table.aggregate(avg_mod=(test_table.int_col % 3).mean()).execute()

    expected = (df.int_col % 3).mean()
    assert pytest.approx(result["avg_mod"].iloc[0]) == expected


# Bit Aggregation Tests


def test_bit_and(test_table, df):
    """Test bitwise AND aggregation."""
    result = test_table.aggregate(bit_and_val=test_table.bigint_col.bit_and()).execute()

    expected = np.bitwise_and.reduce(df.bigint_col.values)
    assert result["bit_and_val"].iloc[0] == expected


def test_bit_or(test_table, df):
    """Test bitwise OR aggregation."""
    result = test_table.aggregate(bit_or_val=test_table.bigint_col.bit_or()).execute()

    expected = np.bitwise_or.reduce(df.bigint_col.values)
    assert result["bit_or_val"].iloc[0] == expected


def test_bit_xor(test_table, df):
    """Test bitwise XOR aggregation."""
    result = test_table.aggregate(bit_xor_val=test_table.bigint_col.bit_xor()).execute()

    expected = np.bitwise_xor.reduce(df.bigint_col.values)
    assert result["bit_xor_val"].iloc[0] == expected


# Filter and Aggregate


def test_filter_then_aggregate(test_table, df):
    """Test filtering before aggregation."""
    result = (
        test_table.filter(test_table.string_col == "1")
        .aggregate(sum_val=test_table.double_col.sum())
        .execute()
    )

    expected = df.loc[df.string_col == "1", "double_col"].sum()
    assert pytest.approx(result["sum_val"].iloc[0]) == expected


def test_value_counts(test_table, df):
    """Test value_counts aggregation."""
    result = (
        test_table.bigint_col.value_counts()
        .order_by("bigint_col")
        .execute()
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    expected = (
        df.bigint_col.value_counts()
        .reset_index()
        .rename(columns={"index": "bigint_col", "count": "bigint_col_count"})
        .sort_values("bigint_col")
        .reset_index(drop=True)
    )

    # The column names might differ, so just check the values
    assert list(result["bigint_col"]) == list(expected["bigint_col"])
    assert list(result.iloc[:, 1]) == list(expected.iloc[:, 1])
