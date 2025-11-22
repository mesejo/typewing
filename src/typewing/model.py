"""Core model classes for typewing."""

from __future__ import annotations

from typing import Any, ClassVar, TypeVar, get_type_hints

from ibis.expr.types import Table
from ibis.expr.types.groupby import GroupedTable

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
            field_value = getattr(cls, field_name, None) if field_name in namespace else None

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
            if not hasattr(cls, field_name) or isinstance(getattr(cls, field_name, None), Field):
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
            raise AttributeError(f"Cannot set attribute {name} on {self.__class__.__name__}")


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
    def bind(cls: type[T], connection: Any, table_name: str | None = None) -> TypedTable:
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
