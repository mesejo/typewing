import ibis
import pytest

from typewing import SemanticModel, TypedTable


class User(SemanticModel):
    """Test model for users table."""

    __tablename__ = "users"

    id: int
    name: str
    email: str
    age: int | None
    active: bool


class Product(SemanticModel):
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


def test_methods_should_wrap(duckdb_con):
    """Test filtering query."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(UserTable.age > 28)

    assert isinstance(query, TypedTable)


def test_filter_returns_typed_table(duckdb_con):
    """Test that filter method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    # Test simple filter
    query = UserTable.filter(UserTable.age > 28)
    assert isinstance(query, TypedTable)

    # Test chained filters
    query = UserTable.filter(UserTable.age > 28).filter(UserTable.active)
    assert isinstance(query, TypedTable)


def test_select_returns_typed_table(duckdb_con):
    """Test that select method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    # Test select with column names
    query = UserTable.select("name", "email")
    assert isinstance(query, TypedTable)

    # Test select with columns
    query = UserTable.select(UserTable.name, UserTable.email)
    assert isinstance(query, TypedTable)


def test_order_by_returns_typed_table(duckdb_con):
    """Test that order_by method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.order_by(UserTable.age)
    assert isinstance(query, TypedTable)

    # Test with descending order
    query = UserTable.order_by(UserTable.age.desc())
    assert isinstance(query, TypedTable)


def test_limit_returns_typed_table(duckdb_con):
    """Test that limit method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.limit(10)
    assert isinstance(query, TypedTable)


def test_mutate_returns_typed_table(duckdb_con):
    """Test that mutate method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.mutate(age_in_months=UserTable.age * 12)
    assert isinstance(query, TypedTable)


def test_join_returns_typed_table(duckdb_con):
    """Test that join methods return TypedTable."""
    # Create products table
    con = duckdb_con
    con.raw_sql(
        """
        CREATE TABLE products (
            product_id INTEGER,
            name VARCHAR,
            price DOUBLE
        )
        """
    )
    con.raw_sql(
        """
        INSERT INTO products VALUES
            (1, 'Widget', 19.99),
            (2, 'Gadget', 29.99)
        """
    )

    # Create orders table
    con.raw_sql(
        """
        CREATE TABLE orders (
            order_id INTEGER,
            user_id INTEGER,
            product_id INTEGER
        )
        """
    )
    con.raw_sql(
        """
        INSERT INTO orders VALUES
            (1, 1, 1),
            (2, 2, 2)
        """
    )

    UserTable = User.bind(con)
    Product.bind(con, table_name="products")
    OrdersTable = con.table("orders")

    # Test join
    query = UserTable.join(OrdersTable, UserTable.id == OrdersTable.user_id)
    assert isinstance(query, TypedTable)

    # Test left_join
    query = UserTable.left_join(OrdersTable, UserTable.id == OrdersTable.user_id)
    assert isinstance(query, TypedTable)

    # Test inner_join
    query = UserTable.inner_join(OrdersTable, UserTable.id == OrdersTable.user_id)
    assert isinstance(query, TypedTable)


def test_group_by_aggregate_returns_typed_table(duckdb_con):
    """Test that group_by followed by aggregate returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    # group_by returns a GroupedTable, but aggregate on it returns a Table
    query = UserTable.group_by(UserTable.active).aggregate(count=UserTable.count())
    assert isinstance(query, TypedTable)


def test_aggregate_returns_typed_table(duckdb_con):
    """Test that aggregate method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.aggregate(count=UserTable.count())
    assert isinstance(query, TypedTable)


def test_distinct_returns_typed_table(duckdb_con):
    """Test that distinct method returns TypedTable."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.distinct()
    assert isinstance(query, TypedTable)


def test_chained_operations_return_typed_table(duckdb_con):
    """Test that chained operations all return TypedTable."""
    UserTable = User.bind(duckdb_con)

    query = (
        UserTable.filter(UserTable.age > 25)
        .select(UserTable.name, UserTable.email, UserTable.age)
        .order_by(UserTable.age.desc())
        .limit(5)
    )

    assert isinstance(query, TypedTable)

    # Test that we can still execute and get results
    result = query.execute()
    assert len(result) > 0
