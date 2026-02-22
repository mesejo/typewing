"""Tests for conditional expressions with TypedTable.

These tests verify that TypedTable works with ibis conditional expressions
like ifelse, cases, substitute, and nullif.
"""

from __future__ import annotations

import ibis
import pytest

from typewing import SemanticModel
from typewing.model import TypedTable


class SalesData(SemanticModel):
    """Model for sales data."""

    __tablename__ = "sales"

    id: int
    amount: float
    category: str
    status: str


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create sales table
    con.raw_sql(
        """
        CREATE TABLE sales (
            id INTEGER,
            amount DOUBLE,
            category VARCHAR,
            status VARCHAR
        )
        """
    )

    # Insert test data
    con.raw_sql(
        """
        INSERT INTO sales VALUES
            (1, 100.0, 'A', 'completed'),
            (2, 0.0, 'B', 'pending'),
            (3, 250.0, 'A', 'completed'),
            (4, 0.0, 'C', 'cancelled'),
            (5, 500.0, 'B', 'completed'),
            (6, 75.0, 'A', 'pending'),
            (7, 0.0, 'B', 'cancelled'),
            (8, 300.0, 'C', 'completed')
        """
    )

    yield con
    con.disconnect()


def test_ifelse_with_select_returns_typed_table(duckdb_con):
    """Test that select with ibis.ifelse expression returns TypedTable."""
    SalesTable = SalesData.bind(duckdb_con)

    # Use ibis.ifelse to create a conditional column
    query = SalesTable.select(
        [
            "id",
            "amount",
            ibis.ifelse(SalesTable.amount == 0, "zero", "non-zero").name("amount_flag"),
        ]
    )

    # Should return TypedTable
    assert isinstance(query, TypedTable)

    # Execute and verify
    result = query.execute()
    assert len(result) == 8
    assert "amount_flag" in result.columns

    # Verify conditional logic works
    zero_amounts = result[result["amount"] == 0.0]
    assert all(zero_amounts["amount_flag"] == "zero")

    non_zero_amounts = result[result["amount"] > 0.0]
    assert all(non_zero_amounts["amount_flag"] == "non-zero")


def test_ifelse_with_numeric_values(duckdb_con):
    """Test ifelse with numeric conditional values."""
    SalesTable = SalesData.bind(duckdb_con)

    # Use ifelse to create bonus column
    query = SalesTable.select(
        [
            SalesTable.id,
            SalesTable.amount,
            ibis.ifelse(SalesTable.amount > 200, 50, 10).name("bonus"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) == 8

    # High amounts get 50 bonus
    high_amounts = result[result["amount"] > 200]
    assert all(high_amounts["bonus"] == 50)

    # Low amounts get 10 bonus
    low_amounts = result[result["amount"] <= 200]
    assert all(low_amounts["bonus"] == 10)


def test_cases_value_based(duckdb_con):
    """Test value-based case expressions with column."""
    SalesTable = SalesData.bind(duckdb_con)

    # Use .cases() on a column
    query = SalesTable.select(
        [
            SalesTable.id,
            SalesTable.category,
            SalesTable.category.cases(
                ("A", "Alpha"), ("B", "Beta"), ("C", "Charlie"), else_="Unknown"
            ).name("category_name"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) == 8
    assert "category_name" in result.columns

    # Verify mappings
    assert set(result[result["category"] == "A"]["category_name"]) == {"Alpha"}
    assert set(result[result["category"] == "B"]["category_name"]) == {"Beta"}
    assert set(result[result["category"] == "C"]["category_name"]) == {"Charlie"}


def test_ibis_cases_condition_based(duckdb_con):
    """Test ibis.cases with condition-based logic."""
    SalesTable = SalesData.bind(duckdb_con)

    # Use ibis.cases for complex conditions
    query = SalesTable.select(
        [
            SalesTable.id,
            SalesTable.amount,
            ibis.cases(
                (SalesTable.amount == 0, "no_sale"),
                (SalesTable.amount < 100, "small"),
                (SalesTable.amount < 300, "medium"),
                else_="large",
            ).name("sale_size"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) == 8

    # Verify conditional logic
    assert set(result[result["amount"] == 0.0]["sale_size"]) == {"no_sale"}
    assert set(result[result["amount"] == 75.0]["sale_size"]) == {"small"}
    assert set(result[result["amount"] == 100.0]["sale_size"]) == {"medium"}
    assert set(result[result["amount"] >= 300]["sale_size"]) == {"large"}


def test_nullif_and_substitute(duckdb_con):
    """Test nullif and substitute operations."""
    SalesTable = SalesData.bind(duckdb_con)

    # Use nullif to convert specific values to NULL, then substitute
    query = SalesTable.select(
        [
            SalesTable.id,
            SalesTable.status,
            SalesTable.status.nullif("cancelled")
            .substitute({None: "VOID"})
            .name("status_clean"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) == 8

    # Cancelled should be replaced with VOID
    cancelled_rows = result[result["status"] == "cancelled"]
    assert all(cancelled_rows["status_clean"] == "VOID")

    # Others should remain unchanged
    not_cancelled = result[result["status"] != "cancelled"]
    assert all(not_cancelled["status_clean"] == not_cancelled["status"])


def test_chained_conditionals(duckdb_con):
    """Test chaining multiple conditional operations."""
    SalesTable = SalesData.bind(duckdb_con)

    # Chain filter with conditional select
    query = (
        SalesTable.filter(SalesTable.amount > 0)
        .select(
            [
                SalesTable.id,
                SalesTable.amount,
                ibis.ifelse(SalesTable.amount > 200, "high", "low").name("tier"),
            ]
        )
        .filter(lambda t: t.tier == "high")
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    # Should only have amounts > 200
    assert all(result["amount"] > 200)
    assert all(result["tier"] == "high")


def test_mutate_with_conditionals(duckdb_con):
    """Test mutate with conditional expressions."""
    SalesTable = SalesData.bind(duckdb_con)

    # Use mutate to add conditional columns
    query = SalesTable.mutate(
        is_high_value=ibis.ifelse(SalesTable.amount > 250, True, False),
        tier=ibis.cases(
            (SalesTable.amount == 0, 0),
            (SalesTable.amount < 100, 1),
            (SalesTable.amount < 300, 2),
            else_=3,
        ),
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert "is_high_value" in result.columns
    assert "tier" in result.columns

    # Verify tier logic
    assert all(result[result["amount"] == 0]["tier"] == 0)
    assert all(result[result["amount"] == 75.0]["tier"] == 1)
    assert all(result[result["amount"] >= 300]["tier"] == 3)


def test_ibis_expressions_in_filter(duckdb_con):
    """Test that filter works with ibis conditional expressions."""
    SalesTable = SalesData.bind(duckdb_con)

    # Create a conditional expression
    is_valid = ibis.cases(
        (SalesTable.amount > 0, True),
        (SalesTable.status == "pending", True),
        else_=False,
    )

    # Use it in filter
    query = SalesTable.filter(is_valid).select(SalesTable.id, SalesTable.amount)

    assert isinstance(query, TypedTable)

    result = query.execute()
    # Should filter out zero amounts with non-pending status
    assert len(result) > 0


def test_select_accepts_mixed_expressions(duckdb_con):
    """Test that select accepts both column references and ibis expressions."""
    SalesTable = SalesData.bind(duckdb_con)

    # Mix column references, ibis expressions, and literals
    query = SalesTable.select(
        [
            SalesTable.id,  # Direct column reference
            SalesTable.amount * 1.1,  # Column expression
            ibis.ifelse(SalesTable.amount > 100, "premium", "standard").name(
                "tier"
            ),  # ibis.ifelse
            ibis.literal("USD").name("currency"),  # ibis.literal
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result.columns) == 4
    assert "id" in result.columns
    assert "tier" in result.columns
    assert "currency" in result.columns
    assert all(result["currency"] == "USD")
