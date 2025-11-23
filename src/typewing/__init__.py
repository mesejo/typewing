from typewing.backend import TypedBackend
from typewing.model import SemanticModel, TypedTable


try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__all__ = ["SemanticModel", "TypedBackend", "TypedTable"]
__version__ = importlib_metadata.version(__package__ or "typewing")
