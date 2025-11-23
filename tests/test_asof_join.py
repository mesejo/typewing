"""Tests for asof_join operations with TypedTable."""

from __future__ import annotations

import ibis
import pytest

from typewing import SemanticModel
from typewing.model import TypedTable


class TickData(SemanticModel):
    """Model for tick data with timestamps."""

    __tablename__ = "ticks"

    time: int  # Unix timestamp
    price: float
    symbol: str


class TradeData(SemanticModel):
    """Model for trade data with timestamps."""

    __tablename__ = "trades"

    time: int  # Unix timestamp
    volume: float
    symbol: str


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create ticks table
    con.raw_sql(
        """
        CREATE TABLE ticks (
            time INTEGER,
            price DOUBLE,
            symbol VARCHAR
        )
        """
    )

    # Insert tick data
    con.raw_sql(
        """
        INSERT INTO ticks VALUES
            (1, 100.0, 'AAPL'),
            (2, 101.0, 'AAPL'),
            (3, 102.0, 'AAPL'),
            (4, 103.0, 'AAPL'),
            (1, 50.0, 'GOOG'),
            (3, 51.0, 'GOOG'),
            (5, 52.0, 'GOOG')
        """
    )

    # Create trades table
    con.raw_sql(
        """
        CREATE TABLE trades (
            time INTEGER,
            volume DOUBLE,
            symbol VARCHAR
        )
        """
    )

    # Insert trade data (happens at times 2 and 4)
    con.raw_sql(
        """
        INSERT INTO trades VALUES
            (2, 100.0, 'AAPL'),
            (4, 200.0, 'AAPL'),
            (2, 50.0, 'GOOG'),
            (4, 75.0, 'GOOG')
        """
    )

    yield con
    con.disconnect()


def test_asof_join_backward_returns_typed_table(duckdb_con):
    """Test that asof_join with backward direction returns TypedTable."""
    TicksTable = TickData.bind(duckdb_con)
    TradesTable = TradeData.bind(duckdb_con)

    # Perform backward asof join (find most recent trade before or at each tick)
    query = TicksTable.asof_join(
        TradesTable, TicksTable.time >= TradesTable.time, "symbol"
    )

    assert isinstance(query, TypedTable)

    # Execute and verify we get results
    result = query.execute()
    assert len(result) > 0


def test_asof_join_forward_returns_typed_table(duckdb_con):
    """Test that asof_join with forward direction returns TypedTable."""
    TicksTable = TickData.bind(duckdb_con)
    TradesTable = TradeData.bind(duckdb_con)

    # Perform forward asof join (find next trade at or after each tick)
    query = TicksTable.asof_join(
        TradesTable, TicksTable.time <= TradesTable.time, "symbol"
    )

    assert isinstance(query, TypedTable)

    # Execute and verify we get results
    result = query.execute()
    assert len(result) > 0


def test_asof_join_without_by_key(duckdb_con):
    """Test asof_join without a by key returns TypedTable."""
    # Create simple tables without symbol grouping
    con = duckdb_con
    con.raw_sql(
        """
        CREATE TABLE simple_left (
            time INTEGER,
            value DOUBLE
        )
        """
    )
    con.raw_sql(
        """
        INSERT INTO simple_left VALUES
            (1, 1.1),
            (2, 2.2),
            (3, 3.3),
            (4, 4.4)
        """
    )

    con.raw_sql(
        """
        CREATE TABLE simple_right (
            time INTEGER,
            other_value DOUBLE
        )
        """
    )
    con.raw_sql(
        """
        INSERT INTO simple_right VALUES
            (2, 1.2),
            (4, 2.0)
        """
    )

    # Bind to a model
    class SimpleLeft(SemanticModel):
        __tablename__ = "simple_left"
        time: int
        value: float

    LeftTable = SimpleLeft.bind(con)
    right = con.table("simple_right")

    # Perform asof join without by key
    query = LeftTable.asof_join(right, LeftTable.time >= right.time)

    assert isinstance(query, TypedTable)

    # Execute and verify we get results
    result = query.execute()
    assert len(result) == 4


def test_asof_join_chained_with_filter(duckdb_con):
    """Test that asof_join can be chained with other operations."""
    TicksTable = TickData.bind(duckdb_con)
    TradesTable = TradeData.bind(duckdb_con)

    # Chain asof_join with filter
    query = (
        TicksTable.asof_join(TradesTable, TicksTable.time >= TradesTable.time, "symbol")
        .filter(TicksTable.price > 100.0)
        .select(TicksTable.time, TicksTable.price, TradesTable.volume)
    )

    assert isinstance(query, TypedTable)

    # Execute and verify we get results
    result = query.execute()
    assert len(result) > 0
    # All prices should be > 100
    assert all(result["price"] > 100.0)


def test_asof_join_result_can_be_executed(duckdb_con):
    """Test that asof_join result can be executed and returns valid data."""
    TicksTable = TickData.bind(duckdb_con)
    TradesTable = TradeData.bind(duckdb_con)

    # Perform asof join
    query = TicksTable.asof_join(
        TradesTable, TicksTable.time >= TradesTable.time, "symbol"
    )

    # Should be able to execute
    result = query.execute()

    # Should have both tick and trade columns
    assert "time" in result.columns
    assert "price" in result.columns
    assert "volume" in result.columns
    assert "symbol" in result.columns
