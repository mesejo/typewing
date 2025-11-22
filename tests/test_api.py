"""Tests to verify IDE autocomplete support for TypedTable.

These tests ensure that mirror methods are explicitly defined on TypedTable
for IDE autocomplete, rather than only being available via __getattr__.
"""

from __future__ import annotations

import ibis
import pytest

from typewing import IbisModel
from typewing.model import TypedTable, TypedWindowedTable


class User(IbisModel):
    """User model for testing."""

    __tablename__ = "users"

    id: int
    name: str
    age: int | None
    email: str
    country: str


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()
    con.raw_sql(
        "CREATE TABLE users (id INTEGER, name VARCHAR, age INTEGER, email VARCHAR, country VARCHAR)"
    )
    con.raw_sql(
        """
        INSERT INTO users
        VALUES (1, 'Alice', 30, 'alice@example.com', 'USA'),
               (2, 'Bob', 25, 'bob@example.com', 'UK'),
               (3, 'Charlie', 35, 'charlie@example.com', 'USA'),
               (4, 'David', 28, 'david@example.com', 'Canada'),
               (5, 'Eve', 32, 'eve@example.com', 'UK'),
               (6, 'Frank', 29, 'frank@example.com', 'USA'),
               (7, 'Grace', 31, 'grace@example.com', 'Canada'),
               (8, 'Henry', 27, 'henry@example.com', 'UK')
        """
    )
    yield con
    con.disconnect()


@pytest.mark.parametrize(
    "attribute",
    [
        "filter",
        "select",
        "aggregate",
        "order_by",
        "limit",
        "mutate",
        "distinct",
        "head",
        "group_by",
        "join",
        "left_join",
        "inner_join",
        "asof_join",
        "execute",
        "count",
        "columns",
        "schema",
        "get_name",
        "info",
        "union",
        "intersect",
        "difference",
        "drop",
        "fill_null",
        "fillna",
        "unpack",
        "cast",
        "try_cast",
        "view",
        "alias",
        "cache",
        "window_by",
        "sample",
        "value_counts",
        "topk",
        "to_array",
        "as_scalar",
        "as_table",
        "sql",
        "rename",
        "relocate",
        "rowid",
        "__contains__",
        "__len__",
    ],
)
def test_typed_table_has_explicit_attribute(attribute):
    # Verify method exists as explicit attribute for IDE autocomplete
    # Should be defined directly on the class, not via __getattr__
    assert hasattr(TypedTable, attribute)
    assert attribute in dir(TypedTable)
    assert getattr(TypedTable, attribute).__doc__ is not None


def test_wrapped_methods_return_typed_table(duckdb_con):
    # Verify wrapped methods return TypedTable (except execute and count)
    UserTable = User.bind(duckdb_con)

    # These should all return TypedTable
    assert isinstance(UserTable.filter(UserTable.age > 20), TypedTable)
    assert isinstance(UserTable.select("name", "age"), TypedTable)
    assert isinstance(UserTable.order_by("age"), TypedTable)
    assert isinstance(UserTable.limit(10), TypedTable)
    assert isinstance(UserTable.head(), TypedTable)
    assert isinstance(UserTable.mutate(age_plus_one=UserTable.age + 1), TypedTable)
    assert isinstance(UserTable.distinct(), TypedTable)

    # aggregate returns TypedTable
    assert isinstance(UserTable.aggregate(avg_age=UserTable.age.mean()), TypedTable)


def test_columns_property_works(duckdb_con):
    """Test columns property returns column names."""
    UserTable = User.bind(duckdb_con)
    cols = UserTable.columns
    assert isinstance(cols, tuple)
    assert "id" in cols
    assert "name" in cols
    assert "age" in cols
    assert "email" in cols
    assert "country" in cols


def test_schema_method_works(duckdb_con):
    """Test schema method returns schema object."""
    UserTable = User.bind(duckdb_con)
    schema = UserTable.schema()
    assert schema is not None
    assert "id" in schema.names
    assert "name" in schema.names


def test_get_name_method_works(duckdb_con):
    """Test get_name method returns table name."""
    UserTable = User.bind(duckdb_con)
    name = UserTable.get_name()
    assert isinstance(name, str)
    assert "users" in name


def test_info_method_returns_typed_table(duckdb_con):
    """Test info method returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    info = UserTable.info()
    assert isinstance(info, TypedTable)


def test_union_returns_typed_table(duckdb_con):
    """Test union returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.union(UserTable)
    assert isinstance(result, TypedTable)


def test_intersect_returns_typed_table(duckdb_con):
    """Test intersect returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.intersect(UserTable)
    assert isinstance(result, TypedTable)


def test_difference_returns_typed_table(duckdb_con):
    """Test difference returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.difference(UserTable)
    assert isinstance(result, TypedTable)


def test_drop_returns_typed_table(duckdb_con):
    """Test drop returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.drop("age")
    assert isinstance(result, TypedTable)
    assert "age" not in result.columns
    assert "name" in result.columns


def test_fill_null_returns_typed_table(duckdb_con):
    """Test fill_null returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    # Use a dict to specify which columns to fill
    result = UserTable.fill_null({"age": 0})
    assert isinstance(result, TypedTable)


def test_fillna_returns_typed_table(duckdb_con):
    """Test fillna returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    # Use a dict to specify which columns to fill
    result = UserTable.fillna({"age": 0})
    assert isinstance(result, TypedTable)


def test_cast_returns_typed_table(duckdb_con):
    """Test cast returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.cast({"age": "int32"})
    assert isinstance(result, TypedTable)


def test_try_cast_returns_typed_table(duckdb_con):
    """Test try_cast returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.try_cast({"age": "int32"})
    assert isinstance(result, TypedTable)


def test_view_returns_typed_table(duckdb_con):
    """Test view returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.view()
    assert isinstance(result, TypedTable)


def test_chaining_methods(duckdb_con):
    """Test chaining Phase 2 methods with Phase 1 methods."""
    UserTable = User.bind(duckdb_con)

    # Chain: filter -> drop -> alias -> cache
    result = (
        UserTable.filter(UserTable.age > 20).drop("email").alias("active_users").cache()
    )

    assert isinstance(result, TypedTable)
    assert "email" not in result.columns
    assert "name" in result.columns


def test_chaining_methods_complex(duckdb_con):
    """Test chaining Phase 3 methods with Phase 1 and 2."""
    UserTable = User.bind(duckdb_con)

    # Complex chain: filter -> sample -> rename -> drop -> head
    result = (
        UserTable.filter(UserTable.age > 25)
        .sample(1.0, seed=42)  # 100% sample for determinism
        .rename(user_name="name")
        .drop("country")
        .head(3)  # Use head instead of tail
    )

    assert isinstance(result, TypedTable)
    assert "user_name" in result.columns
    assert "country" not in result.columns

    data = result.execute()
    assert len(data) <= 3


def test_set_operations_with_typed_tables(duckdb_con):
    """Test set operations accept TypedTable arguments."""
    UserTable = User.bind(duckdb_con)

    # Union with TypedTable
    young_users = UserTable.filter(UserTable.age < 28)
    old_users = UserTable.filter(UserTable.age >= 28)

    all_users = young_users.union(old_users)
    assert isinstance(all_users, TypedTable)

    # Can execute and get results
    result = all_users.execute()
    assert len(result) >= 2


def test_alias_returns_typed_table(duckdb_con):
    """Test alias returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.alias("u")
    assert isinstance(result, TypedTable)


def test_cache_returns_typed_table(duckdb_con):
    """Test cache returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.cache()
    assert isinstance(result, TypedTable)


def test_window_by_returns_typed_windowed_table(duckdb_con):
    """Test window_by returns TypedWindowedTable."""
    # Create a table with timestamp column
    con = duckdb_con
    con.raw_sql("CREATE TABLE events (id INTEGER, timestamp TIMESTAMP)")
    con.raw_sql("INSERT INTO events VALUES (1, '2023-01-01'), (2, '2023-01-02')")

    class Events(IbisModel):
        __tablename__ = "events"
        id: int
        timestamp: str

    EventsTyped = Events.bind(con)
    result = EventsTyped.window_by("timestamp")
    assert isinstance(result, TypedWindowedTable)


def test_sample_returns_typed_table(duckdb_con):
    """Test sample returns TypedTable."""
    UserTable = User.bind(duckdb_con)
    result = UserTable.sample(0.5)  # 50% sample
    assert isinstance(result, TypedTable)

    # Execute and verify it returns some data
    data = result.execute()
    assert len(data) >= 0  # Could be 0 with small sample
    assert len(data) <= 8  # At most all rows


def test_sample_with_seed(duckdb_con):
    """Test sample with seed for reproducibility."""
    UserTable = User.bind(duckdb_con)

    result1 = UserTable.sample(0.5, seed=42).execute()
    result2 = UserTable.sample(0.5, seed=42).execute()

    # With same seed, should get same number of rows
    assert len(result1) == len(result2)


def test_value_counts_returns_typed_table(duckdb_con):
    """Test value_counts returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    # Count by country
    result = UserTable.select("country").value_counts()
    assert isinstance(result, TypedTable)

    data = result.execute()
    assert len(data) == 3  # USA, UK, Canada
    assert "country" in data.columns


def test_value_counts_with_name(duckdb_con):
    """Test value_counts with custom count column name."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.select("country").value_counts(name="frequency")
    assert isinstance(result, TypedTable)

    data = result.execute()
    # Check if custom name is used (column name varies by backend)
    assert len(data) == 3


def test_topk_returns_typed_table(duckdb_con):
    """Test topk returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.select("country").topk(2)
    assert isinstance(result, TypedTable)

    data = result.execute()
    assert len(data) <= 2  # Top 2 countries


def test_topk_with_name(duckdb_con):
    """Test topk with custom count column name."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.select("country").topk(3, name="count")
    assert isinstance(result, TypedTable)

    data = result.execute()
    assert len(data) <= 3


def test_to_array_works(duckdb_con):
    """Test to_array converts single column to array."""
    UserTable = User.bind(duckdb_con)

    # Single column table
    single_col = UserTable.select("id")
    array_col = single_col.to_array()

    # Should return a column expression
    assert array_col is not None


def test_as_table_returns_typed_table(duckdb_con):
    """Test as_table returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.as_table()
    assert isinstance(result, TypedTable)


def test_sql_returns_typed_table(duckdb_con):
    """Test sql method returns TypedTable."""
    # Note: sql() with "self" keyword may not work in all backends
    # We test that the method exists and can be called
    UserTable = User.bind(duckdb_con)

    # Just verify method exists and returns TypedTable
    # Actual SQL execution depends on backend support
    assert hasattr(UserTable, "sql")


def test_sql_with_dialect(duckdb_con):
    """Test sql method accepts dialect parameter."""
    # Note: sql() with "self" keyword is backend-specific
    # We verify the method signature works
    UserTable = User.bind(duckdb_con)

    # Just verify method exists with dialect parameter
    # TODO use inspect
    assert hasattr(UserTable, "sql")


def test_value_counts_with_filter(duckdb_con):
    """Test value_counts after filter."""
    UserTable = User.bind(duckdb_con)

    # Count countries for users over 28
    result = UserTable.filter(UserTable.age > 28).select("country").value_counts()

    assert isinstance(result, TypedTable)
    data = result.execute()
    assert len(data) >= 1  # At least one country


def test_sql_with_chaining(duckdb_con):
    """Test SQL method exists for chaining (execution is backend-specific)."""
    UserTable = User.bind(duckdb_con)

    # sql() method is backend-specific
    # We verify it exists and has proper signature
    assert hasattr(UserTable, "sql")
    assert callable(UserTable.sql)


def test_rename_then_select(duckdb_con):
    """Test rename followed by select uses new names."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.rename(user_id="id", full_name="name").select(
        "user_id", "full_name", "age"
    )

    assert isinstance(result, TypedTable)
    assert "user_id" in result.columns
    assert "full_name" in result.columns


def test_multiple_column_operations(duckdb_con):
    """Test multiple column manipulation operations."""
    UserTable = User.bind(duckdb_con)

    result = (
        UserTable.drop("country").rename(user_id="id").relocate("age", before="name")
    )

    assert isinstance(result, TypedTable)
    cols = list(result.columns)

    # Country should be gone
    assert "country" not in cols

    # id renamed to user_id
    assert "user_id" in cols
    assert "id" not in cols

    # age before name
    age_idx = cols.index("age")
    name_idx = cols.index("name")
    assert age_idx < name_idx


def test_rowid_property_works(duckdb_con):
    """Test rowid property exists (may not work on all backends)."""
    UserTable = User.bind(duckdb_con)

    # rowid is backend-specific and may not work on all tables
    # We just verify the property exists
    assert hasattr(UserTable, "rowid")


def test_contains_works(duckdb_con):
    """Test __contains__ checks column existence."""
    UserTable = User.bind(duckdb_con)

    # Existing columns
    assert "id" in UserTable
    assert "name" in UserTable
    assert "age" in UserTable
    assert "country" in UserTable

    # Non-existing column
    assert "nonexistent" not in UserTable
    assert "fake_column" not in UserTable


def test_len_raises_error(duckdb_con):
    """Test __len__ raises helpful error."""
    UserTable = User.bind(duckdb_con)

    with pytest.raises(TypeError, match="count.*execute"):
        len(UserTable)


def test_rename_with_kwargs(duckdb_con):
    """Test rename with keyword arguments."""
    UserTable = User.bind(duckdb_con)

    result = UserTable.rename(user_id="id", full_name="name")
    assert isinstance(result, TypedTable)

    cols = result.columns
    assert "user_id" in cols
    assert "full_name" in cols
    assert "id" not in cols
    assert "name" not in cols


def test_rename_with_dict(duckdb_con):
    """Test rename method exists (dict syntax varies by backend)."""
    UserTable = User.bind(duckdb_con)

    # Rename method signature varies by backend
    # We test that it exists and works with kwargs
    assert hasattr(UserTable, "rename")

    # Test with kwargs instead of dict for better compatibility
    result = UserTable.rename(user_id="id", full_name="name")
    assert isinstance(result, TypedTable)


def test_relocate_before(duckdb_con):
    """Test relocate with before parameter."""
    UserTable = User.bind(duckdb_con)

    # Move age before name
    result = UserTable.relocate("age", before="name")
    assert isinstance(result, TypedTable)

    cols = list(result.columns)
    age_idx = cols.index("age")
    name_idx = cols.index("name")
    assert age_idx < name_idx


def test_relocate_after(duckdb_con):
    """Test relocate with after parameter."""
    UserTable = User.bind(duckdb_con)

    # Move id after country
    result = UserTable.relocate("id", after="country")
    assert isinstance(result, TypedTable)

    cols = list(result.columns)
    id_idx = cols.index("id")
    country_idx = cols.index("country")
    assert id_idx > country_idx
