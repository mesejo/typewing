"""Tests for IbisModel functionality."""

import ibis
import pytest

from typewing import Field, IbisModel


class User(IbisModel):
    """Test model for users table."""

    __tablename__ = "users"

    id: int
    name: str
    email: str
    age: int | None = Field(description="User's age in years")
    is_active: bool = Field(alias="active")


class Product(IbisModel):
    """Test model without explicit tablename (should default to 'product')."""

    product_id: int
    name: str
    price: float


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create users table
    con.raw_sql(
        """
        CREATE TABLE users (
            id INTEGER,
            name VARCHAR,
            email VARCHAR,
            age INTEGER,
            active BOOLEAN
        )
        """
    )

    # Insert test data
    con.raw_sql(
        """
        INSERT INTO users VALUES
            (1, 'Alice', 'alice@example.com', 30, true),
            (2, 'Bob', 'bob@example.com', 25, true),
            (3, 'Charlie', 'charlie@example.com', NULL, false),
            (4, 'Diana', 'diana@example.com', 35, true)
        """
    )

    yield con
    con.disconnect()


# Model Definition Tests


def test_table_name_explicit():
    """Test that explicit __tablename__ is used."""
    assert User.get_table_name() == "users"


def test_table_name_default():
    """Test that table name defaults to lowercase class name."""
    assert Product.get_table_name() == "product"


def test_field_metadata():
    """Test that field metadata is properly stored."""
    fields = User.get_fields()

    assert "id" in fields
    assert "name" in fields
    assert "age" in fields

    assert fields["age"]["description"] == "User's age in years"
    assert fields["is_active"]["alias"] == "active"


def test_field_names():
    """Test getting list of field names."""
    field_names = User.get_field_names()

    assert "id" in field_names
    assert "name" in field_names
    assert "email" in field_names
    assert "age" in field_names
    assert "is_active" in field_names


def test_field_types():
    """Test getting field type mappings."""
    field_types = User.get_field_types()

    assert field_types["id"] is int
    assert field_types["name"] is str
    assert field_types["email"] is str
    # age is Optional[int] which is Union[int, None]
    assert "age" in field_types


def test_column_name_with_alias():
    """Test that field with alias returns correct column name."""
    assert User.get_column_name("is_active") == "active"


def test_column_name_without_alias():
    """Test that field without alias returns field name."""
    assert User.get_column_name("name") == "name"


# Table Binding Tests


def test_bind_returns_typed_table(duckdb_con):
    """Test that bind() returns a TypedTable."""
    UserTable = User.bind(duckdb_con)

    assert UserTable is not None
    assert hasattr(UserTable, "_ibis_table")
    assert hasattr(UserTable, "_model_class")


def test_bound_table_has_ibis_methods(duckdb_con):
    """Test that bound table has all Ibis Table methods."""
    UserTable = User.bind(duckdb_con)

    # Check for common Ibis methods
    assert hasattr(UserTable, "filter")
    assert hasattr(UserTable, "select")
    assert hasattr(UserTable, "limit")
    assert hasattr(UserTable, "order_by")
    assert hasattr(UserTable, "execute")


def test_bound_table_column_access(duckdb_con):
    """Test accessing columns from bound table."""
    UserTable = User.bind(duckdb_con)

    # Should be able to access columns
    name_col = UserTable.name
    assert name_col is not None

    # Column should be an ibis expression
    from ibis.expr.types import Column

    assert isinstance(name_col, Column)


def test_custom_table_name(duckdb_con):
    """Test binding with custom table name."""
    # This would fail with the actual table, but tests the parameter passing
    with pytest.raises(Exception):  # DuckDB will raise an error for non-existent table
        User.bind(duckdb_con, table_name="custom_users")


# Query Building Tests


def test_simple_select(duckdb_con):
    """Test simple select query."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.execute()

    assert result is not None
    assert len(result) == 4


def test_filter_query(duckdb_con):
    """Test filtering query."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(UserTable.age > 28)
    result = query.execute()

    assert len(result) == 2
    assert all(
        row["age"] > 28 for _, row in result.iterrows() if row["age"] is not None
    )


def test_select_specific_columns(duckdb_con):
    """Test selecting specific columns."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.select("name", "email")
    result = query.execute()

    assert len(result.columns) == 2
    assert "name" in result.columns
    assert "email" in result.columns


def test_chained_operations(duckdb_con):
    """Test chaining multiple query operations."""
    UserTable = User.bind(duckdb_con)

    query = (
        UserTable.filter(UserTable.age.notnull())
        .filter(UserTable.age > 25)
        .select("name", "age")
        .order_by("age")
    )

    result = query.execute()

    assert len(result) == 2
    ages = result["age"].tolist()
    assert ages == sorted(ages)  # Should be ordered


def test_limit_query(duckdb_con):
    """Test limiting query results."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.limit(2)
    result = query.execute()

    assert len(result) == 2


def test_order_by(duckdb_con):
    """Test ordering query results."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.order_by(UserTable.name.desc())
    result = query.execute()

    names = result["name"].tolist()
    assert names == sorted(names, reverse=True)


def test_aggregate_operations(duckdb_con):
    """Test aggregate operations."""
    UserTable = User.bind(duckdb_con)

    # Count all users
    count = UserTable.count().execute()
    assert count == 4

    # Count users with age filter
    count_filtered = UserTable.filter(UserTable.age.notnull()).count().execute()
    assert count_filtered == 3


# Column Access Tests


def test_column_access_returns_column(duckdb_con):
    """Test that accessing a field returns an Ibis Column."""
    UserTable = User.bind(duckdb_con)

    from ibis.expr.types import Column

    assert isinstance(UserTable.name, Column)
    assert isinstance(UserTable.age, Column)


def test_column_in_filter(duckdb_con):
    """Test using column references in filters."""
    UserTable = User.bind(duckdb_con)

    # Should be able to use column references in expressions
    query = UserTable.filter(UserTable.age > 25)
    result = query.execute()

    assert len(result) > 0


def test_column_with_alias(duckdb_con):
    """Test accessing column that has an alias."""
    UserTable = User.bind(duckdb_con)

    # is_active maps to 'active' column
    active_col = UserTable.is_active
    assert active_col is not None

    query = UserTable.filter(UserTable.is_active)
    result = query.execute()

    assert len(result) == 3


# Type Safety Tests


def test_model_has_typed_fields():
    """Test that model class has properly typed fields."""
    # This test is mainly for IDE autocomplete - the fields should be accessible
    assert hasattr(User, "id")
    assert hasattr(User, "name")
    assert hasattr(User, "email")
    assert hasattr(User, "age")
    assert hasattr(User, "is_active")


def test_bound_table_preserves_fields(duckdb_con):
    """Test that bound table preserves field access."""
    UserTable = User.bind(duckdb_con)

    # These should all be accessible (IDE autocomplete would show them)
    assert hasattr(UserTable, "id")
    assert hasattr(UserTable, "name")
    assert hasattr(UserTable, "email")
    assert hasattr(UserTable, "age")
    assert hasattr(UserTable, "is_active")


# Edge Cases Tests


def test_empty_result(duckdb_con):
    """Test querying with no results."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(UserTable.age > 100)
    result = query.execute()

    assert len(result) == 0


def test_null_values(duckdb_con):
    """Test handling of NULL values."""
    UserTable = User.bind(duckdb_con)

    # Charlie has NULL age
    query = UserTable.filter(UserTable.name == "Charlie")
    result = query.execute()

    assert len(result) == 1
    row = result.iloc[0]
    assert row["age"] is None or row["age"] != row["age"]  # Check for NULL/NaN


def test_repr(duckdb_con):
    """Test string representation of bound table."""
    UserTable = User.bind(duckdb_con)

    repr_str = repr(UserTable)
    assert "User" in repr_str
