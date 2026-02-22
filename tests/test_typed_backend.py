"""Tests for TypedBackend wrapper."""

import ibis
import pytest

from typewing import SemanticModel, TypedBackend
from typewing.model import TypedTable


class User(SemanticModel):
    """Test model for users table."""

    __tablename__ = "users"

    id: int
    name: str
    age: int | None


class Product(SemanticModel):
    """Test model for products table."""

    __tablename__ = "products"

    id: int
    name: str
    price: float


@pytest.fixture
def duckdb_raw_con():
    """Create a raw DuckDB connection with test data."""
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
            (2, 'Bob', 25),
            (3, 'Charlie', 35)
        """
    )

    # Create products table
    con.raw_sql(
        """
        CREATE TABLE products (
            id INTEGER,
            name VARCHAR,
            price DOUBLE
        )
        """
    )

    con.raw_sql(
        """
        INSERT INTO products VALUES
            (1, 'Widget', 9.99),
            (2, 'Gadget', 19.99)
        """
    )

    yield con
    con.disconnect()


@pytest.fixture
def typed_backend(duckdb_raw_con):
    """Create a TypedBackend wrapping the raw connection."""
    return TypedBackend(duckdb_raw_con)


# Basic Initialization Tests


def test_typed_backend_creation(duckdb_raw_con):
    """Test creating a TypedBackend."""
    backend = TypedBackend(duckdb_raw_con)
    assert backend is not None
    assert hasattr(backend, "_backend")
    assert backend._backend is duckdb_raw_con


def test_typed_backend_repr(typed_backend):
    """Test TypedBackend string representation."""
    repr_str = repr(typed_backend)
    assert "TypedBackend" in repr_str


# Table Method Tests


def test_table_with_explicit_model(typed_backend):
    """Test getting a table with an explicit model."""
    UserTable = typed_backend.table("users", model=User)

    assert isinstance(UserTable, TypedTable)


def test_table_returns_typed_table(typed_backend):
    """Test that table() returns a TypedTable."""
    UserTable = typed_backend.table("users", model=User)

    # Should be able to use it like a TypedTable
    result = UserTable.filter(UserTable.age > 25).execute()
    assert len(result) == 2


def test_table_without_model(typed_backend):
    """Test getting a table without a model."""
    table = typed_backend.table("users")

    # Should still return a TypedTable (with minimal model)
    assert isinstance(table, TypedTable)


# Model Registry Tests


def test_register_model(typed_backend):
    """Test registering a model."""
    typed_backend.register_model(User)

    # Model should be in registry
    assert "users" in typed_backend._model_registry
    assert typed_backend._model_registry["users"] == User


def test_register_model_with_custom_name(typed_backend):
    """Test registering a model with a custom table name."""
    typed_backend.register_model(User, "custom_users")

    assert "custom_users" in typed_backend._model_registry
    assert typed_backend._model_registry["custom_users"] == User


def test_with_models_registers_multiple(typed_backend):
    """Test with_models() registers multiple models."""
    result = typed_backend.with_models(User, Product)

    # Should return self for chaining
    assert result is typed_backend

    # Both models should be registered
    assert "users" in typed_backend._model_registry
    assert "products" in typed_backend._model_registry


# Delegation Tests


def test_delegate_to_underlying_backend(typed_backend, duckdb_raw_con):
    """Test that TypedBackend delegates to the underlying backend."""
    # Should be able to call raw_sql on the wrapped backend
    result = typed_backend.raw_sql("SELECT 1 as value")

    # Should work just like the underlying backend
    assert result is not None


def test_delegate_attributes(typed_backend):
    """Test accessing attributes from the underlying backend."""
    # Should be able to access backend attributes
    assert hasattr(typed_backend, "con")  # DuckDB backend has 'con' attribute


# Integration Tests


def test_full_workflow_with_explicit_model(typed_backend):
    """Test a complete workflow with explicit model."""
    UserTable = typed_backend.table("users", model=User)

    result = (
        UserTable.filter(UserTable.age > 25)
        .select("name", "age")
        .order_by("age")
        .execute()
    )

    assert len(result) == 2
    assert result.iloc[0]["name"] == "Alice"


def test_full_workflow_with_registered_model(typed_backend):
    """Test a complete workflow with registered model."""
    typed_backend.register_model(User)

    UserTable = typed_backend.table("users")

    result = UserTable.filter(UserTable.age == 30).execute()

    assert len(result) == 1
    assert result.iloc[0]["name"] == "Alice"


def test_multiple_tables_with_registry(typed_backend):
    """Test working with multiple tables using the registry."""
    typed_backend.with_models(User, Product)

    UserTable = typed_backend.table("users")
    ProductTable = typed_backend.table("products")

    user_result = UserTable.count().execute()
    product_result = ProductTable.count().execute()

    assert user_result == 3
    assert product_result == 2


# Automatic Wrapping Tests (Phase 3)


def test_sql_method_returns_typed_table(typed_backend):
    """Test that sql() method returns a TypedTable."""
    result = typed_backend.sql("SELECT * FROM users")

    assert isinstance(result, TypedTable)


def test_sql_method_with_model(typed_backend):
    """Test sql() method with explicit model."""
    result = typed_backend.sql("SELECT * FROM users WHERE age > 25", model=User)

    assert isinstance(result, TypedTable)

    # Should be able to use model fields
    data = result.execute()
    assert len(data) == 2


def test_sql_method_with_registered_model(typed_backend):
    """Test that sql() can use registered models."""
    typed_backend.register_model(User)

    # Without explicit model parameter
    result = typed_backend.sql("SELECT * FROM users")

    # Should still return a TypedTable (even without model binding)
    assert isinstance(result, TypedTable)


def test_automatic_wrapping_preserves_typed_table_subclass(typed_backend):
    """Test that automatic wrapping preserves TypedTable subclasses."""

    class UserWithCustom(SemanticModel):
        """User model with custom operations."""

        __tablename__ = "users"

        id: int
        name: str
        age: int | None

        def adults(self):
            """Filter for adults."""
            return self.filter(self.age >= 18)

    # Register the model
    typed_backend.register_model(UserWithCustom)

    # Get the table - should use the custom TypedTable subclass
    UserTable = typed_backend.table("users")

    # Should have the custom method
    assert hasattr(UserTable, "adults")

    # And it should work
    result = UserTable.adults().execute()
    assert len(result) == 3  # All test users are adults
