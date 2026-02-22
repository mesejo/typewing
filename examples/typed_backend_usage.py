"""Comprehensive example of TypedBackend usage with custom operations.

This example demonstrates:
1. Creating models with custom operations
2. Wrapping backends with TypedBackend
3. Using explicit model binding
4. Using model registration
5. Custom operations with method chaining
6. SQL queries with typed results
"""

import ibis

from typewing import (
    SemanticModel,
    TypedBackend,
)


# Define models with custom operations
class User(SemanticModel):
    """User model with custom operations."""

    __tablename__ = "users"

    id: int
    name: str
    email: str
    country: str
    age: int | None

    def adults_only(self):
        """Filter for users 18 and older."""
        return self.filter(self.age >= 18)

    def by_country(self, country: str):
        """Filter by country."""
        return self.filter(self.country == country)

    def with_age_category(self):
        """Add age category column."""
        return self.mutate(
            age_category=ibis.ifelse(
                self.age < 18,
                "minor",
                ibis.ifelse(self.age < 65, "adult", "senior"),
            )
        )


class Product(SemanticModel):
    """Product model with custom operations."""

    __tablename__ = "products"

    id: int
    name: str
    price: float
    category: str

    def affordable(self, max_price: float = 50.0):
        """Filter for affordable products."""
        return self.filter(self.price <= max_price)

    def by_category(self, category: str):
        """Filter by category."""
        return self.filter(self.category == category)

    def with_discount(self, percent: float):
        """Add discounted price column."""
        return self.mutate(
            discount_price=self.price * (1 - percent / 100),
            savings=self.price * (percent / 100),
        )


def main():
    """Demonstrate TypedBackend features."""
    # Create a regular ibis connection
    raw_con = ibis.duckdb.connect()

    # Create sample data
    setup_sample_data(raw_con)

    # Wrap the connection with TypedBackend
    con = TypedBackend(raw_con)

    print("=" * 70)
    print("TypedBackend Usage Examples")
    print("=" * 70)

    # Example 1: Explicit model binding
    print("\n1. Explicit Model Binding:")
    print("-" * 70)
    UserTable = con.table("users", model=User)
    result = UserTable.filter(UserTable.age > 30).execute()
    print(f"Users over 30: {len(result)} users")
    print(result[["name", "age"]])

    # Example 2: Using custom operations
    print("\n2. Custom Operations:")
    print("-" * 70)
    adults = UserTable.adults_only().execute()
    print(f"Adult users: {len(adults)} users")

    us_users = UserTable.by_country("US").execute()
    print(f"US users: {len(us_users)} users")

    # Example 3: Chaining custom and standard operations
    print("\n3. Chaining Custom and Standard Operations:")
    print("-" * 70)
    result = (
        UserTable.adults_only()
        .by_country("US")
        .with_age_category()
        .select("name", "age", "age_category", "country")
        .order_by("age")
        .execute()
    )
    print("Adult US users with age categories:")
    print(result)

    # Example 4: Model registration
    print("\n4. Model Registration:")
    print("-" * 70)
    con.register_model(Product)

    # Now we can get the table without specifying the model
    ProductTable = con.table("products")
    print("Product table has custom operations:", hasattr(ProductTable, "affordable"))

    # Example 5: Using registered model's custom operations
    print("\n5. Custom Operations on Registered Models:")
    print("-" * 70)
    affordable_products = ProductTable.affordable(max_price=30.0).execute()
    print(f"Affordable products (<= $30): {len(affordable_products)}")
    print(affordable_products[["name", "price"]])

    # Example 6: Complex custom operation with discount
    print("\n6. Complex Custom Operations:")
    print("-" * 70)
    electronics = (
        ProductTable.by_category("Electronics")
        .with_discount(15)
        .select("name", "price", "discount_price", "savings")
        .execute()
    )
    print("Electronics with 15% discount:")
    print(electronics)

    # Example 7: Bulk model registration
    print("\n7. Bulk Model Registration:")
    print("-" * 70)
    # Create a fresh backend and register multiple models at once
    con2 = TypedBackend(raw_con).with_models(User, Product)
    print(f"Registered models: {list(con2._model_registry.keys())}")

    # Example 8: SQL queries with models
    print("\n8. SQL Queries with Model Binding:")
    print("-" * 70)
    result = con.sql(
        "SELECT * FROM users WHERE age > 25 ORDER BY age",
        model=User,
    )
    # Can use custom operations on SQL results!
    us_adults = result.by_country("US").execute()
    print(f"US users over 25: {len(us_adults)}")
    print(us_adults[["name", "age", "country"]])

    # Example 9: Combining tables with joins
    print("\n9. Joins Work Seamlessly:")
    print("-" * 70)
    # Create an orders table for demonstration
    raw_con.raw_sql(
        """
        CREATE TABLE orders (
            id INTEGER,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER
        )
        """
    )
    raw_con.raw_sql(
        """
        INSERT INTO orders VALUES
            (1, 1, 1, 2),
            (2, 1, 2, 1),
            (3, 2, 1, 3)
        """
    )

    # Standard join operation
    Orders = con.table("orders")
    joined = UserTable.join(Orders, UserTable.id == Orders.user_id).select(
        UserTable.name, Orders.quantity
    )
    result = joined.execute()
    print("User orders:")
    print(result)

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)


def setup_sample_data(con):
    """Create sample tables and data."""
    # Users table
    con.raw_sql(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER,
            name VARCHAR,
            email VARCHAR,
            age INTEGER,
            country VARCHAR
        )
        """
    )
    con.raw_sql("DELETE FROM users")  # Clear existing data
    con.raw_sql(
        """
        INSERT INTO users VALUES
            (1, 'Alice Smith', 'alice@example.com', 32, 'US'),
            (2, 'Bob Jones', 'bob@example.com', 27, 'UK'),
            (3, 'Charlie Brown', 'charlie@example.com', 45, 'US'),
            (4, 'Diana Prince', 'diana@example.com', 29, 'US'),
            (5, 'Eve Wilson', 'eve@example.com', 16, 'CA')
        """
    )

    # Products table
    con.raw_sql(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER,
            name VARCHAR,
            price DOUBLE,
            category VARCHAR
        )
        """
    )
    con.raw_sql("DELETE FROM products")  # Clear existing data
    con.raw_sql(
        """
        INSERT INTO products VALUES
            (1, 'Laptop', 999.99, 'Electronics'),
            (2, 'Mouse', 24.99, 'Electronics'),
            (3, 'Desk Chair', 199.99, 'Furniture'),
            (4, 'Monitor', 299.99, 'Electronics'),
            (5, 'Notebook', 5.99, 'Stationery')
        """
    )


if __name__ == "__main__":
    main()
