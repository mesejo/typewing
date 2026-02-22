"""TypedBackend wrapper for Ibis backends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ibis.expr.types import Table

from typewing.model import SemanticModel


if TYPE_CHECKING:
    from ibis.backends.sql import SQLBackend


class TypedBackend:
    """Wrapper around an Ibis backend that returns TypedTable instances.

    This class wraps any Ibis backend connection and automatically wraps
    table-returning methods to return TypedTable instances instead of raw
    ibis Table objects.

    Example:
        ```python
        import ibis
        from typewing import TypedBackend, IbisModel

        class User(IbisModel):
            __tablename__ = "users"
            id: int
            name: str

        # Wrap a backend
        raw_con = ibis.duckdb.connect()
        con = TypedBackend(raw_con)

        # Get a typed table with explicit model
        UserTable = con.table('users', model=User)

        # UserTable is now a TypedTable with full type information
        result = UserTable.filter(UserTable.age > 18).execute()
        ```
    """

    def __init__(self, backend: SQLBackend):
        """Initialize the TypedBackend wrapper.

        Args:
            backend: The Ibis backend connection to wrap
        """
        self._backend = backend
        self._model_registry: dict[str, type[SemanticModel]] = {}

    def table(
        self, name: str, /, *, model: type[SemanticModel] | None = None
    ) -> SemanticModel:
        """Get a table from the backend as a SemanticModel instance.

        Args:
            name: Name of the table to load
            model: Optional SemanticModel class to use for typing. If not provided,
                   will look up in the model registry.

        Returns:
            SemanticModel instance wrapping the ibis Table

        Example:
            ```python
            # With explicit model
            UserTable = con.table('users', model=User)

            # With registered model
            con.register_model(User)
            UserTable = con.table('users')  # Uses registered User model
            ```
        """
        # Get the raw ibis table
        ibis_table = self._backend.table(name)

        # Determine which model to use
        if model is None:
            # Try to find in registry
            model = self._model_registry.get(name)

        if model is None:
            # No model provided and not in registry - return base SemanticModel
            return SemanticModel(ibis_table)

        # Instantiate the model class
        return model(ibis_table)

    def register_model(
        self, model_class: type[SemanticModel], table_name: str | None = None
    ) -> None:
        """Register a model for automatic typing.

        Args:
            model_class: The IbisModel class to register
            table_name: Optional table name. If not provided, will use
                       model's get_table_name() method.

        Example:
            ```python
            con.register_model(User)  # Register with default table name
            con.register_model(User, "custom_users")  # Register with custom name
            ```
        """
        table_name = table_name or model_class.get_table_name()
        self._model_registry[table_name] = model_class

    def with_models(self, *model_classes: type[SemanticModel]) -> TypedBackend:
        """Register multiple models at once.

        Args:
            *model_classes: IbisModel classes to register

        Returns:
            Self for method chaining

        Example:
            ```python
            con.with_models(User, Product, Order)
            ```
        """
        for model_class in model_classes:
            self.register_model(model_class)
        return self

    def _wrap_result(
        self, result: Any, model_class: type[SemanticModel] | None = None
    ) -> Any:
        """Wrap a result if it's a Table.

        Args:
            result: The result to potentially wrap
            model_class: Optional model class to use for typing

        Returns:
            SemanticModel instance if result is a Table, otherwise the original result
        """
        if isinstance(result, Table):
            if model_class is None:
                # Return base SemanticModel instance
                return SemanticModel(result)
            # Instantiate the model class
            return model_class(result)
        return result

    def sql(
        self, query: str, /, *, model: type[SemanticModel] | None = None, **kwargs: Any
    ) -> SemanticModel:
        """Execute SQL query and return a SemanticModel instance.

        Args:
            query: SQL query string
            model: Optional SemanticModel class to use for typing
            **kwargs: Additional arguments passed to backend.sql()

        Returns:
            SemanticModel instance wrapping the query result

        Example:
            ```python
            # With model
            result = con.sql("SELECT * FROM users WHERE age > 18", model=User)

            # Without model
            result = con.sql("SELECT * FROM users")
            ```
        """
        result = self._backend.sql(query, **kwargs)
        return self._wrap_result(result, model)  # type: ignore[return-value]

    def read_csv(
        self, path: str, /, *, model: type[SemanticModel] | None = None, **kwargs: Any
    ) -> SemanticModel:
        """Read CSV file and return a SemanticModel instance.

        Args:
            path: Path to CSV file
            model: Optional SemanticModel class to use for typing
            **kwargs: Additional arguments passed to backend.read_csv()

        Returns:
            SemanticModel instance wrapping the CSV data
        """
        result = self._backend.read_csv(path, **kwargs)
        return self._wrap_result(result, model)  # type: ignore[return-value]

    def read_parquet(
        self, path: str, /, *, model: type[SemanticModel] | None = None, **kwargs: Any
    ) -> SemanticModel:
        """Read Parquet file and return a SemanticModel instance.

        Args:
            path: Path to Parquet file
            model: Optional SemanticModel class to use for typing
            **kwargs: Additional arguments passed to backend.read_parquet()

        Returns:
            SemanticModel instance wrapping the Parquet data
        """
        result = self._backend.read_parquet(path, **kwargs)
        return self._wrap_result(result, model)  # type: ignore[return-value]

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to the underlying backend.

        This enables the TypedBackend to act as a transparent proxy for
        the underlying Ibis backend, while automatically wrapping table-returning
        methods.
        """
        attr = getattr(self._backend, name)

        # If it's a callable, wrap it to automatically wrap table results
        if callable(attr):

            def wrapped_method(*args, **kwargs):
                # Extract model parameter if provided
                model = kwargs.pop("model", None)

                # Call the underlying method
                result = attr(*args, **kwargs)

                # If result is a Table, wrap it
                if isinstance(result, Table):
                    return self._wrap_result(result, model)

                return result

            return wrapped_method

        return attr

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TypedBackend({self._backend})"
