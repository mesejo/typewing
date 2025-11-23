# typewing

Type-safe Ibis table extensions with SQLModel-like interface. 

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

## License

This project is licensed under the Apache License.

## Acknowledgments

- Built on top of [Ibis](https://ibis-project.org/) - the portable dataframe library
- Inspired by [SQLModel](https://sqlmodel.tiangolo.com/) - the SQL database framework

## Related Projects

- [Ibis](https://ibis-project.org/) - The portable Python dataframe library
- [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases in Python, designed for simplicity
- [SQLAlchemy](https://www.sqlalchemy.org/) - The Python SQL toolkit
