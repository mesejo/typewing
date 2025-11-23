"""Type-safe wrappers for Ibis datatypes and columns."""

from typing import Generic, TypeVar, Union

from ibis.expr.datatypes import (
    Float16,
    Float32,
    Float64,
    Int8,
    Int16,
    Int32,
    Int64,
    UInt8,
    UInt16,
    UInt32,
    UInt64,
)
from ibis.expr.types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    DateColumn,
    DecimalColumn,
    FloatingColumn,
    IntegerColumn,
    IntervalColumn,
    JSONColumn,
    MapColumn,
    SetColumn,
    StringColumn,
    StructColumn,
    TimeColumn,
    TimestampColumn,
    UUIDColumn,
)


IntegerType = Union[Int8, Int16, Int32, Int64]
T_Integer = TypeVar("T_Integer", bound=IntegerType)


class Integer(IntegerColumn, Generic[T_Integer]):
    """Type-safe signed integer column.

    Generic parameter specifies the exact integer width:
    - Int8: 8-bit signed integer
    - Int16: 16-bit signed integer
    - Int32: 32-bit signed integer
    - Int64: 64-bit signed integer

    Example:
        class MyTable(TypedTable):
            small_num: Integer[Int8]
            medium_num: Integer[Int16]
            large_num: Integer[Int64]
    """

    pass


UnsignedIntegerType = Union[UInt8, UInt16, UInt32, UInt64]
T_UnsignedInteger = TypeVar("T_UnsignedInteger", bound=UnsignedIntegerType)


class UnsignedInteger(IntegerColumn, Generic[T_UnsignedInteger]):
    """Type-safe unsigned integer column.

    Generic parameter specifies the exact integer width:
    - UInt8: 8-bit unsigned integer
    - UInt16: 16-bit unsigned integer
    - UInt32: 32-bit unsigned integer
    - UInt64: 64-bit unsigned integer

    Example:
        class MyTable(TypedTable):
            counter: UnsignedInteger[UInt32]
            id: UnsignedInteger[UInt64]
    """

    pass


FloatingType = Union[Float16, Float32, Float64]
T_Floating = TypeVar("T_Floating", bound=FloatingType)


class Floating(FloatingColumn, Generic[T_Floating]):
    """Type-safe floating point column.

    Generic parameter specifies the exact float precision:
    - Float16: 16-bit floating point (half precision)
    - Float32: 32-bit floating point (single precision)
    - Float64: 64-bit floating point (double precision)

    Example:
        class MyTable(TypedTable):
            temperature: Floating[Float32]
            precise_value: Floating[Float64]
    """

    pass


class String(StringColumn):
    """Type-safe string column."""

    pass


class Boolean(BooleanColumn):
    """Type-safe boolean column."""

    pass


class Date(DateColumn):
    """Type-safe date column."""

    pass


class Time(TimeColumn):
    """Type-safe time column."""

    pass


class Timestamp(TimestampColumn):
    """Type-safe timestamp column."""

    pass


class Decimal(DecimalColumn):
    """Type-safe decimal column."""

    pass


class Binary(BinaryColumn):
    """Type-safe binary column."""

    pass


class Array(ArrayColumn):
    """Type-safe array column."""

    pass


class Map(MapColumn):
    """Type-safe map column."""

    pass


class Struct(StructColumn):
    """Type-safe struct column."""

    pass


class Set(SetColumn):
    """Type-safe set column."""

    pass


class JSON(JSONColumn):
    """Type-safe JSON column."""

    pass


class UUID(UUIDColumn):
    """Type-safe UUID column."""

    pass


class Interval(IntervalColumn):
    """Type-safe interval column."""

    pass
