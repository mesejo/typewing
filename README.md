# typewing

Type-safe Ibis table extensions with SQLModel-like interface. Create typed models for your database tables and get full IDE autocomplete support while preserving all of Ibis's powerful query building capabilities.

## Features

- **SQLModel-like API**: Define your table schemas using Python type annotations
- **Full IDE Autocomplete**: Get intelligent code completion for your table columns and their types
- **Native Ibis Integration**: All Ibis query operations work seamlessly
- **Type Safety**: Leverage Python's type system for safer database queries
- **Field Aliases**: Map Python field names to different database column names
- **Field Metadata**: Add descriptions and other metadata to your fields

## Installation

```bash
pip install typewing
```

Or with uv:

```bash
uv add typewing
```

## Quick Start

```python
from typewing import IbisModel, Field
import ibis

# Define your model with type annotations
class User(IbisModel):
    __tablename__ = "users"

    id: int
    name: str
    email: str
    age: int | None = Field(description="User's age in years")
    is_active: bool = Field(alias="active")

# Connect to your database
con = ibis.duckdb.connect()

# Bind the model to get a typed table
UserTable = User.bind(con)

# Use all of Ibis's query building with full type safety!
query = (
    UserTable
    .filter(UserTable.age > 18)
    .filter(UserTable.is_active == True)
    .select("name", "email")
    .order_by("name")
    .limit(10)
)

# Execute and get results
results = query.execute()
```

## Detailed Usage

### Defining Models

Models are defined by inheriting from `IbisModel` and using type annotations:

```python
from typewing import IbisModel, Field

class Product(IbisModel):
    # Explicit table name (optional - defaults to lowercase class name)
    __tablename__ = "products"

    # Simple typed fields
    product_id: int
    name: str
    price: float

    # Optional fields using Union type
    description: str | None

    # Fields with metadata
    category: str = Field(description="Product category")

    # Fields with database column aliases
    is_available: bool = Field(alias="available")
```

### Table Names

If you don't specify `__tablename__`, the table name defaults to the lowercase class name:

```python
class User(IbisModel):
    id: int
    name: str

# Table name will be "user"
```

### Field Aliases

Use the `alias` parameter to map Python field names to different database column names:

```python
class User(IbisModel):
    user_id: int = Field(alias="id")
    full_name: str = Field(alias="name")
    is_active: bool = Field(alias="active")

# Now you can use Python-style names in your code:
UserTable = User.bind(con)
query = UserTable.filter(UserTable.is_active == True)
# But it maps to the actual database column "active"
```

### Binding to a Database

Before you can query, bind your model to an Ibis connection:

```python
import ibis

# Create a connection (DuckDB, PostgreSQL, etc.)
con = ibis.duckdb.connect()

# Bind the model
UserTable = User.bind(con)

# Optionally override the table name
CustomTable = User.bind(con, table_name="custom_users")
```

### Query Building

The bound table supports all Ibis operations:

```python
# Filtering
active_users = UserTable.filter(UserTable.is_active == True)

# Selecting columns
names = UserTable.select("name", "email")

# Chaining operations
query = (
    UserTable
    .filter(UserTable.age > 18)
    .filter(UserTable.name.like("A%"))
    .select("name", "email", "age")
    .order_by(UserTable.age.desc())
    .limit(10)
)

# Aggregations
user_count = UserTable.count().execute()
avg_age = UserTable.age.mean().execute()

# Grouping
by_category = (
    ProductTable
    .group_by("category")
    .aggregate(
        count=ProductTable.count(),
        avg_price=ProductTable.price.mean()
    )
)

# Joins (with other ibis tables)
orders = con.table("orders")
query = UserTable.join(orders, UserTable.id == orders.user_id)
```

### Executing Queries

Execute queries using the `.execute()` method:

```python
# Returns a pandas DataFrame
results = query.execute()

# Iterate over results
for index, row in results.iterrows():
    print(row["name"], row["email"])
```

### Working with Multiple Backends

typewing works with any Ibis backend:

```python
# DuckDB
con = ibis.duckdb.connect()

# PostgreSQL
con = ibis.postgres.connect(
    host="localhost",
    database="mydb",
    user="user",
    password="password"
)

# SQLite
con = ibis.sqlite.connect("database.db")

# And many more: BigQuery, Snowflake, Trino, etc.
UserTable = User.bind(con)
```

## IDE Autocomplete Support

One of the key features is full IDE autocomplete support. When you access fields on your bound table, your IDE will:

- Show all available fields
- Display their types
- Show field descriptions (from `Field()` metadata)
- Provide autocomplete for Ibis methods

```python
UserTable = User.bind(con)

# Your IDE will autocomplete:
UserTable.name       #  knows it's a string column
UserTable.age        #  knows it's an int | None column
UserTable.is_active  #  knows it's a bool column
UserTable.filter(    #  autocompletes Ibis methods
```

## Advanced Usage

### Getting Field Metadata

Access field information programmatically:

```python
# Get all fields
fields = User.get_fields()

# Get field names
field_names = User.get_field_names()
# ['id', 'name', 'email', 'age', 'is_active']

# Get field types
field_types = User.get_field_types()
# {'id': int, 'name': str, 'email': str, ...}

# Get table name
table_name = User.get_table_name()
# 'users'

# Get column name (handles aliases)
col_name = User.get_column_name('is_active')
# 'active'
```

### Using with Ibis Expressions

You can mix typed tables with regular Ibis expressions:

```python
import ibis

UserTable = User.bind(con)

# Use ibis functions
query = UserTable.filter(
    ibis.and_(
        UserTable.age > 18,
        UserTable.name.length() > 3
    )
)

# Window functions
query = UserTable.mutate(
    rank=ibis.rank().over(order_by=UserTable.age.desc())
)
```

## Comparison with SQLModel

If you're familiar with SQLModel, here's how typewing compares:

| Feature | SQLModel | typewing |
|---------|----------|----------|
| Type annotations |  |  |
| IDE autocomplete |  |  |
| Field metadata |  |  |
| ORM-style queries |  |  (uses Ibis) |
| Multiple backends | Limited |  (20+ via Ibis) |
| Complex queries | Via SQLAlchemy |  Native Ibis |
| Data validation |  |  |
| Model instances |  |  (returns DataFrames) |

typewing is designed for:
- **Complex analytical queries** where Ibis excels
- **Working with multiple database backends** with a unified API
- **Type-safe query building** without ORM overhead
- **Data engineering/analysis** workflows

## Examples

### Example 1: User Analytics

```python
from typewing import IbisModel, Field
import ibis

class User(IbisModel):
    __tablename__ = "users"

    id: int
    email: str
    signup_date: str  # Or use datetime if your backend supports it
    age: int | None
    country: str

con = ibis.duckdb.connect("analytics.db")
UserTable = User.bind(con)

# Find users by country
us_users = UserTable.filter(UserTable.country == "US")

# Age distribution
age_stats = UserTable.filter(UserTable.age.notnull()).aggregate(
    avg_age=UserTable.age.mean(),
    min_age=UserTable.age.min(),
    max_age=UserTable.age.max(),
    count=UserTable.count()
).execute()

print(f"Average age: {age_stats['avg_age'][0]:.1f}")
```

### Example 2: E-commerce Products

```python
class Product(IbisModel):
    __tablename__ = "products"

    id: int
    name: str
    category: str
    price: float
    stock: int
    is_active: bool = Field(alias="active")

con = ibis.postgres.connect(...)
ProductTable = Product.bind(con)

# Find affordable products in stock
query = (
    ProductTable
    .filter(ProductTable.is_active == True)
    .filter(ProductTable.stock > 0)
    .filter(ProductTable.price < 50)
    .order_by(ProductTable.price.asc())
)

affordable_products = query.execute()
```

### Example 3: Sales Analytics

```python
class Sale(IbisModel):
    __tablename__ = "sales"

    sale_id: int
    product_id: int
    quantity: int
    revenue: float
    sale_date: str

con = ibis.duckdb.connect()
SaleTable = Sale.bind(con)

# Revenue by day
daily_revenue = (
    SaleTable
    .group_by("sale_date")
    .aggregate(
        total_revenue=SaleTable.revenue.sum(),
        total_quantity=SaleTable.quantity.sum(),
        num_sales=SaleTable.count()
    )
    .order_by("sale_date")
)

results = daily_revenue.execute()
```

## Testing

Run the test suite:

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=typewing --cov-report=html
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the MIT License.

## Acknowledgments

- Built on top of [Ibis](https://ibis-project.org/) - the portable dataframe library
- Inspired by [SQLModel](https://sqlmodel.tiangolo.com/) - the SQL database framework

## Related Projects

- [Ibis](https://ibis-project.org/) - The portable Python dataframe library
- [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases in Python, designed for simplicity
- [SQLAlchemy](https://www.sqlalchemy.org/) - The Python SQL toolkit
