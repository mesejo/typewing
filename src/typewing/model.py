"""Core model classes for typewing."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Iterable,
    Literal,
    Mapping,
    Self,
    Sequence,
    TypeVar,
    get_type_hints,
)

from ibis.expr.types import Table
from ibis.expr.types.groupby import GroupedTable


if TYPE_CHECKING:
    import ibis.expr.schema as sch
    import ibis.expr.types as ir
    from ibis.expr.types.temporal_windows import WindowedTable
    from ibis.selectors import Selector

T = TypeVar("T", bound="SemanticModel")


class FieldDescriptor:
    """Simple descriptor for model fields.

    This enables field access on both the class and instances.
    """

    def __init__(self, field_name: str):
        self.field_name = field_name

    def __get__(self, obj, objtype=None):
        """Get the field value.

        Args:
            obj: Instance being accessed (or None if accessing from class)
            objtype: Type of the instance

        Returns:
            self for class access, column for instance access
        """
        if obj is None:
            # Accessed from the class, return self to indicate the field exists
            return self

        # If accessed from a SemanticModel instance, return the column
        if isinstance(obj, SemanticModel):
            return obj._ibis_table[self.field_name]

        # For other cases, just return self
        return self

    # def __set__(self, obj, value):
    #     """Prevent setting field values."""
    #     raise AttributeError(f"Cannot set field '{self.field_name}' on model")

    def __repr__(self):
        """Return string representation."""
        return f"FieldDescriptor({self.field_name!r})"


class ModelMeta(type):
    """Metaclass for SemanticModel that handles field registration."""

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs
    ):
        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace)

        # Skip for the base SemanticModel class itself
        if name == "SemanticModel":
            return cls

        # Get type hints for this class only (not inherited)
        if hasattr(cls, "__annotations__"):
            hints = get_type_hints(cls)
        else:
            hints = {}

        # Store field names (just the names, no complex metadata)
        cls._field_names = [
            field_name for field_name in hints.keys() if not field_name.startswith("_")
        ]
        cls._table_name = namespace.get("__tablename__")

        # Add class-level descriptors for each field
        # This enables IDE autocomplete and hasattr checks on the class itself
        for field_name in cls._field_names:
            if not hasattr(cls, field_name):
                setattr(cls, field_name, FieldDescriptor(field_name))

        return cls


class TypedGroupedTable:
    """Wrapper around an Ibis GroupedTable that preserves type information.

    This class delegates all attribute access to the underlying Ibis GroupedTable
    while ensuring that methods returning Table objects are wrapped in the model class.
    """

    def __init__(
        self,
        grouped_table: GroupedTable,
        model_class: type[SemanticModel],
    ):
        self._grouped_table = grouped_table
        self._model_class = model_class

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying grouped table."""
        attr = getattr(self._grouped_table, name)

        # If it's a callable (method), wrap it to return model instance when appropriate
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                # If the result is a Table, wrap it in the model class
                if isinstance(result, Table):
                    return self._model_class(result)
                return result

            return wrapped_method

        return attr

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TypedGroupedTable({self._grouped_table})"


class TypedWindowedTable:
    """Wrapper around an Ibis WindowedTable that preserves type information.

    This class delegates all attribute access to the underlying Ibis WindowedTable
    while ensuring that methods returning Table objects are wrapped in the model class.
    """

    def __init__(
        self,
        windowed_table: WindowedTable,
        model_class: type[SemanticModel],
    ):
        self._windowed_table = windowed_table
        self._model_class = model_class

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying windowed table."""
        attr = getattr(self._windowed_table, name)

        # If it's a callable (method), wrap it to return model instance when appropriate
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                # If the result is a Table, wrap it in the model class
                if isinstance(result, Table):
                    return self._model_class(result)
                return result

            return wrapped_method

        return attr

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TypedWindowedTable({self._windowed_table})"


class SemanticModel(metaclass=ModelMeta):
    """Base class for typed Ibis tables with a unified design.

    Define your table schema using type annotations, and add custom methods
    directly to the model class. When you bind to a connection, you get back
    an instance that wraps the Ibis table with full type safety.

    Example:
        ```python
        from typewing import SemanticModel
        import ibis

        class User(SemanticModel):
            __tablename__ = "users"

            id: int
            name: str
            email: str
            age: int | None

            # Add custom methods directly
            def adults_only(self):
                return self.filter(self.age >= 18)

            def by_country(self, country: str):
                return self.filter(self.country == country)

        # Bind to a connection
        con = ibis.duckdb.connect()
        UserTable = User.bind(con)

        # Use custom and standard methods
        query = UserTable.adults_only().select("name", "email")
        result = query.execute()
        ```
    """

    _field_names: ClassVar[list[str]] = []
    _table_name: ClassVar[str | None] = None

    def __init__(self, ibis_table: Table):
        """Initialize the model with an Ibis table.

        Args:
            ibis_table: The underlying Ibis table to wrap
        """
        self._ibis_table = ibis_table
        assert self.__typewing_schema_matches__(ibis_table.schema())

        # Create properties for each field to enable typed access
        available_columns = set(ibis_table.columns)
        for field_name in self._field_names:
            if field_name in available_columns:
                object.__setattr__(self, field_name, ibis_table[field_name])

    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        if cls._table_name:
            return cls._table_name
        # Default to lowercase class name
        return cls.__name__.lower()

    @classmethod
    def bind(cls: type[T], connection: Any, table_name: str | None = None) -> T:
        """Bind this model to an ibis connection and return a model instance.

        Args:
            connection: Ibis connection object (e.g., ibis.duckdb.connect())
            table_name: Optional table name override

        Returns:
            An instance of this model class wrapping the ibis Table

        Example:
            ```python
            con = ibis.duckdb.connect()
            UserTable = User.bind(con)

            # Now you can use it with custom and standard methods
            query = UserTable.adults_only().filter(UserTable.age > 18)
            results = query.execute()
            ```
        """
        table_name = table_name or cls.get_table_name()
        ibis_table = connection.table(table_name)
        return cls(ibis_table)

    @classmethod
    def get_field_names(cls) -> list[str]:
        """Get list of all field names."""
        return cls._field_names.copy()

    def __typewing_schema_matches__(
        self, schema: sch.Schema, strict: bool = False
    ) -> bool:
        """Validate that the table schema matches the model's type annotations.

        This method uses the type annotations of the fields and checks that types
        match. For example, int should match dtype int64 or int32.

        Parameters
        ----------
        schema
            The Ibis schema to validate against.
        strict
            If True, requires exact type match. If False, allows compatible types
            (e.g., int matches int32, int64, etc.).

        Returns
        -------
        bool
            True if schema matches annotations, False otherwise.
        """
        import types
        from typing import Union, get_args, get_origin

        import ibis.expr.datatypes as dt
        from ibis.expr.types import Column

        # Get type hints for this class
        hints = get_type_hints(type(self))

        # Check each annotated field that exists in the schema
        # Note: We only validate fields present in the schema, allowing for
        # projections and selections that may have a subset of fields
        for field_name in self._field_names:
            # Skip if field not in annotations
            if field_name not in hints:
                continue

            # Skip if field doesn't exist in schema (could be a projection)
            if field_name not in schema:
                continue

            # Get the annotation and schema type
            annotation = hints[field_name]
            schema_type = schema[field_name]

            # Handle Union types (e.g., int | None for nullable fields)
            actual_type = annotation

            # Check if it's a Union type (including | syntax and Union[] syntax)
            origin = get_origin(annotation)
            if origin is Union or isinstance(annotation, types.UnionType):
                # Get the non-None type from the union
                args = get_args(annotation)
                non_none_types = [arg for arg in args if arg is not type(None)]
                if len(non_none_types) == 1:
                    actual_type = non_none_types[0]

            # Convert annotation to expected Ibis datatype category
            # Handle Ibis Column types (e.g., IntegerColumn, StringColumn)
            if isinstance(actual_type, type) and issubclass(actual_type, Column):
                # Map Column types to their corresponding datatype classes
                column_type_map = {
                    "IntegerColumn": dt.Integer,
                    "StringColumn": dt.String,
                    "FloatingColumn": dt.Floating,
                    "BooleanColumn": dt.Boolean,
                    "DateColumn": dt.Date,
                    "TimestampColumn": dt.Timestamp,
                    "DecimalColumn": dt.Decimal,
                }
                expected_type_class = column_type_map.get(actual_type.__name__)
                if expected_type_class is None:
                    # Unknown column type, skip validation for this field
                    continue

                # Check if schema type is instance of expected type
                if not isinstance(schema_type, expected_type_class):
                    return False

            # Handle Python native types
            elif actual_type is int:
                if strict:
                    # In strict mode, we'd need to know the exact type
                    # For now, just check it's an integer type
                    if not isinstance(schema_type, dt.Integer):
                        return False
                else:
                    # Non-strict: accept any integer type
                    if not isinstance(schema_type, dt.Integer):
                        return False

            elif actual_type is str:
                if not isinstance(schema_type, dt.String):
                    return False

            elif actual_type is float:
                if strict:
                    # In strict mode, check for specific floating type
                    if not isinstance(schema_type, dt.Floating):
                        return False
                else:
                    # Non-strict: accept any floating type
                    if not isinstance(schema_type, dt.Floating):
                        return False

            elif actual_type is bool:
                if not isinstance(schema_type, dt.Boolean):
                    return False

            else:
                # Try to convert the annotation to an Ibis dtype and compare
                try:
                    from ibis.expr.datatypes import dtype as make_dtype

                    expected_dtype = make_dtype(actual_type)

                    if strict:
                        # Strict mode: types must match exactly
                        if type(expected_dtype) is not type(schema_type):
                            return False
                    else:
                        # Non-strict: check if they're compatible
                        # (same base class, e.g., both Integer)
                        if not isinstance(schema_type, type(expected_dtype)):
                            if not isinstance(expected_dtype, type(schema_type)):
                                return False
                except Exception:
                    # If we can't convert, skip validation for this field
                    continue

        return True

    # ==================== Core Query Methods ====================

    def filter(
        self,
        *predicates: ir.Value
        | bool
        | Sequence[ir.Value | bool]
        | Callable[[Any], bool],
    ) -> Self:
        """Filter rows based on boolean predicates.

        Parameters
        ----------
        predicates
            Boolean expressions to filter rows.

        Returns
        -------
        Self
            Filtered table.

        Examples
        --------
        >>> UserTable.filter(UserTable.age > 25)
        >>> UserTable.filter(UserTable.age > 25, UserTable.is_active)
        """
        result = self._ibis_table.filter(*predicates)  # type: ignore[arg-type]
        return type(self)(result)

    def select(
        self,
        *exprs: ir.Value | str | Iterable[ir.Value | str],
        **named_exprs: ir.Value | str,
    ) -> Self:
        """Select columns or expressions from the table.

        Parameters
        ----------
        exprs
            Column names, column expressions, or iterables of these.
        named_exprs
            Named expressions to add as new columns.

        Returns
        -------
        Self
            Table with selected columns.

        Examples
        --------
        >>> UserTable.select("name", "email")
        >>> UserTable.select(UserTable.name, UserTable.age + 1)
        """
        result = self._ibis_table.select(*exprs, **named_exprs)
        return type(self)(result)

    def aggregate(
        self,
        metrics: ir.Scalar | Sequence[ir.Scalar] | None = (),
        /,
        **kw_metrics: ir.Scalar,
    ) -> Self:
        """Aggregate the table.

        Parameters
        ----------
        metrics
            Aggregate expressions.
        kw_metrics
            Named aggregate expressions.

        Returns
        -------
        Self
            Aggregated table.

        Examples
        --------
        >>> UserTable.aggregate(avg_age=UserTable.age.mean())
        >>> UserTable.aggregate([UserTable.age.mean(), UserTable.age.max()])
        """
        result = self._ibis_table.aggregate(metrics, **kw_metrics)  # type: ignore[arg-type]
        return type(self)(result)

    def order_by(
        self,
        *by: str | ir.Column | tuple[str | ir.Column, bool],
    ) -> Self:
        """Sort the table by one or more expressions.

        Parameters
        ----------
        by
            Column names, expressions, or (expr, ascending) tuples.

        Returns
        -------
        Self
            Sorted table.

        Examples
        --------
        >>> UserTable.order_by("age")
        >>> UserTable.order_by(UserTable.age.desc())
        """
        result = self._ibis_table.order_by(*by)  # type: ignore[arg-type]
        return type(self)(result)

    def limit(self, n: int | None, /, *, offset: int = 0) -> Self:
        """Select a limited number of rows.

        Parameters
        ----------
        n
            Number of rows to select. If None, no limit is applied.
        offset
            Number of rows to skip before starting selection.

        Returns
        -------
        Self
            Table with at most n rows.

        Examples
        --------
        >>> UserTable.limit(10)
        >>> UserTable.limit(10, offset=5)
        """
        result = self._ibis_table.limit(n, offset=offset)
        return type(self)(result)

    def head(self, n: int = 5, /) -> Self:
        """Select the first n rows.

        Parameters
        ----------
        n
            Number of rows to select.

        Returns
        -------
        Self
            Table with first n rows.

        Examples
        --------
        >>> UserTable.head()
        >>> UserTable.head(10)
        """
        result = self._ibis_table.head(n)
        return type(self)(result)

    def mutate(self, *exprs: ir.Value, **mutations: ir.Value | str) -> Self:
        """Add or modify columns.

        Parameters
        ----------
        exprs
            Column expressions.
        mutations
            Named column expressions.

        Returns
        -------
        Self
            Table with added/modified columns.

        Examples
        --------
        >>> UserTable.mutate(age_plus_one=UserTable.age + 1)
        >>> UserTable.mutate(UserTable.name.upper().name("name_upper"))
        """
        result = self._ibis_table.mutate(*exprs, **mutations)
        return type(self)(result)

    def distinct(
        self,
        *,
        on: str | Iterable[str] | Selector | None = None,
    ) -> Self:
        """Remove duplicate rows.

        Parameters
        ----------
        on
            Optional columns to consider for uniqueness.

        Returns
        -------
        Self
            Table with unique rows.

        Examples
        --------
        >>> UserTable.distinct()
        >>> UserTable.distinct(on="email")
        """
        result = self._ibis_table.distinct(on=on)
        return type(self)(result)

    def group_by(
        self,
        *by: str | ir.Value | Iterable[str | ir.Value],
    ) -> TypedGroupedTable:
        """Group the table by one or more expressions.

        Parameters
        ----------
        by
            Grouping expressions or column names.

        Returns
        -------
        TypedGroupedTable
            Grouped table for aggregation.

        Examples
        --------
        >>> UserTable.group_by("country").aggregate(count=UserTable.count())
        >>> UserTable.group_by(UserTable.age > 25).aggregate(avg_age=UserTable.age.mean())
        """
        result = self._ibis_table.group_by(*by)  # type: ignore[arg-type]
        return TypedGroupedTable(result, type(self))

    def join(
        self,
        right: Table | SemanticModel,
        predicates: (
            str
            | Sequence[
                str
                | ir.BooleanColumn
                | Literal[True]
                | Literal[False]
                | tuple[
                    str | ir.Column | ir.Deferred,
                    str | ir.Column | ir.Deferred,
                ]
                | ir.BooleanValue
            ]
        ) = (),
        *,
        how: Literal[
            "inner", "left", "right", "outer", "asof", "semi", "anti"
        ] = "inner",
        lname: str = "",
        rname: str = "{name}_right",
    ) -> Self:
        """Join this table with another table.

        Parameters
        ----------
        right
            Table to join with.
        predicates
            Join conditions.
        how
            Join type: 'inner', 'left', 'outer', 'right', etc.
        lname
            Template for renaming duplicate left columns.
        rname
            Template for renaming duplicate right columns.

        Returns
        -------
        Self
            Joined table.

        Examples
        --------
        >>> UserTable.join(OrdersTable, UserTable.id == OrdersTable.user_id)
        """
        # Unwrap SemanticModel if necessary
        right_table = right._ibis_table if isinstance(right, SemanticModel) else right
        result = self._ibis_table.join(  # type: ignore[arg-type]
            right_table, predicates, how=how, lname=lname, rname=rname
        )
        return type(self)(result)

    def left_join(
        self,
        right: Table | SemanticModel,
        predicates: (
            str
            | Sequence[
                str
                | ir.BooleanColumn
                | Literal[True]
                | Literal[False]
                | tuple[
                    str | ir.Column | ir.Deferred,
                    str | ir.Column | ir.Deferred,
                ]
                | ir.BooleanValue
            ]
        ) = (),
        *,
        lname: str = "",
        rname: str = "{name}_right",
    ) -> Self:
        """Left outer join with another table.

        Parameters
        ----------
        right
            Table to join with.
        predicates
            Join conditions.
        lname
            Template for renaming duplicate left columns.
        rname
            Template for renaming duplicate right columns.

        Returns
        -------
        Self
            Joined table.

        Examples
        --------
        >>> UserTable.left_join(OrdersTable, UserTable.id == OrdersTable.user_id)
        """
        right_table = right._ibis_table if isinstance(right, SemanticModel) else right
        result = self._ibis_table.left_join(  # type: ignore[arg-type]
            right_table, predicates, lname=lname, rname=rname
        )
        return type(self)(result)

    def inner_join(
        self,
        right: Table | SemanticModel,
        predicates: (
            str
            | Sequence[
                str
                | ir.BooleanColumn
                | Literal[True]
                | Literal[False]
                | tuple[
                    str | ir.Column | ir.Deferred,
                    str | ir.Column | ir.Deferred,
                ]
                | ir.BooleanValue
            ]
        ) = (),
        *,
        lname: str = "",
        rname: str = "{name}_right",
    ) -> Self:
        """Inner join with another table.

        Parameters
        ----------
        right
            Table to join with.
        predicates
            Join conditions.
        lname
            Template for renaming duplicate left columns.
        rname
            Template for renaming duplicate right columns.

        Returns
        -------
        Self
            Joined table.

        Examples
        --------
        >>> UserTable.inner_join(OrdersTable, UserTable.id == OrdersTable.user_id)
        """
        right_table = right._ibis_table if isinstance(right, SemanticModel) else right
        result = self._ibis_table.inner_join(  # type: ignore[arg-type]
            right_table, predicates, lname=lname, rname=rname
        )
        return type(self)(result)

    def asof_join(
        self,
        right: Table | SemanticModel,
        on: str | ir.BooleanColumn,
        predicates: str | ir.BooleanColumn | Sequence[str | ir.BooleanColumn] = (),
        *,
        tolerance: ir.IntervalScalar | None = None,
        lname: str = "",
        rname: str = "{name}_right",
    ) -> Self:
        """Perform an as-of join with another table.

        Parameters
        ----------
        right
            Table to join with.
        on
            Join conditions (typically inequality on time column).
        predicates
            Additional columns that must match exactly.
        tolerance
            Maximum time difference allowed.
        lname
            Template for renaming duplicate left columns.
        rname
            Template for renaming duplicate right columns.

        Returns
        -------
        Self
            Joined table.

        Examples
        --------
        >>> TicksTable.asof_join(TradesTable, TicksTable.time >= TradesTable.time, "symbol")
        """
        right_table = right._ibis_table if isinstance(right, SemanticModel) else right
        result = self._ibis_table.asof_join(  # type: ignore[arg-type]
            right_table, on, predicates, tolerance=tolerance, lname=lname, rname=rname
        )
        return type(self)(result)

    def count(self) -> ir.IntegerScalar:
        """Count the number of rows in the table.

        Returns
        -------
        IntegerScalar
            Number of rows.

        Examples
        --------
        >>> UserTable.count()
        """
        return self._ibis_table.count()

    def execute(self, **kwargs: Any):
        """Execute the table expression and return results.

        Parameters
        ----------
        kwargs
            Backend-specific execution parameters.

        Returns
        -------
        DataFrame or other result type
            Materialized query results.

        Examples
        --------
        >>> UserTable.filter(UserTable.age > 25).execute()
        """
        return self._ibis_table.execute(**kwargs)

    # ==================== Schema & Metadata Methods ====================

    @property
    def columns(self) -> tuple[str, ...]:
        """Return column names as a tuple.

        Returns
        -------
        tuple[str, ...]
            Tuple of column names.

        Examples
        --------
        >>> UserTable.columns
        ('id', 'name', 'email', 'age')
        """
        return self._ibis_table.columns

    def schema(self) -> sch.Schema:
        """Return the schema of the table.

        Returns
        -------
        Schema
            The table schema with column names and types.

        Examples
        --------
        >>> UserTable.schema()
        ibis.Schema {
          id     int64
          name   string
          email  string
          age    int64
        }
        """
        return self._ibis_table.schema()

    def get_name(self) -> str:
        """Return the fully qualified name of the table.

        Returns
        -------
        str
            Fully qualified table name (catalog.database.table).

        Examples
        --------
        >>> UserTable.get_name()
        'main.public.users'
        """
        return self._ibis_table.get_name()

    def info(self) -> Self:
        """Return summary information about the table.

        Returns
        -------
        Self
            Table with schema information (name, type, nullable).

        Examples
        --------
        >>> UserTable.info()
        """
        result = self._ibis_table.info()
        return type(self)(result)

    # ==================== Set Operations ====================

    def union(
        self,
        table: Table | SemanticModel,
        /,
        *rest: Table | SemanticModel,
        distinct: bool = False,
    ) -> Self:
        """Compute the union of multiple tables.

        Parameters
        ----------
        table
            Table to union with.
        rest
            Additional tables to union.
        distinct
            If True, remove duplicate rows.

        Returns
        -------
        Self
            Union of all tables.

        Examples
        --------
        >>> UserTable.union(OtherUsersTable)
        >>> UserTable.union(Table1, Table2, distinct=True)
        """
        # Unwrap SemanticModel if necessary
        unwrapped_table = (
            table._ibis_table if isinstance(table, SemanticModel) else table
        )
        unwrapped_rest = tuple(
            t._ibis_table if isinstance(t, SemanticModel) else t for t in rest
        )
        result = self._ibis_table.union(
            unwrapped_table, *unwrapped_rest, distinct=distinct
        )
        return type(self)(result)

    def intersect(
        self,
        table: Table | SemanticModel,
        /,
        *rest: Table | SemanticModel,
        distinct: bool = True,
    ) -> Self:
        """Compute the intersection of multiple tables.

        Parameters
        ----------
        table
            Table to intersect with.
        rest
            Additional tables to intersect.
        distinct
            If True, remove duplicate rows.

        Returns
        -------
        Self
            Intersection of all tables.

        Examples
        --------
        >>> UserTable.intersect(ActiveUsersTable)
        """
        unwrapped_table = (
            table._ibis_table if isinstance(table, SemanticModel) else table
        )
        unwrapped_rest = tuple(
            t._ibis_table if isinstance(t, SemanticModel) else t for t in rest
        )
        result = self._ibis_table.intersect(
            unwrapped_table, *unwrapped_rest, distinct=distinct
        )
        return type(self)(result)

    def difference(
        self,
        table: Table | SemanticModel,
        /,
        *rest: Table | SemanticModel,
        distinct: bool = True,
    ) -> Self:
        """Compute the difference of multiple tables.

        Parameters
        ----------
        table
            Table to subtract.
        rest
            Additional tables to subtract.
        distinct
            If True, remove duplicate rows.

        Returns
        -------
        Self
            Rows in self that are not in other tables.

        Examples
        --------
        >>> AllUsersTable.difference(InactiveUsersTable)
        """
        unwrapped_table = (
            table._ibis_table if isinstance(table, SemanticModel) else table
        )
        unwrapped_rest = tuple(
            t._ibis_table if isinstance(t, SemanticModel) else t for t in rest
        )
        result = self._ibis_table.difference(
            unwrapped_table, *unwrapped_rest, distinct=distinct
        )
        return type(self)(result)

    # ==================== Data Manipulation ====================

    def drop(self, *fields: str | Selector) -> Self:
        """Remove columns from the table.

        Parameters
        ----------
        fields
            Column names or selectors to drop.

        Returns
        -------
        Self
            Table without specified columns.

        Examples
        --------
        >>> UserTable.drop("temp_column")
        >>> UserTable.drop("col1", "col2", "col3")
        """
        result = self._ibis_table.drop(*fields)
        return type(self)(result)

    def fill_null(self, replacements: Any | Mapping[str, Any], /) -> Self:
        """Fill null values in the table.

        Parameters
        ----------
        replacements
            Scalar value or dict mapping column names to replacement values.

        Returns
        -------
        Self
            Table with nulls filled.

        Examples
        --------
        >>> UserTable.fill_null(0)
        >>> UserTable.fill_null({"age": 0, "name": "Unknown"})
        """
        result = self._ibis_table.fill_null(replacements)
        return type(self)(result)

    def fillna(self, replacements: Any | dict[str, Any], /) -> Self:
        """Fill null values (alias for fill_null).

        Parameters
        ----------
        replacements
            Scalar value or dict mapping column names to replacement values.

        Returns
        -------
        Self
            Table with nulls filled.

        Examples
        --------
        >>> UserTable.fillna(0)
        """
        result = self._ibis_table.fillna(replacements)
        return type(self)(result)

    def unpack(self, *columns: str) -> Self:
        """Unpack struct columns into individual columns.

        Parameters
        ----------
        columns
            Names of struct columns to unpack.

        Returns
        -------
        Self
            Table with struct fields unpacked as separate columns.

        Examples
        --------
        >>> UserTable.unpack("address")  # Unpacks address.street, address.city, etc.
        """
        result = self._ibis_table.unpack(*columns)
        return type(self)(result)

    # ==================== Type Casting ====================

    def cast(self, schema: Any, /) -> Self:
        """Cast columns to specified types.

        Parameters
        ----------
        schema
            Schema-like object or dict mapping columns to types.

        Returns
        -------
        Self
            Table with columns cast to new types.

        Examples
        --------
        >>> UserTable.cast({"age": "int32", "score": "float64"})
        """
        result = self._ibis_table.cast(schema)
        return type(self)(result)

    def try_cast(self, schema: Any, /) -> Self:
        """Attempt to cast columns, returning null on failure.

        Parameters
        ----------
        schema
            Schema-like object or dict mapping columns to types.

        Returns
        -------
        Self
            Table with columns cast to new types (nulls where cast failed).

        Examples
        --------
        >>> UserTable.try_cast({"age": "int32"})
        """
        result = self._ibis_table.try_cast(schema)
        return type(self)(result)

    # ==================== Special Operations ====================

    def view(self) -> Self:
        """Create a view of the table for self-referencing operations.

        Returns
        -------
        Self
            New table expression for self-joins.

        Examples
        --------
        >>> UserTable.join(UserTable.view(), ...)  # Self-join
        """
        result = self._ibis_table.view()
        return type(self)(result)

    def alias(self, alias: str, /) -> Self:
        """Give the table an alias.

        Parameters
        ----------
        alias
            Alias name for the table.

        Returns
        -------
        Self
            Aliased table expression.

        Examples
        --------
        >>> UserTable.alias("u")
        """
        result = self._ibis_table.alias(alias)
        return type(self)(result)

    def cache(self) -> Self:
        """Cache the table expression.

        Returns
        -------
        Self
            Cached table expression.

        Examples
        --------
        >>> cached_users = UserTable.filter(UserTable.age > 25).cache()
        """
        result = self._ibis_table.cache()
        return type(self)(result)

    def window_by(self, time_col: str | ir.Value, /) -> TypedWindowedTable:
        """Create a windowed table for time-based operations.

        Parameters
        ----------
        time_col
            Time column name or expression.

        Returns
        -------
        TypedWindowedTable
            Windowed table for time-series operations.

        Examples
        --------
        >>> UserTable.window_by("created_at")
        """
        result = self._ibis_table.window_by(time_col)
        return TypedWindowedTable(result, type(self))

    # ==================== Data Sampling & Inspection ====================

    def sample(
        self,
        fraction: float,
        /,
        *,
        method: Literal["row", "block"] = "row",
        seed: int | None = None,
    ) -> Self:
        """Sample a fraction of rows randomly.

        Parameters
        ----------
        fraction
            Fraction of rows to sample (0.0 to 1.0).
        method
            Sampling method: 'row' or 'block'.
        seed
            Random seed for reproducibility.

        Returns
        -------
        Self
            Randomly sampled table.

        Examples
        --------
        >>> UserTable.sample(0.1)  # 10% sample
        >>> UserTable.sample(0.25, seed=42)  # Reproducible
        """
        result = self._ibis_table.sample(fraction, method=method, seed=seed)
        return type(self)(result)

    def value_counts(self, *, name: str | None = None) -> Self:
        """Compute frequency of each unique row.

        Parameters
        ----------
        name
            Name for the count column.

        Returns
        -------
        Self
            Table with unique rows and their counts.

        Examples
        --------
        >>> UserTable.select("country").value_counts()
        >>> UserTable.select("status").value_counts(name="frequency")
        """
        result = self._ibis_table.value_counts(name=name)
        return type(self)(result)

    def topk(self, k: int | None = None, *, name: str | None = None) -> Self:
        """Get the top K most frequent values.

        Parameters
        ----------
        k
            Number of top values to return. None returns all.
        name
            Name for the count column.

        Returns
        -------
        Self
            Table with top K most frequent values.

        Examples
        --------
        >>> UserTable.select("country").topk(10)
        >>> UserTable.select("category").topk(5, name="count")
        """
        result = self._ibis_table.topk(k, name=name)
        return type(self)(result)

    # ==================== Type Conversion ====================

    def to_array(self) -> ir.Column:
        """Convert single-column table to array column.

        Returns
        -------
        Column
            Array column expression.

        Examples
        --------
        >>> UserTable.select("id").to_array()
        """
        return self._ibis_table.to_array()

    def as_scalar(self) -> ir.Scalar:
        """Convert single-value table to scalar.

        The table must have exactly one column and one row.

        Returns
        -------
        Scalar
            Scalar value expression.

        Examples
        --------
        >>> UserTable.aggregate(max_age=UserTable.age.max()).select("max_age").as_scalar()
        """
        return self._ibis_table.as_scalar()

    def as_table(self) -> Self:
        """Ensure this expression is a table.

        This is a no-op for table expressions but ensures type.

        Returns
        -------
        Self
            This table (no-op).

        Examples
        --------
        >>> expr.as_table()
        """
        result = self._ibis_table.as_table()
        return type(self)(result)

    # ==================== SQL & Advanced ====================

    def sql(self, query: str, /, *, dialect: str | None = None) -> Self:
        """Execute SQL query on this table.

        Parameters
        ----------
        query
            SQL query string. Use 'self' to reference this table.
        dialect
            SQL dialect to use.

        Returns
        -------
        Self
            Result of SQL query.

        Examples
        --------
        >>> UserTable.sql("SELECT * FROM self WHERE age > 25")
        >>> UserTable.sql("SELECT name, age FROM self ORDER BY age DESC", dialect="duckdb")
        """
        result = self._ibis_table.sql(query, dialect=dialect)
        return type(self)(result)

    # ==================== Column Operations ====================

    def rename(
        self,
        *args: str | dict[str, str],
        **kwargs: str,
    ) -> Self:
        """Rename columns in the table.

        Parameters
        ----------
        args
            Renaming method or mapping dict.
        kwargs
            Column name mappings (new_name=old_name).

        Returns
        -------
        Self
            Table with renamed columns.

        Examples
        --------
        >>> UserTable.rename(user_id="id", full_name="name")
        >>> UserTable.rename({"id": "user_id", "name": "full_name"})
        """
        result = self._ibis_table.rename(*args, **kwargs)
        return type(self)(result)

    def relocate(
        self,
        *columns: str | Selector,
        before: str | Selector | None = None,
        after: str | Selector | None = None,
        **kwargs: str,
    ) -> Self:
        """Relocate columns to different positions.

        Parameters
        ----------
        columns
            Columns to relocate.
        before
            Column to insert before.
        after
            Column to insert after.
        kwargs
            Additional column specifications.

        Returns
        -------
        Self
            Table with relocated columns.

        Examples
        --------
        >>> UserTable.relocate("id", before="name")
        >>> UserTable.relocate("email", after="name")
        """
        result = self._ibis_table.relocate(
            *columns, before=before, after=after, **kwargs
        )
        return type(self)(result)

    # ==================== Properties & Special ====================

    @property
    def rowid(self) -> ir.IntegerValue:
        """Get row identifier column.

        Returns a unique integer per row.

        Returns
        -------
        IntegerValue
            Row identifier column.

        Examples
        --------
        >>> UserTable.rowid
        >>> UserTable.select(UserTable.rowid, UserTable.name)
        """
        return self._ibis_table.rowid  # type: ignore[return-value]

    def __contains__(self, name: str) -> bool:
        """Check if column exists in the table.

        Parameters
        ----------
        name
            Column name to check.

        Returns
        -------
        bool
            True if column exists, False otherwise.

        Examples
        --------
        >>> "age" in UserTable
        True
        >>> "nonexistent" in UserTable
        False
        """
        return name in self._ibis_table

    def __len__(self) -> int:
        """Prevent calling len() on lazy table.

        Raises
        ------
        TypeError
            Always raised with helpful message.

        Examples
        --------
        >>> len(UserTable)  # Raises TypeError
        TypeError: Use .count().execute() instead of len()
        """
        raise TypeError(
            "Cannot call len() on a lazy table expression. "
            "Use table.count().execute() to get the row count."
        )

    # ==================== Delegation ====================

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying ibis table.

        This enables access to columns and any ibis methods not explicitly wrapped.
        """
        # Get the attribute from the ibis table
        attr = getattr(self._ibis_table, name)

        # If it's a callable (method), wrap it to return Self when appropriate
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                # If the result is a Table, wrap it in this model class
                if isinstance(result, Table):
                    return type(self)(result)
                # If the result is a GroupedTable, wrap it in TypedGroupedTable
                elif isinstance(result, GroupedTable):
                    return TypedGroupedTable(result, type(self))
                return result

            return wrapped_method

        return attr

    def __getitem__(self, key):
        """Delegate indexing to the underlying ibis table."""
        return self._ibis_table[key]

    def __dir__(self):
        """Show attributes from both this class and the underlying table."""
        base_attrs = list(set(dir(self._ibis_table) + list(object.__dir__(self))))
        # Add field names for autocomplete
        base_attrs.extend(self._field_names)
        return list(set(base_attrs))

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{type(self).__name__}({self._ibis_table})"

    def __setattr__(self, name: str, value: Any):
        """Prevent attribute setting on the wrapper."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(
                f"Cannot set attribute {name} on {self.__class__.__name__}"
            )


# For backwards compatibility, export TypedTable as an alias
TypedTable = SemanticModel
