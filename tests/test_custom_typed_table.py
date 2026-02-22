"""Tests for custom model operations."""

import ibis
import pytest

from typewing import SemanticModel


class UserWithCustomOps(SemanticModel):
    """Test model with custom operations."""

    __tablename__ = "users"

    id: int
    name: str
    age: int | None

    def adults_only(self):
        """Filter for users 18 and older."""
        return self.filter(self.age >= 18)

    def by_name(self, name: str):
        """Filter by exact name match."""
        return self.filter(self.name == name)

    def age_group(self):
        """Add age_group column."""
        import ibis

        return self.mutate(
            age_group=ibis.ifelse(
                self.age < 18,
                "minor",
                ibis.ifelse(self.age < 65, "adult", "senior"),
            )
        )


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
            age INTEGER
        )
        """
    )

    # Insert test data
    con.raw_sql(
        """
        INSERT INTO users VALUES
            (1, 'Alice', 30),
            (2, 'Bob', 17),
            (3, 'Charlie', 45),
            (4, 'Diana', 16),
            (5, 'Eve', 70)
        """
    )

    yield con
    con.disconnect()


def test_custom_model_instance_created(duckdb_con):
    """Test that binding creates a model instance with custom methods."""
    UserTable = UserWithCustomOps.bind(duckdb_con)

    # Should have custom methods
    assert hasattr(UserTable, "adults_only")
    assert hasattr(UserTable, "by_name")
    assert hasattr(UserTable, "age_group")


def test_custom_operation_adults_only(duckdb_con):
    """Test the adults_only custom operation."""
    UserTable = UserWithCustomOps.bind(duckdb_con)

    result = UserTable.adults_only().execute()

    assert len(result) == 3
    assert all(row["age"] >= 18 for _, row in result.iterrows())


def test_custom_operation_by_name(duckdb_con):
    """Test the by_name custom operation."""
    UserTable = UserWithCustomOps.bind(duckdb_con)

    result = UserTable.by_name("Alice").execute()

    assert len(result) == 1
    assert result.iloc[0]["name"] == "Alice"


def test_custom_operation_age_group(duckdb_con):
    """Test the age_group custom operation."""
    UserTable = UserWithCustomOps.bind(duckdb_con)

    result = UserTable.age_group().execute()

    assert "age_group" in result.columns
    assert result[result["name"] == "Bob"].iloc[0]["age_group"] == "minor"
    assert result[result["name"] == "Alice"].iloc[0]["age_group"] == "adult"
    assert result[result["name"] == "Eve"].iloc[0]["age_group"] == "senior"


def test_chaining_custom_and_standard_ops(duckdb_con):
    """Test chaining custom operations with standard ibis operations."""
    UserTable = UserWithCustomOps.bind(duckdb_con)

    result = (
        UserTable.adults_only()
        .age_group()
        .select("name", "age", "age_group")
        .order_by("age")
        .execute()
    )

    assert len(result) == 3
    assert "age_group" in result.columns
    assert all(row["age"] >= 18 for _, row in result.iterrows())


def test_custom_ops_preserve_through_operations(duckdb_con):
    """Test that custom operations are preserved after standard operations."""
    UserTable = UserWithCustomOps.bind(duckdb_con)

    # Apply standard operation
    filtered = UserTable.filter(UserTable.age > 20)

    # Custom operations should still be available
    assert hasattr(filtered, "adults_only")
    assert hasattr(filtered, "by_name")
    assert hasattr(filtered, "age_group")

    # And they should work
    result = filtered.adults_only().execute()
    assert len(result) == 3


def test_model_without_custom_table(duckdb_con):
    """Test that models without custom TypedTable still work."""

    class SimpleUser(SemanticModel):
        """Model without custom operations."""

        __tablename__ = "users"

        id: int
        name: str
        age: int | None

    SimpleUserTable = SimpleUser.bind(duckdb_con)

    # Should not have custom operations
    assert not hasattr(SimpleUserTable, "adults_only")

    # But standard operations should work
    result = SimpleUserTable.filter(SimpleUserTable.age > 20).execute()
    assert len(result) == 3
