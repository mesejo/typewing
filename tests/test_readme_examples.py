"""Tests for README.md code examples."""

import ibis
import pytest

from typewing import Field, IbisModel


# Model definitions from README examples


class User(IbisModel):
    """User model from Quick Start example."""

    __tablename__ = "users"

    id: int
    name: str
    email: str
    age: int | None = Field(description="User's age in years")
    is_active: bool = Field(alias="active")


class Product(IbisModel):
    """Product model from Detailed Usage example."""

    __tablename__ = "products"

    product_id: int
    name: str
    price: float
    description: str | None
    category: str = Field(description="Product category")
    is_available: bool = Field(alias="available")


class UserWithAliases(IbisModel):
    """User model demonstrating field aliases."""

    __tablename__ = "users_aliases"

    user_id: int = Field(alias="id")
    full_name: str = Field(alias="name")
    is_active: bool = Field(alias="active")


class UserAnalytics(IbisModel):
    """User model for analytics example."""

    __tablename__ = "users_analytics"

    id: int
    email: str
    signup_date: str
    age: int | None
    country: str


class Sale(IbisModel):
    """Sales model from Sales Analytics example."""

    __tablename__ = "sales"

    sale_id: int
    product_id: int
    quantity: int
    revenue: float
    sale_date: str


# Fixtures


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data for all examples."""
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

    con.raw_sql(
        """
        INSERT INTO users VALUES
            (1, 'Alice', 'alice@example.com', 30, true),
            (2, 'Bob', 'bob@example.com', 25, true),
            (3, 'Charlie', 'charlie@example.com', 17, false),
            (4, 'Diana', 'diana@example.com', 35, true),
            (5, 'Abigail', 'abigail@example.com', 22, true),
            (6, 'Andrew', 'andrew@example.com', 19, true)
        """
    )

    # Create products table
    con.raw_sql(
        """
        CREATE TABLE products (
            product_id INTEGER,
            name VARCHAR,
            price DOUBLE,
            description VARCHAR,
            category VARCHAR,
            available BOOLEAN
        )
        """
    )

    con.raw_sql(
        """
        INSERT INTO products VALUES
            (1, 'Laptop', 999.99, 'High-performance laptop', 'Electronics', true),
            (2, 'Mouse', 25.50, 'Wireless mouse', 'Electronics', true),
            (3, 'Keyboard', 75.00, NULL, 'Electronics', true),
            (4, 'Desk', 299.99, 'Standing desk', 'Furniture', false),
            (5, 'Chair', 199.99, 'Ergonomic chair', 'Furniture', true),
            (6, 'Monitor', 45.00, '24-inch monitor', 'Electronics', true)
        """
    )

    # Create users_aliases table
    con.raw_sql(
        """
        CREATE TABLE users_aliases (
            id INTEGER,
            name VARCHAR,
            active BOOLEAN
        )
        """
    )

    con.raw_sql(
        """
        INSERT INTO users_aliases VALUES
            (1, 'Alice Smith', true),
            (2, 'Bob Jones', false),
            (3, 'Charlie Brown', true)
        """
    )

    # Create users_analytics table
    con.raw_sql(
        """
        CREATE TABLE users_analytics (
            id INTEGER,
            email VARCHAR,
            signup_date VARCHAR,
            age INTEGER,
            country VARCHAR
        )
        """
    )

    con.raw_sql(
        """
        INSERT INTO users_analytics VALUES
            (1, 'user1@example.com', '2024-01-15', 28, 'US'),
            (2, 'user2@example.com', '2024-01-20', 35, 'US'),
            (3, 'user3@example.com', '2024-02-01', 42, 'UK'),
            (4, 'user4@example.com', '2024-02-15', NULL, 'US'),
            (5, 'user5@example.com', '2024-03-01', 31, 'CA'),
            (6, 'user6@example.com', '2024-03-10', 29, 'US')
        """
    )

    # Create sales table
    con.raw_sql(
        """
        CREATE TABLE sales (
            sale_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            revenue DOUBLE,
            sale_date VARCHAR
        )
        """
    )

    con.raw_sql(
        """
        INSERT INTO sales VALUES
            (1, 1, 2, 199.98, '2024-01-15'),
            (2, 2, 5, 127.50, '2024-01-15'),
            (3, 1, 1, 99.99, '2024-01-16'),
            (4, 3, 3, 225.00, '2024-01-16'),
            (5, 2, 10, 255.00, '2024-01-17'),
            (6, 1, 1, 99.99, '2024-01-17')
        """
    )

    yield con
    con.disconnect()


# Quick Start Example Tests


def test_quick_start_filter_age(duckdb_con):
    """Test Quick Start example: filter by age > 18."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(UserTable.age > 18)
    results = query.execute()

    assert len(results) == 5
    assert all(age > 18 for age in results["age"] if age is not None)


def test_quick_start_filter_active(duckdb_con):
    """Test Quick Start example: filter by is_active == True."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(UserTable.is_active)
    results = query.execute()

    assert len(results) == 5
    assert all(results["active"])


def test_quick_start_chained_query(duckdb_con):
    """Test Quick Start example: chained filtering with select, order_by, limit."""
    UserTable = User.bind(duckdb_con)

    query = (
        UserTable.filter(UserTable.age > 18)
        .filter(UserTable.is_active)
        .select("name", "email")
        .order_by("name")
        .limit(10)
    )

    results = query.execute()

    assert len(results) == 5
    assert list(results.columns) == ["name", "email"]
    # Check ordering
    names = results["name"].tolist()
    assert names == sorted(names)


# Field Aliases Tests


def test_field_aliases_mapping(duckdb_con):
    """Test Field Aliases example: Python names map to database columns."""
    UserAliasTable = UserWithAliases.bind(duckdb_con)

    query = UserAliasTable.filter(UserAliasTable.is_active)
    results = query.execute()

    assert len(results) == 2
    assert "id" in results.columns
    assert "name" in results.columns
    assert "active" in results.columns


def test_field_aliases_column_name_method():
    """Test that get_column_name returns correct database column names."""
    assert UserWithAliases.get_column_name("user_id") == "id"
    assert UserWithAliases.get_column_name("full_name") == "name"
    assert UserWithAliases.get_column_name("is_active") == "active"


# Query Building Tests


def test_query_building_filtering(duckdb_con):
    """Test Query Building example: filtering."""
    UserTable = User.bind(duckdb_con)

    active_users = UserTable.filter(UserTable.is_active)
    results = active_users.execute()

    assert len(results) == 5
    assert all(results["active"])


def test_query_building_selecting_columns(duckdb_con):
    """Test Query Building example: selecting columns."""
    UserTable = User.bind(duckdb_con)

    names = UserTable.select("name", "email")
    results = names.execute()

    assert list(results.columns) == ["name", "email"]
    assert len(results) == 6


def test_query_building_chaining(duckdb_con):
    """Test Query Building example: chaining operations."""
    UserTable = User.bind(duckdb_con)

    query = (
        UserTable.filter(UserTable.age > 18)
        .filter(UserTable.name.like("A%"))
        .select("name", "email", "age")
        .order_by(UserTable.age.desc())
        .limit(10)
    )

    results = query.execute()

    assert len(results) <= 10
    assert all(name.startswith("A") for name in results["name"])
    assert all(age > 18 for age in results["age"])
    # Check descending order
    ages = results["age"].tolist()
    assert ages == sorted(ages, reverse=True)


def test_query_building_aggregations_count(duckdb_con):
    """Test Query Building example: count aggregation."""
    UserTable = User.bind(duckdb_con)

    user_count = UserTable.count().execute()

    assert user_count == 6


def test_query_building_aggregations_mean(duckdb_con):
    """Test Query Building example: mean aggregation."""
    UserTable = User.bind(duckdb_con)

    avg_age = UserTable.age.mean().execute()

    assert avg_age is not None
    assert pytest.approx(avg_age, rel=0.1) == 26.4  # (30+25+17+35+22+19)/6


def test_query_building_grouping(duckdb_con):
    """Test Query Building example: grouping."""
    ProductTable = Product.bind(duckdb_con)

    by_category = ProductTable.group_by("category").aggregate(
        count=ProductTable.count(), avg_price=ProductTable.price.mean()
    )

    results = by_category.execute()

    assert len(results) == 2
    assert set(results["category"]) == {"Electronics", "Furniture"}

    # Check Electronics stats
    electronics = results[results["category"] == "Electronics"].iloc[0]
    assert electronics["count"] == 4
    assert (
        pytest.approx(electronics["avg_price"], rel=0.01)
        == (999.99 + 25.50 + 75.00 + 45.00) / 4
    )


def test_query_building_joins(duckdb_con):
    """Test Query Building example: joins."""
    UserTable = User.bind(duckdb_con)

    # Create a simple orders table for this test
    duckdb_con.raw_sql(
        """
        CREATE TABLE orders (
            order_id INTEGER,
            user_id INTEGER,
            amount DOUBLE
        )
        """
    )

    duckdb_con.raw_sql(
        """
        INSERT INTO orders VALUES
            (1, 1, 100.00),
            (2, 1, 200.00),
            (3, 2, 150.00)
        """
    )

    orders = duckdb_con.table("orders")
    query = UserTable.join(orders, UserTable.id == orders.user_id)
    results = query.execute()

    assert len(results) == 3
    assert "name" in results.columns
    assert "amount" in results.columns


# Advanced Usage Tests


def test_advanced_usage_get_fields():
    """Test Advanced Usage example: get_fields()."""
    fields = User.get_fields()

    assert "id" in fields
    assert "name" in fields
    assert "age" in fields
    assert fields["age"]["description"] == "User's age in years"
    assert fields["is_active"]["alias"] == "active"


def test_advanced_usage_get_field_names():
    """Test Advanced Usage example: get_field_names()."""
    field_names = User.get_field_names()

    assert field_names == ["id", "name", "email", "age", "is_active"]


def test_advanced_usage_get_field_types():
    """Test Advanced Usage example: get_field_types()."""
    field_types = User.get_field_types()

    assert field_types["id"] is int
    assert field_types["name"] is str
    assert field_types["email"] is str
    assert "age" in field_types


def test_advanced_usage_get_table_name():
    """Test Advanced Usage example: get_table_name()."""
    table_name = User.get_table_name()

    assert table_name == "users"


def test_advanced_usage_get_column_name():
    """Test Advanced Usage example: get_column_name()."""
    col_name = User.get_column_name("is_active")

    assert col_name == "active"


def test_advanced_usage_ibis_expressions(duckdb_con):
    """Test Advanced Usage example: using with Ibis expressions."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(ibis.and_(UserTable.age > 18, UserTable.name.length() > 3))

    results = query.execute()

    assert all(age > 18 for age in results["age"])
    assert all(len(name) > 3 for name in results["name"])


def test_advanced_usage_window_functions(duckdb_con):
    """Test Advanced Usage example: window functions."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.mutate(rank=ibis.rank().over(order_by=UserTable.age.desc()))

    results = query.execute()

    assert "rank" in results.columns
    # Highest age should have rank 0 or 1 (depending on Ibis version)
    max_age_row = results[results["age"] == results["age"].max()].iloc[0]
    assert max_age_row["rank"] in [0, 1]


# Example 1: User Analytics Tests


def test_example_user_analytics_country_filter(duckdb_con):
    """Test User Analytics example: find users by country."""
    UserAnalyticsTable = UserAnalytics.bind(duckdb_con)

    us_users = UserAnalyticsTable.filter(UserAnalyticsTable.country == "US")
    results = us_users.execute()

    assert len(results) == 4
    assert all(country == "US" for country in results["country"])


def test_example_user_analytics_age_stats(duckdb_con):
    """Test User Analytics example: age distribution."""
    UserAnalyticsTable = UserAnalytics.bind(duckdb_con)

    # First filter, then aggregate
    filtered_table = UserAnalyticsTable.filter(UserAnalyticsTable.age.notnull())
    age_stats = filtered_table.aggregate(
        avg_age=filtered_table.age.mean(),
        min_age=filtered_table.age.min(),
        max_age=filtered_table.age.max(),
        count=filtered_table.count(),
    ).execute()

    assert age_stats["avg_age"].iloc[0] == pytest.approx((28 + 35 + 42 + 31 + 29) / 5)
    assert age_stats["min_age"].iloc[0] == 28
    assert age_stats["max_age"].iloc[0] == 42
    assert age_stats["count"].iloc[0] == 5


# Example 2: E-commerce Products Tests


def test_example_ecommerce_affordable_products(duckdb_con):
    """Test E-commerce Products example: find affordable products in stock."""
    ProductTable = Product.bind(duckdb_con)

    query = (
        ProductTable.filter(ProductTable.is_available)
        .filter(ProductTable.price < 50)
        .order_by(ProductTable.price.asc())
    )

    affordable_products = query.execute()

    assert len(affordable_products) == 2
    assert all(price < 50 for price in affordable_products["price"])
    assert all(affordable_products["available"])
    # Check ascending order
    prices = affordable_products["price"].tolist()
    assert prices == sorted(prices)


# Example 3: Sales Analytics Tests


def test_example_sales_analytics_daily_revenue(duckdb_con):
    """Test Sales Analytics example: revenue by day."""
    SaleTable = Sale.bind(duckdb_con)

    daily_revenue = (
        SaleTable.group_by("sale_date")
        .aggregate(
            total_revenue=SaleTable.revenue.sum(),
            total_quantity=SaleTable.quantity.sum(),
            num_sales=SaleTable.count(),
        )
        .order_by("sale_date")
    )

    results = daily_revenue.execute()

    assert len(results) == 3
    # Check 2024-01-15
    day1 = results[results["sale_date"] == "2024-01-15"].iloc[0]
    assert day1["total_revenue"] == pytest.approx(199.98 + 127.50)
    assert day1["total_quantity"] == 7
    assert day1["num_sales"] == 2


# Model Definition Tests


def test_product_model_field_metadata():
    """Test Product model field metadata."""
    fields = Product.get_fields()

    assert fields["category"]["description"] == "Product category"
    assert fields["is_available"]["alias"] == "available"


def test_product_model_optional_fields():
    """Test Product model has optional description field."""
    field_types = Product.get_field_types()

    assert "description" in field_types


# Executing Queries Tests


def test_executing_queries_iterate_results(duckdb_con):
    """Test Executing Queries example: iterate over results."""
    UserTable = User.bind(duckdb_con)

    query = UserTable.filter(UserTable.age > 20).select("name", "email")
    results = query.execute()

    # Iterate and collect
    collected = []
    for index, row in results.iterrows():
        collected.append((row["name"], row["email"]))

    assert len(collected) == 4
    assert all(
        isinstance(item[0], str) and isinstance(item[1], str) for item in collected
    )


# Additional Edge Case Tests


def test_default_tablename():
    """Test that table name defaults to lowercase class name when not specified."""

    class DefaultTable(IbisModel):
        id: int
        name: str

    assert DefaultTable.get_table_name() == "defaulttable"


def test_filter_with_null_values(duckdb_con):
    """Test filtering with NULL values in age field."""
    UserTable = User.bind(duckdb_con)

    # Filter for users with non-null age
    query = UserTable.filter(UserTable.age.notnull())
    results = query.execute()

    assert len(results) == 6  # All users have ages in our test data


def test_complex_filter_conditions(duckdb_con):
    """Test complex filter with multiple conditions."""
    ProductTable = Product.bind(duckdb_con)

    query = (
        ProductTable.filter(ProductTable.category == "Electronics")
        .filter(ProductTable.price < 100)
        .filter(ProductTable.is_available)
    )

    results = query.execute()

    assert len(results) == 3
    assert all(cat == "Electronics" for cat in results["category"])
    assert all(price < 100 for price in results["price"])
    assert all(results["available"])
