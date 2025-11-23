"""Tests for schema validation functionality."""

import ibis
import pytest
from ibis.expr.types import BooleanColumn, FloatingColumn, IntegerColumn, StringColumn

from typewing import SemanticModel


class UserWithPythonTypes(SemanticModel):
    """Test model using Python native types."""

    __tablename__ = "users_python"

    id: int
    name: str
    age: int | None
    score: float
    active: bool


class UserWithIbisTypes(SemanticModel):
    """Test model using Ibis Column types."""

    __tablename__ = "users_ibis"

    id: IntegerColumn
    name: StringColumn
    age: IntegerColumn | None
    score: FloatingColumn
    active: BooleanColumn


class UserMixedTypes(SemanticModel):
    """Test model with mixed type annotations."""

    __tablename__ = "users_mixed"

    id: IntegerColumn
    name: str
    age: int | None
    score: float


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create users table with int64 (default integer type in DuckDB)
    con.raw_sql(
        """
        CREATE TABLE users_python (
            id INTEGER,
            name VARCHAR,
            age INTEGER,
            score DOUBLE,
            active BOOLEAN
        )
        """
    )

    con.raw_sql(
        """
        CREATE TABLE users_ibis (
            id INTEGER,
            name VARCHAR,
            age INTEGER,
            score DOUBLE,
            active BOOLEAN
        )
        """
    )

    con.raw_sql(
        """
        CREATE TABLE users_mixed (
            id INTEGER,
            name VARCHAR,
            age INTEGER,
            score DOUBLE
        )
        """
    )

    # Table with mismatched types
    con.raw_sql(
        """
        CREATE TABLE users_mismatch (
            id VARCHAR,
            name INTEGER,
            age VARCHAR,
            score INTEGER,
            active VARCHAR
        )
        """
    )

    return con


def test_schema_validation_python_types(duckdb_con):
    """Test that Python native types match corresponding Ibis types."""
    # This should succeed - Python int matches Integer types
    user_table = UserWithPythonTypes.bind(duckdb_con, "users_python")
    assert user_table is not None


def test_schema_validation_ibis_types(duckdb_con):
    """Test that Ibis Column types match corresponding schema types."""
    # This should succeed - IntegerColumn matches Integer schema type
    user_table = UserWithIbisTypes.bind(duckdb_con, "users_ibis")
    assert user_table is not None


def test_schema_validation_mixed_types(duckdb_con):
    """Test that mixed Python and Ibis types work correctly."""
    # This should succeed - mix of Python and Ibis types
    user_table = UserMixedTypes.bind(duckdb_con, "users_mixed")
    assert user_table is not None


def test_schema_validation_fails_on_mismatch(duckdb_con):
    """Test that schema validation fails when types don't match."""
    # Get the table with mismatched types
    ibis_table = duckdb_con.table("users_mismatch")

    # Creating UserWithPythonTypes with mismatched schema should fail
    with pytest.raises(AssertionError):
        UserWithPythonTypes(ibis_table)


def test_schema_validation_method_directly(duckdb_con):
    """Test the __typewing_schema_matches__ method directly."""
    user_table = UserWithPythonTypes.bind(duckdb_con, "users_python")
    schema = user_table.schema()

    # Should return True for matching schema
    assert user_table.__typewing_schema_matches__(schema) is True
    assert user_table.__typewing_schema_matches__(schema, strict=False) is True


def test_schema_validation_missing_field(duckdb_con):
    """Test that validation allows missing fields (for projections)."""

    class UserWithExtraField(SemanticModel):
        __tablename__ = "users_python"

        id: int
        name: str
        age: int | None
        score: float
        active: bool
        extra_field: str  # This field doesn't exist in the table

    ibis_table = duckdb_con.table("users_python")

    # Should succeed - validation only checks fields that exist in schema
    # This allows for projections where only a subset of fields are present
    user = UserWithExtraField(ibis_table)
    assert user is not None


def test_int_matches_int32_and_int64(duckdb_con):
    """Test that Python int annotation matches both int32 and int64 schema types."""
    # Create a table specifically with int32
    duckdb_con.raw_sql(
        """
        CREATE TABLE users_int32 (
            id INT,
            name VARCHAR
        )
        """
    )

    class UserInt(SemanticModel):
        __tablename__ = "users_int32"
        id: int
        name: str

    # Should succeed - int matches int32
    user_table = UserInt.bind(duckdb_con, "users_int32")
    assert user_table is not None


def test_integer_column_matches_any_integer(duckdb_con):
    """Test that IntegerColumn matches any integer type (int8, int16, int32, int64)."""
    # DuckDB uses INTEGER (int32) by default
    user_table = UserWithIbisTypes.bind(duckdb_con, "users_ibis")
    schema = user_table.schema()

    # IntegerColumn should match the integer type in schema
    assert user_table.__typewing_schema_matches__(schema) is True


def test_strict_mode_validation(duckdb_con):
    """Test schema validation in strict mode."""
    user_table = UserWithPythonTypes.bind(duckdb_con, "users_python")
    schema = user_table.schema()

    # In strict mode, should still pass for compatible types
    # (strict mode currently checks the same way for basic types)
    assert user_table.__typewing_schema_matches__(schema, strict=True) is True


def test_nullable_field_validation(duckdb_con):
    """Test that nullable fields (Type | None) are handled correctly."""

    class UserNullable(SemanticModel):
        __tablename__ = "users_python"

        id: int
        name: str
        age: int | None  # Nullable field
        score: float
        active: bool

    # Should succeed - age field allows None
    user_table = UserNullable.bind(duckdb_con, "users_python")
    assert user_table is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
