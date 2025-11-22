"""Core model classes for typewing."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Iterable,
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

T = TypeVar("T", bound="IbisModel")


class Field:
    """Field definition for IbisModel attributes.

    Args:
        description: Field description for documentation
        alias: Column name in the database table (if different from field name)
    """

    def __init__(
        self,
        *,
        description: str | None = None,
        alias: str | None = None,
    ):
        self.description = description
        self.alias = alias


class FieldDescriptor:
    """Descriptor for model fields that enables access on both class and instances.

    This descriptor allows field access on:
    1. The model class itself (for hasattr checks and IDE autocomplete)
    2. TypedTable instances (returns the actual column)
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

        # If accessed from a TypedTable instance, return the column
        if isinstance(obj, TypedTable):
            col_name = obj._model_class.get_column_name(self.field_name)
            return obj._ibis_table[col_name]

        # For other cases, just return self
        return self

    def __set__(self, obj, value):
        """Prevent setting field values."""
        raise AttributeError(f"Cannot set field '{self.field_name}' on model class")

    def __repr__(self):
        """Return string representation."""
        return f"FieldDescriptor({self.field_name!r})"


class ModelMeta(type):
    """Metaclass for IbisModel that handles field registration."""

    def __new__(mcs, name: str, bases: tuple, namespace: dict, **kwargs):
        # Create the class first
        cls = super().__new__(mcs, name, bases, namespace)

        # Skip for the base IbisModel class itself
        if name == "IbisModel":
            return cls

        # Get type hints for this class only (not inherited)
        if hasattr(cls, "__annotations__"):
            hints = get_type_hints(cls)
        else:
            hints = {}

        # Store field metadata
        cls._fields_metadata = {}
        cls._table_name = namespace.get("__tablename__")

        # Process each annotated field
        for field_name, field_type in hints.items():
            if field_name.startswith("_"):
                continue

            # Get the field value if it exists
            field_value = (
                getattr(cls, field_name, None) if field_name in namespace else None
            )

            metadata = {
                "type": field_type,
                "alias": None,
                "description": None,
            }

            # If it's a Field instance, extract metadata
            if isinstance(field_value, Field):
                metadata["alias"] = field_value.alias
                metadata["description"] = field_value.description

            cls._fields_metadata[field_name] = metadata

        # Now add class-level descriptors for each field
        # This enables IDE autocomplete on the class itself
        for field_name in cls._fields_metadata.keys():
            if not hasattr(cls, field_name) or isinstance(
                getattr(cls, field_name, None), Field
            ):
                # Create a descriptor that provides documentation
                descriptor = FieldDescriptor(field_name)
                setattr(cls, field_name, descriptor)

        return cls


class TypedGroupedTable:
    """Wrapper around an Ibis GroupedTable that preserves type information.

    This class delegates all attribute access to the underlying Ibis GroupedTable
    while ensuring that methods returning Table objects are wrapped in TypedTable.
    """

    def __init__(self, grouped_table: GroupedTable, model_class: type[IbisModel]):
        object.__setattr__(self, "_grouped_table", grouped_table)
        object.__setattr__(self, "_model_class", model_class)

    def __getattr__(self, name: str):
        """Delegate attribute access to the underlying grouped table."""
        attr = getattr(self._grouped_table, name)

        # If it's a callable (method), wrap it to return TypedTable when appropriate
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                # If the result is a Table, wrap it in TypedTable
                if isinstance(result, Table):
                    return TypedTable(result, self._model_class)
                return result

            return wrapped_method

        return attr

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TypedGroupedTable({self._grouped_table})"


class TypedWindowedTable:
    """Wrapper around an Ibis WindowedTable that preserves type information.

    This class delegates all attribute access to the underlying Ibis WindowedTable
    while ensuring that methods returning Table objects are wrapped in TypedTable.
    """

    def __init__(self, windowed_table: WindowedTable, model_class: type[IbisModel]):
        object.__setattr__(self, "_windowed_table", windowed_table)
        object.__setattr__(self, "_model_class", model_class)

    def __getattr__(self, name: str):
        """Delegate attribute access to the underlying windowed table."""
        attr = getattr(self._windowed_table, name)

        # If it's a callable (method), wrap it to return TypedTable when appropriate
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                # If the result is a Table, wrap it in TypedTable
                if isinstance(result, Table):
                    return TypedTable(result, self._model_class)
                return result

            return wrapped_method

        return attr

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TypedWindowedTable({self._windowed_table})"


class TypedTable:
    """Wrapper around an Ibis Table that preserves type information.

    This class delegates all attribute access to the underlying Ibis Table
    while maintaining type hints for IDE autocomplete.
    """

    def __init__(self, ibis_table: Table, model_class: type[IbisModel]):
        object.__setattr__(self, "_ibis_table", ibis_table)
        object.__setattr__(self, "_model_class", model_class)

        # Create properties for each field to enable typed access
        # Only set attributes for columns that actually exist in the table
        available_columns = set(ibis_table.columns)
        for field_name in model_class._fields_metadata.keys():
            if not hasattr(self.__class__, field_name):
                # Add the field as an attribute that returns the column
                col_name = model_class.get_column_name(field_name)
                # Only set if the column exists in the table
                if col_name in available_columns:
                    # Use object.__setattr__ to bypass our custom __setattr__
                    object.__setattr__(self, field_name, ibis_table[col_name])

    # ==================== Mirror Methods for IDE Autocomplete ====================
    # These methods explicitly mirror ibis Table methods to enable IDE autocomplete.
    # Each method delegates to _ibis_table and wraps the result appropriately.

    def filter(
        self,
        *predicates: ir.BooleanValue | bool | Sequence[ir.BooleanValue | bool],
    ) -> TypedTable:
        """Filter rows based on boolean predicates.

        Parameters
        ----------
        predicates
            Boolean expressions to filter rows.

        Returns
        -------
        TypedTable
            Filtered table.

        Examples
        --------
        >>> UserTable.filter(UserTable.age > 25)
        >>> UserTable.filter(UserTable.age > 25, UserTable.is_active)
        """
        result = self._ibis_table.filter(*predicates)
        return TypedTable(result, self._model_class)

    def select(
        self,
        *exprs: ir.Value | str | Iterable[ir.Value | str],
        **named_exprs: ir.Value | str,
    ) -> TypedTable:
        """Select columns or expressions from the table.

        Parameters
        ----------
        exprs
            Column names, column expressions, or iterables of these.
        named_exprs
            Named expressions to add as new columns.

        Returns
        -------
        TypedTable
            Table with selected columns.

        Examples
        --------
        >>> UserTable.select("name", "email")
        >>> UserTable.select(UserTable.name, UserTable.age + 1)
        """
        result = self._ibis_table.select(*exprs, **named_exprs)
        return TypedTable(result, self._model_class)

    def aggregate(
        self,
        metrics: ir.Scalar | Sequence[ir.Scalar] | None = (),
        /,
        **kw_metrics: ir.Scalar,
    ) -> TypedTable:
        """Aggregate the table.

        Parameters
        ----------
        metrics
            Aggregate expressions.
        kw_metrics
            Named aggregate expressions.

        Returns
        -------
        TypedTable
            Aggregated table.

        Examples
        --------
        >>> UserTable.aggregate(avg_age=UserTable.age.mean())
        >>> UserTable.aggregate([UserTable.age.mean(), UserTable.age.max()])
        """
        result = self._ibis_table.aggregate(metrics, **kw_metrics)
        return TypedTable(result, self._model_class)

    def order_by(
        self,
        *by: str | ir.Column | tuple[str | ir.Column, bool],
    ) -> TypedTable:
        """Sort the table by one or more expressions.

        Parameters
        ----------
        by
            Column names, expressions, or (expr, ascending) tuples.

        Returns
        -------
        TypedTable
            Sorted table.

        Examples
        --------
        >>> UserTable.order_by("age")
        >>> UserTable.order_by(UserTable.age.desc())
        """
        result = self._ibis_table.order_by(*by)
        return TypedTable(result, self._model_class)

    def limit(self, n: int | None, /, *, offset: int = 0) -> TypedTable:
        """Select a limited number of rows.

        Parameters
        ----------
        n
            Number of rows to select. If None, no limit is applied.
        offset
            Number of rows to skip before starting selection.

        Returns
        -------
        TypedTable
            Table with at most n rows.

        Examples
        --------
        >>> UserTable.limit(10)
        >>> UserTable.limit(10, offset=5)
        """
        result = self._ibis_table.limit(n, offset=offset)
        return TypedTable(result, self._model_class)

    def head(self, n: int = 5, /) -> TypedTable:
        """Select the first n rows.

        Parameters
        ----------
        n
            Number of rows to select.

        Returns
        -------
        TypedTable
            Table with first n rows.

        Examples
        --------
        >>> UserTable.head()
        >>> UserTable.head(10)
        """
        result = self._ibis_table.head(n)
        return TypedTable(result, self._model_class)

    def mutate(self, *exprs: ir.Value, **mutations: ir.Value | str) -> TypedTable:
        """Add or modify columns.

        Parameters
        ----------
        exprs
            Column expressions.
        mutations
            Named column expressions.

        Returns
        -------
        TypedTable
            Table with added/modified columns.

        Examples
        --------
        >>> UserTable.mutate(age_plus_one=UserTable.age + 1)
        >>> UserTable.mutate(UserTable.name.upper().name("name_upper"))
        """
        result = self._ibis_table.mutate(*exprs, **mutations)
        return TypedTable(result, self._model_class)

    def distinct(
        self,
        *,
        on: str | Iterable[str] | Selector | None = None,
    ) -> TypedTable:
        """Remove duplicate rows.

        Parameters
        ----------
        on
            Optional columns to consider for uniqueness.

        Returns
        -------
        TypedTable
            Table with unique rows.

        Examples
        --------
        >>> UserTable.distinct()
        >>> UserTable.distinct(on="email")
        """
        result = self._ibis_table.distinct(on=on)
        return TypedTable(result, self._model_class)

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
        result = self._ibis_table.group_by(*by)
        return TypedGroupedTable(result, self._model_class)

    def join(
        self,
        right: Table | TypedTable,
        predicates: ir.BooleanValue | Sequence[ir.BooleanValue] = (),
        *,
        how: str = "inner",
        lname: str = "",
        rname: str = "{name}_right",
    ) -> TypedTable:
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
        TypedTable
            Joined table.

        Examples
        --------
        >>> UserTable.join(OrdersTable, UserTable.id == OrdersTable.user_id)
        """
        # Unwrap TypedTable if necessary
        right_table = right._ibis_table if isinstance(right, TypedTable) else right
        result = self._ibis_table.join(
            right_table, predicates, how=how, lname=lname, rname=rname
        )
        return TypedTable(result, self._model_class)

    def left_join(
        self,
        right: Table | TypedTable,
        predicates: ir.BooleanValue | Sequence[ir.BooleanValue] = (),
        *,
        lname: str = "",
        rname: str = "{name}_right",
    ) -> TypedTable:
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
        TypedTable
            Joined table.

        Examples
        --------
        >>> UserTable.left_join(OrdersTable, UserTable.id == OrdersTable.user_id)
        """
        right_table = right._ibis_table if isinstance(right, TypedTable) else right
        result = self._ibis_table.left_join(
            right_table, predicates, lname=lname, rname=rname
        )
        return TypedTable(result, self._model_class)

    def inner_join(
        self,
        right: Table | TypedTable,
        predicates: ir.BooleanValue | Sequence[ir.BooleanValue] = (),
        *,
        lname: str = "",
        rname: str = "{name}_right",
    ) -> TypedTable:
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
        TypedTable
            Joined table.

        Examples
        --------
        >>> UserTable.inner_join(OrdersTable, UserTable.id == OrdersTable.user_id)
        """
        right_table = right._ibis_table if isinstance(right, TypedTable) else right
        result = self._ibis_table.inner_join(
            right_table, predicates, lname=lname, rname=rname
        )
        return TypedTable(result, self._model_class)

    def asof_join(
        self,
        right: Table | TypedTable,
        predicates: ir.BooleanValue | Sequence[ir.BooleanValue] = (),
        by: str | ir.Value | Sequence[str | ir.Value] = (),
        *,
        tolerance: ir.IntervalValue | None = None,
        lname: str = "",
        rname: str = "{name}_right",
    ) -> TypedTable:
        """Perform an as-of join with another table.

        Parameters
        ----------
        right
            Table to join with.
        predicates
            Join conditions (typically inequality on time column).
        by
            Additional columns that must match exactly.
        tolerance
            Maximum time difference allowed.
        lname
            Template for renaming duplicate left columns.
        rname
            Template for renaming duplicate right columns.

        Returns
        -------
        TypedTable
            Joined table.

        Examples
        --------
        >>> TicksTable.asof_join(TradesTable, TicksTable.time >= TradesTable.time, "symbol")
        """
        right_table = right._ibis_table if isinstance(right, TypedTable) else right
        result = self._ibis_table.asof_join(
            right_table, predicates, by, tolerance=tolerance, lname=lname, rname=rname
        )
        return TypedTable(result, self._model_class)

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

    # ==================== Phase 2: Schema & Metadata Methods ====================

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

    def info(self) -> TypedTable:
        """Return summary information about the table.

        Returns
        -------
        TypedTable
            Table with schema information (name, type, nullable).

        Examples
        --------
        >>> UserTable.info()
        """
        result = self._ibis_table.info()
        return TypedTable(result, self._model_class)

    # ==================== Phase 2: Set Operations ====================

    def union(
        self,
        table: Table | TypedTable,
        /,
        *rest: Table | TypedTable,
        distinct: bool = False,
    ) -> TypedTable:
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
        TypedTable
            Union of all tables.

        Examples
        --------
        >>> UserTable.union(OtherUsersTable)
        >>> UserTable.union(Table1, Table2, distinct=True)
        """
        # Unwrap TypedTable if necessary
        unwrapped_table = table._ibis_table if isinstance(table, TypedTable) else table
        unwrapped_rest = tuple(
            t._ibis_table if isinstance(t, TypedTable) else t for t in rest
        )
        result = self._ibis_table.union(
            unwrapped_table, *unwrapped_rest, distinct=distinct
        )
        return TypedTable(result, self._model_class)

    def intersect(
        self,
        table: Table | TypedTable,
        /,
        *rest: Table | TypedTable,
        distinct: bool = True,
    ) -> TypedTable:
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
        TypedTable
            Intersection of all tables.

        Examples
        --------
        >>> UserTable.intersect(ActiveUsersTable)
        """
        unwrapped_table = table._ibis_table if isinstance(table, TypedTable) else table
        unwrapped_rest = tuple(
            t._ibis_table if isinstance(t, TypedTable) else t for t in rest
        )
        result = self._ibis_table.intersect(
            unwrapped_table, *unwrapped_rest, distinct=distinct
        )
        return TypedTable(result, self._model_class)

    def difference(
        self,
        table: Table | TypedTable,
        /,
        *rest: Table | TypedTable,
        distinct: bool = True,
    ) -> TypedTable:
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
        TypedTable
            Rows in self that are not in other tables.

        Examples
        --------
        >>> AllUsersTable.difference(InactiveUsersTable)
        """
        unwrapped_table = table._ibis_table if isinstance(table, TypedTable) else table
        unwrapped_rest = tuple(
            t._ibis_table if isinstance(t, TypedTable) else t for t in rest
        )
        result = self._ibis_table.difference(
            unwrapped_table, *unwrapped_rest, distinct=distinct
        )
        return TypedTable(result, self._model_class)

    # ==================== Phase 2: Data Manipulation ====================

    def drop(self, *fields: str | Selector) -> TypedTable:
        """Remove columns from the table.

        Parameters
        ----------
        fields
            Column names or selectors to drop.

        Returns
        -------
        TypedTable
            Table without specified columns.

        Examples
        --------
        >>> UserTable.drop("temp_column")
        >>> UserTable.drop("col1", "col2", "col3")
        """
        result = self._ibis_table.drop(*fields)
        return TypedTable(result, self._model_class)

    def fill_null(
        self, replacements: ir.Scalar | dict[str, ir.Scalar], /
    ) -> TypedTable:
        """Fill null values in the table.

        Parameters
        ----------
        replacements
            Scalar value or dict mapping column names to replacement values.

        Returns
        -------
        TypedTable
            Table with nulls filled.

        Examples
        --------
        >>> UserTable.fill_null(0)
        >>> UserTable.fill_null({"age": 0, "name": "Unknown"})
        """
        result = self._ibis_table.fill_null(replacements)
        return TypedTable(result, self._model_class)

    def fillna(self, replacements: ir.Scalar | dict[str, ir.Scalar], /) -> TypedTable:
        """Fill null values (alias for fill_null).

        Parameters
        ----------
        replacements
            Scalar value or dict mapping column names to replacement values.

        Returns
        -------
        TypedTable
            Table with nulls filled.

        Examples
        --------
        >>> UserTable.fillna(0)
        """
        result = self._ibis_table.fillna(replacements)
        return TypedTable(result, self._model_class)

    def unpack(self, *columns: str) -> TypedTable:
        """Unpack struct columns into individual columns.

        Parameters
        ----------
        columns
            Names of struct columns to unpack.

        Returns
        -------
        TypedTable
            Table with struct fields unpacked as separate columns.

        Examples
        --------
        >>> UserTable.unpack("address")  # Unpacks address.street, address.city, etc.
        """
        result = self._ibis_table.unpack(*columns)
        return TypedTable(result, self._model_class)

    # ==================== Phase 2: Type Casting ====================

    def cast(self, schema: Any, /) -> TypedTable:
        """Cast columns to specified types.

        Parameters
        ----------
        schema
            Schema-like object or dict mapping columns to types.

        Returns
        -------
        TypedTable
            Table with columns cast to new types.

        Examples
        --------
        >>> UserTable.cast({"age": "int32", "score": "float64"})
        """
        result = self._ibis_table.cast(schema)
        return TypedTable(result, self._model_class)

    def try_cast(self, schema: Any, /) -> TypedTable:
        """Attempt to cast columns, returning null on failure.

        Parameters
        ----------
        schema
            Schema-like object or dict mapping columns to types.

        Returns
        -------
        TypedTable
            Table with columns cast to new types (nulls where cast failed).

        Examples
        --------
        >>> UserTable.try_cast({"age": "int32"})
        """
        result = self._ibis_table.try_cast(schema)
        return TypedTable(result, self._model_class)

    # ==================== Phase 2: Special Operations ====================

    def view(self) -> TypedTable:
        """Create a view of the table for self-referencing operations.

        Returns
        -------
        TypedTable
            New table expression for self-joins.

        Examples
        --------
        >>> UserTable.join(UserTable.view(), ...)  # Self-join
        """
        result = self._ibis_table.view()
        return TypedTable(result, self._model_class)

    def alias(self, alias: str, /) -> TypedTable:
        """Give the table an alias.

        Parameters
        ----------
        alias
            Alias name for the table.

        Returns
        -------
        TypedTable
            Aliased table expression.

        Examples
        --------
        >>> UserTable.alias("u")
        """
        result = self._ibis_table.alias(alias)
        return TypedTable(result, self._model_class)

    def cache(self) -> TypedTable:
        """Cache the table expression.

        Returns
        -------
        TypedTable
            Cached table expression.

        Examples
        --------
        >>> cached_users = UserTable.filter(UserTable.age > 25).cache()
        """
        result = self._ibis_table.cache()
        return TypedTable(result, self._model_class)

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
        return TypedWindowedTable(result, self._model_class)

    # ==================== Phase 3: Data Sampling & Inspection ====================

    # Note: tail() is not available in standard ibis Table API
    # It will work via __getattr__ fallback if backend supports it

    def sample(
        self,
        fraction: float,
        /,
        *,
        method: str = "row",
        seed: int | None = None,
    ) -> TypedTable:
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
        TypedTable
            Randomly sampled table.

        Examples
        --------
        >>> UserTable.sample(0.1)  # 10% sample
        >>> UserTable.sample(0.25, seed=42)  # Reproducible
        """
        result = self._ibis_table.sample(fraction, method=method, seed=seed)
        return TypedTable(result, self._model_class)

    def value_counts(self, *, name: str | None = None) -> TypedTable:
        """Compute frequency of each unique row.

        Parameters
        ----------
        name
            Name for the count column.

        Returns
        -------
        TypedTable
            Table with unique rows and their counts.

        Examples
        --------
        >>> UserTable.select("country").value_counts()
        >>> UserTable.select("status").value_counts(name="frequency")
        """
        result = self._ibis_table.value_counts(name=name)
        return TypedTable(result, self._model_class)

    def topk(self, k: int | None = None, *, name: str | None = None) -> TypedTable:
        """Get the top K most frequent values.

        Parameters
        ----------
        k
            Number of top values to return. None returns all.
        name
            Name for the count column.

        Returns
        -------
        TypedTable
            Table with top K most frequent values.

        Examples
        --------
        >>> UserTable.select("country").topk(10)
        >>> UserTable.select("category").topk(5, name="count")
        """
        result = self._ibis_table.topk(k, name=name)
        return TypedTable(result, self._model_class)

    # ==================== Phase 3: Type Conversion ====================

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

    def as_table(self) -> TypedTable:
        """Ensure this expression is a table.

        This is a no-op for table expressions but ensures type.

        Returns
        -------
        TypedTable
            This table (no-op).

        Examples
        --------
        >>> expr.as_table()
        """
        result = self._ibis_table.as_table()
        return TypedTable(result, self._model_class)

    # ==================== Phase 3: SQL & Advanced ====================

    def sql(self, query: str, /, *, dialect: str | None = None) -> TypedTable:
        """Execute SQL query on this table.

        Parameters
        ----------
        query
            SQL query string. Use 'self' to reference this table.
        dialect
            SQL dialect to use.

        Returns
        -------
        TypedTable
            Result of SQL query.

        Examples
        --------
        >>> UserTable.sql("SELECT * FROM self WHERE age > 25")
        >>> UserTable.sql("SELECT name, age FROM self ORDER BY age DESC", dialect="duckdb")
        """
        result = self._ibis_table.sql(query, dialect=dialect)
        return TypedTable(result, self._model_class)

    # ==================== Phase 3: Column Operations ====================

    def rename(
        self,
        *args: str | dict[str, str],
        **kwargs: str,
    ) -> TypedTable:
        """Rename columns in the table.

        Parameters
        ----------
        args
            Renaming method or mapping dict.
        kwargs
            Column name mappings (new_name=old_name).

        Returns
        -------
        TypedTable
            Table with renamed columns.

        Examples
        --------
        >>> UserTable.rename(user_id="id", full_name="name")
        >>> UserTable.rename({"id": "user_id", "name": "full_name"})
        """
        result = self._ibis_table.rename(*args, **kwargs)
        return TypedTable(result, self._model_class)

    def relocate(
        self,
        *columns: str | Selector,
        before: str | Selector | None = None,
        after: str | Selector | None = None,
        **kwargs: str,
    ) -> TypedTable:
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
        TypedTable
            Table with relocated columns.

        Examples
        --------
        >>> UserTable.relocate("id", before="name")
        >>> UserTable.relocate("email", after="name")
        """
        result = self._ibis_table.relocate(
            *columns, before=before, after=after, **kwargs
        )
        return TypedTable(result, self._model_class)

    # ==================== Phase 3: Properties & Special ====================

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
        return self._ibis_table.rowid

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

    # ==================== End Mirror Methods ====================

    def __getattr__(self, name: str):
        """Delegate attribute access to the underlying ibis table.

        Handles field name to column name translation for aliased fields.
        """
        # Check if this is a model field that might have an alias
        if hasattr(self, "_model_class") and name in self._model_class._fields_metadata:
            col_name = self._model_class.get_column_name(name)
            return self._ibis_table[col_name]

        # Get the attribute from the ibis table
        attr = getattr(self._ibis_table, name)

        # If it's a callable (method), wrap it to return TypedTable when appropriate
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                result = attr(*args, **kwargs)
                # If the result is a Table, wrap it in TypedTable
                if isinstance(result, Table):
                    return TypedTable(result, self._model_class)
                # If the result is a GroupedTable, wrap it in TypedGroupedTable
                elif isinstance(result, GroupedTable):
                    return TypedGroupedTable(result, self._model_class)
                return result

            return wrapped_method

        return attr

    def __getitem__(self, key):
        """Delegate indexing to the underlying ibis table."""
        return self._ibis_table[key]

    def __dir__(self):
        """Show attributes from both this class and the underlying table."""
        base_attrs = list(set(dir(self._ibis_table) + list(object.__dir__(self))))
        # Add model field names for autocomplete
        if hasattr(self, "_model_class"):
            base_attrs.extend(self._model_class.get_field_names())
        return list(set(base_attrs))

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self._model_class.__name__}({self._ibis_table})"

    def __setattr__(self, name: str, value: Any):
        """Prevent attribute setting on the wrapper."""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            raise AttributeError(
                f"Cannot set attribute {name} on {self.__class__.__name__}"
            )


class IbisModel(metaclass=ModelMeta):
    """Base class for typed Ibis tables with SQLModel-like behavior.

    Define your table schema using type annotations, then bind to a connection
    to get a fully-typed Table that preserves all Ibis query building capabilities.

    Example:
        ```python
        from typewing import IbisModel, Field
        import ibis

        class User(IbisModel):
            __tablename__ = "users"

            id: int
            name: str
            email: str
            age: int | None = Field(description="User's age in years")

        # Bind to a connection - returns a typed Table
        con = ibis.duckdb.connect()
        UserTable = User.bind(con)

        # All Ibis operations work with full type safety
        query = UserTable.filter(UserTable.age > 18).select("name", "email")

        # IDE autocomplete works
        print(UserTable.name)  # Column access
        result = query.execute()  # Execute query
        ```
    """

    _fields_metadata: ClassVar[dict[str, dict[str, Any]]] = {}
    _table_name: ClassVar[str | None] = None

    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        if cls._table_name:
            return cls._table_name
        # Default to lowercase class name
        return cls.__name__.lower()

    @classmethod
    def get_column_name(cls, field_name: str) -> str:
        """Get the database column name for a field."""
        metadata = cls._fields_metadata.get(field_name, {})
        return metadata.get("alias") or field_name

    @classmethod
    def bind(
        cls: type[T], connection: Any, table_name: str | None = None
    ) -> TypedTable:
        """Bind this model to an ibis connection and return a typed Table.

        Args:
            connection: Ibis connection object (e.g., ibis.duckdb.connect())
            table_name: Optional table name override

        Returns:
            A TypedTable that wraps the ibis Table with type information

        Example:
            ```python
            con = ibis.duckdb.connect()
            UserTable = User.bind(con)

            # Now you can use it like any ibis Table
            query = UserTable.filter(UserTable.age > 18)
            results = query.execute()
            ```
        """
        table_name = table_name or cls.get_table_name()

        # Get the actual ibis table
        ibis_table = connection.table(table_name)

        # Return a typed wrapper
        return TypedTable(ibis_table, cls)

    @classmethod
    def get_fields(cls) -> dict[str, dict[str, Any]]:
        """Get all field metadata for this model."""
        return cls._fields_metadata.copy()

    @classmethod
    def get_field_names(cls) -> list[str]:
        """Get list of all field names."""
        return list(cls._fields_metadata.keys())

    @classmethod
    def get_field_types(cls) -> dict[str, type]:
        """Get mapping of field names to their Python types."""
        return {name: meta["type"] for name, meta in cls._fields_metadata.items()}
