"""Basic usage example for ibis-var."""

import ibis

from typewing import Field, IbisModel


# Define models
class User(IbisModel):
    """User model with typed fields."""

    __tablename__ = "users"

    id: int
    name: str
    email: str
    age: int | None = Field(description="User's age in years")
    is_active: bool = Field(
        alias="active", description="Whether the user account is active"
    )


class Product(IbisModel):
    """Product model."""

    __tablename__ = "products"

    product_id: int
    name: str
    category: str
    price: float
    stock: int


def setup_sample_data(con):
    """Create sample tables and insert data."""
    # Create users table
    con.raw_sql(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER,
            name VARCHAR,
            email VARCHAR,
            age INTEGER,
            active BOOLEAN
        )
        """
    )

    # Insert sample users
    con.raw_sql(
        """
        INSERT INTO users VALUES
            (1, 'Alice Johnson', 'alice@example.com', 30, true),
            (2, 'Bob Smith', 'bob@example.com', 25, true),
            (3, 'Charlie Brown', 'charlie@example.com', NULL, false),
            (4, 'Diana Prince', 'diana@example.com', 35, true),
            (5, 'Eve Anderson', 'eve@example.com', 28, true)
        """
    )

    # Create products table
    con.raw_sql(
        """
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER,
            name VARCHAR,
            category VARCHAR,
            price DOUBLE,
            stock INTEGER
        )
        """
    )

    # Insert sample products
    con.raw_sql(
        """
        INSERT INTO products VALUES
            (1, 'Laptop', 'Electronics', 999.99, 15),
            (2, 'Mouse', 'Electronics', 29.99, 50),
            (3, 'Desk Chair', 'Furniture', 199.99, 10),
            (4, 'Monitor', 'Electronics', 299.99, 20),
            (5, 'Keyboard', 'Electronics', 79.99, 30)
        """
    )


def main():
    """Run example queries."""
    print("=" * 60)
    print("ibis-var Basic Usage Example")
    print("=" * 60)

    # Connect to DuckDB (in-memory)
    con = ibis.duckdb.connect()
    print("\n✓ Connected to DuckDB")

    # Setup sample data
    setup_sample_data(con)
    print("✓ Sample data created")

    # Bind models
    UserTable = User.bind(con)
    ProductTable = Product.bind(con)
    print("✓ Models bound to database\n")

    # Example 1: Simple select
    print("Example 1: Get all users")
    print("-" * 60)
    all_users = UserTable.execute()
    print(all_users)
    print()

    # Example 2: Filtering
    print("Example 2: Filter active users with age > 25")
    print("-" * 60)
    active_users = (
        UserTable.filter(UserTable.is_active)
        .filter(UserTable.age > 25)
        .select("name", "email", "age")
    )
    results = active_users.execute()
    print(results)
    print()

    # Example 3: Ordering
    print("Example 3: Users ordered by age (descending)")
    print("-" * 60)
    ordered = (
        UserTable.filter(UserTable.age.notnull())
        .select("name", "age")
        .order_by(UserTable.age.desc())
    )
    results = ordered.execute()
    print(results)
    print()

    # Example 4: Aggregation
    print("Example 4: User statistics")
    print("-" * 60)
    filtered_users = UserTable.filter(UserTable.age.notnull())
    stats = filtered_users.aggregate(
        total_users=filtered_users.age.count(),
        avg_age=filtered_users.age.mean(),
        min_age=filtered_users.age.min(),
        max_age=filtered_users.age.max(),
    )
    results = stats.execute()
    print(f"Total users with age: {results['total_users'][0]}")
    print(f"Average age: {results['avg_age'][0]:.1f}")
    print(f"Age range: {results['min_age'][0]} - {results['max_age'][0]}")
    print()

    # Example 5: Products by category
    print("Example 5: Electronics under $100")
    print("-" * 60)
    affordable_electronics = (
        ProductTable.filter(ProductTable.category == "Electronics")
        .filter(ProductTable.price < 100)
        .select("name", "price", "stock")
        .order_by(ProductTable.price.asc())
    )
    results = affordable_electronics.execute()
    print(results)
    print()

    # Example 6: Product inventory summary
    print("Example 6: Inventory by category")
    print("-" * 60)
    inventory = ProductTable.group_by("category").aggregate(
        num_products=ProductTable.product_id.count(),
        total_value=(ProductTable.price * ProductTable.stock).sum(),
        avg_price=ProductTable.price.mean(),
    )
    results = inventory.execute()
    print(results)
    print()

    # Example 7: Using limit
    print("Example 7: Top 3 most expensive products")
    print("-" * 60)
    top_products = (
        ProductTable.select("name", "price")
        .order_by(ProductTable.price.desc())
        .limit(3)
    )
    results = top_products.execute()
    print(results)
    print()

    # Example 8: Field metadata
    print("Example 8: Model field metadata")
    print("-" * 60)
    print(f"User fields: {User.get_field_names()}")
    print(f"Product fields: {Product.get_field_names()}")
    print(f"\nUser table name: {User.get_table_name()}")
    print(f"'is_active' maps to column: {User.get_column_name('is_active')}")
    print()

    print("=" * 60)
    print("Examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
