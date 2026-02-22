"""Tests for numeric operations with TypedTable on DuckDB.

Tests common numeric operations like arithmetic, math functions, and comparisons.
"""

from __future__ import annotations

import math

import ibis
import pytest

from typewing import SemanticModel
from typewing.model import TypedTable


class NumericData(SemanticModel):
    """Model for numeric data."""

    __tablename__ = "numbers"

    id: int
    int_val: int
    float_val: float
    small_int: int


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create numbers table
    con.raw_sql(
        """
        CREATE TABLE numbers (
            id INTEGER,
            int_val INTEGER,
            float_val DOUBLE,
            small_int SMALLINT
        )
        """
    )

    # Insert test data
    con.raw_sql(
        """
        INSERT INTO numbers VALUES
            (1, 10, 3.14, 2),
            (2, -5, 2.71, 3),
            (3, 0, 1.41, 1),
            (4, 100, -2.5, 4),
            (5, 42, 0.0, 5),
            (6, -10, 5.5, 2),
            (7, 7, -1.0, 1),
            (8, 99, 10.5, 3)
        """
    )

    yield con
    con.disconnect()


def test_arithmetic_add_subtract(duckdb_con):
    """Test addition and subtraction operations."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            (NumTable.int_val + 10).name("added"),
            (NumTable.int_val - 5).name("subtracted"),
            (NumTable.int_val + NumTable.small_int).name("col_add"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["added"] == 20  # 10 + 10
    assert row["subtracted"] == 5  # 10 - 5
    assert row["col_add"] == 12  # 10 + 2


def test_arithmetic_multiply_divide(duckdb_con):
    """Test multiplication and division operations."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            (NumTable.int_val * 2).name("multiplied"),
            (NumTable.int_val / 2).name("divided"),
            (NumTable.int_val * NumTable.small_int).name("col_multiply"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["multiplied"] == 20
    assert row["divided"] == 5.0
    assert row["col_multiply"] == 20


def test_arithmetic_modulo_floor_div(duckdb_con):
    """Test modulo and floor division."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            (NumTable.int_val % 3).name("modulo"),
            (NumTable.int_val // 3).name("floor_div"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["modulo"] == 1  # 10 % 3
    assert row["floor_div"] == 3  # 10 // 3


def test_math_abs_sign(duckdb_con):
    """Test abs() and sign() functions."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            NumTable.int_val.abs().name("absolute"),
            NumTable.int_val.sign().name("sign_val"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    # Check negative number
    row_neg = result[result["id"] == 2].iloc[0]
    assert row_neg["absolute"] == 5  # abs(-5)
    assert row_neg["sign_val"] == -1

    # Check zero
    row_zero = result[result["id"] == 3].iloc[0]
    assert row_zero["sign_val"] == 0


def test_math_round_ceil_floor(duckdb_con):
    """Test round(), ceil(), and floor() functions."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            NumTable.float_val.round().name("rounded"),
            NumTable.float_val.round(1).name("rounded_1"),
            NumTable.float_val.ceil().name("ceiling"),
            NumTable.float_val.floor().name("floored"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["rounded"] == 3.0  # round(3.14)
    assert row["rounded_1"] == 3.1  # round(3.14, 1)
    assert row["ceiling"] == 4  # ceil(3.14)
    assert row["floored"] == 3  # floor(3.14)


def test_math_sqrt_exp(duckdb_con):
    """Test sqrt() and exp() functions."""
    NumTable = NumericData.bind(duckdb_con)

    # Test with positive values
    query = NumTable.select(
        [
            NumTable.id,
            NumTable.float_val.sqrt().name("square_root"),
            ibis.literal(2.0).exp().name("exponential"),
        ]
    ).filter(NumTable.id == 3)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert abs(row["square_root"] - math.sqrt(1.41)) < 0.001
    assert abs(row["exponential"] - math.exp(2.0)) < 0.001


def test_math_log_functions(duckdb_con):
    """Test logarithm functions."""
    NumTable = NumericData.bind(duckdb_con)

    # Use positive float values for logarithms
    query = NumTable.select(
        [
            NumTable.id,
            NumTable.float_val.ln().name("natural_log"),
            NumTable.float_val.log10().name("log_base_10"),
            NumTable.float_val.log2().name("log_base_2"),
            NumTable.float_val.log(5).name("log_base_5"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert abs(row["natural_log"] - math.log(3.14)) < 0.001
    assert abs(row["log_base_10"] - math.log10(3.14)) < 0.001
    assert abs(row["log_base_2"] - math.log2(3.14)) < 0.001
    assert abs(row["log_base_5"] - math.log(3.14) / math.log(5)) < 0.001


def test_math_power(duckdb_con):
    """Test power operation."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [NumTable.id, (NumTable.small_int**2).name("squared")]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["squared"] == 4  # 2^2


def test_trig_functions(duckdb_con):
    """Test trigonometric functions."""
    NumTable = NumericData.bind(duckdb_con)

    # Use 0 for simpler verification
    query = NumTable.select(
        [
            NumTable.id,
            ibis.literal(0.0).sin().name("sine"),
            ibis.literal(0.0).cos().name("cosine"),
            ibis.literal(0.0).tan().name("tangent"),
            ibis.literal(0.0).asin().name("arcsine"),
            ibis.literal(0.0).acos().name("arccosine"),
            ibis.literal(0.0).atan().name("arctangent"),
        ]
    ).limit(1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert abs(row["sine"] - 0.0) < 0.001
    assert abs(row["cosine"] - 1.0) < 0.001
    assert abs(row["tangent"] - 0.0) < 0.001
    assert abs(row["arcsine"] - 0.0) < 0.001
    assert abs(row["arccosine"] - math.pi / 2) < 0.001
    assert abs(row["arctangent"] - 0.0) < 0.001


def test_angle_conversion(duckdb_con):
    """Test radians() and degrees() functions."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            ibis.literal(180.0).radians().name("to_radians"),
            ibis.literal(math.pi).degrees().name("to_degrees"),
        ]
    ).limit(1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert abs(row["to_radians"] - math.pi) < 0.001
    assert abs(row["to_degrees"] - 180.0) < 0.001


def test_least_greatest(duckdb_con):
    """Test least() and greatest() functions."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            ibis.least(NumTable.int_val, NumTable.small_int).name("minimum"),
            ibis.greatest(NumTable.int_val, NumTable.small_int).name("maximum"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["minimum"] == 2  # min(10, 2)
    assert row["maximum"] == 10  # max(10, 2)


def test_constants(duckdb_con):
    """Test mathematical constants."""
    # Test pi and e
    expr_pi = ibis.pi
    result_pi = duckdb_con.execute(expr_pi)
    assert abs(result_pi - math.pi) < 0.001

    expr_e = ibis.e
    result_e = duckdb_con.execute(expr_e)
    assert abs(result_e - math.e) < 0.001


def test_numeric_with_mutate(duckdb_con):
    """Test numeric operations with mutate."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.mutate(
        doubled=NumTable.int_val * 2,
        absolute=NumTable.int_val.abs(),
        is_positive=NumTable.int_val > 0,
    ).filter(NumTable.id == 2)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["doubled"] == -10  # -5 * 2
    assert row["absolute"] == 5  # abs(-5)
    assert not row["is_positive"]  # -5 > 0 is False


def test_numeric_chained_operations(duckdb_con):
    """Test chaining multiple numeric operations."""
    NumTable = NumericData.bind(duckdb_con)

    # Chain operations: filter, add, round, multiply
    query = (
        NumTable.filter(NumTable.int_val > 0)
        .select(
            [
                NumTable.id,
                ((NumTable.float_val + 1.0).round() * 2).name("result"),
            ]
        )
        .filter(lambda t: t.result > 5)
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) > 0


def test_comparison_operators(duckdb_con):
    """Test comparison operators."""
    NumTable = NumericData.bind(duckdb_con)

    # Test various comparisons
    query_gt = NumTable.filter(NumTable.int_val > 50)
    assert isinstance(query_gt, TypedTable)
    assert len(query_gt.execute()) == 2  # 100 and 99

    query_lt = NumTable.filter(NumTable.int_val < 0)
    assert isinstance(query_lt, TypedTable)
    assert len(query_lt.execute()) == 2  # -5 and -10

    query_eq = NumTable.filter(NumTable.int_val == 0)
    assert isinstance(query_eq, TypedTable)
    assert len(query_eq.execute()) == 1


def test_bitwise_operations(duckdb_con):
    """Test bitwise operations."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            (NumTable.int_val & 3).name("bitwise_and"),
            (NumTable.int_val | 3).name("bitwise_or"),
            (NumTable.int_val ^ 3).name("bitwise_xor"),
            (~NumTable.int_val).name("bitwise_not"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["bitwise_and"] == 10 & 3
    assert row["bitwise_or"] == 10 | 3
    assert row["bitwise_xor"] == 10 ^ 3
    assert row["bitwise_not"] == ~10


def test_bitwise_shift(duckdb_con):
    """Test bitwise shift operations."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            (NumTable.small_int << 1).name("left_shift"),
            (NumTable.small_int >> 1).name("right_shift"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["left_shift"] == 2 << 1  # 4
    assert row["right_shift"] == 2 >> 1  # 1


def test_null_arithmetic(duckdb_con):
    """Test arithmetic with null values."""
    NumTable = NumericData.bind(duckdb_con)

    # Use nullif to create null values
    query = NumTable.select(
        [
            NumTable.id,
            NumTable.int_val.nullif(0).name("nullable"),
            (NumTable.int_val.nullif(0) + 5).name("null_plus_five"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    # Row with int_val = 0 should have null
    row_zero = result[result["id"] == 3].iloc[0]
    assert row_zero["nullable"] is None or (
        hasattr(row_zero["nullable"], "__float__")
        and row_zero["nullable"] != row_zero["nullable"]
    )


def test_aggregate_with_numeric(duckdb_con):
    """Test aggregation with numeric columns."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.aggregate(
        [
            NumTable.int_val.sum().name("total"),
            NumTable.int_val.mean().name("average"),
            NumTable.int_val.min().name("minimum"),
            NumTable.int_val.max().name("maximum"),
            NumTable.count().name("row_count"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    # Sum: 10 + (-5) + 0 + 100 + 42 + (-10) + 7 + 99 = 243
    assert row["total"] == 243
    assert row["minimum"] == -10
    assert row["maximum"] == 100
    assert row["row_count"] == 8


def test_numeric_literals(duckdb_con):
    """Test numeric operations on literals."""
    # Integer operations
    expr1 = ibis.literal(10) + ibis.literal(5)
    assert duckdb_con.execute(expr1) == 15

    # Float operations
    expr2 = ibis.literal(3.14).round(1)
    assert duckdb_con.execute(expr2) == 3.1

    # Math function on literal
    expr3 = ibis.literal(16).sqrt()
    assert duckdb_con.execute(expr3) == 4.0


def test_mixed_type_arithmetic(duckdb_con):
    """Test arithmetic with mixed integer and float types."""
    NumTable = NumericData.bind(duckdb_con)

    query = NumTable.select(
        [
            NumTable.id,
            (NumTable.int_val + NumTable.float_val).name("int_plus_float"),
            (NumTable.int_val * NumTable.float_val).name("int_times_float"),
        ]
    ).filter(NumTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert abs(row["int_plus_float"] - 13.14) < 0.001  # 10 + 3.14
    assert abs(row["int_times_float"] - 31.4) < 0.001  # 10 * 3.14
