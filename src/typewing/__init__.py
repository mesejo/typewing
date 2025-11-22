from typewing.model import IbisModel, Field

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata

__all__ = ["IbisModel", "Field"]
__version__ = importlib_metadata.version(__package__)
