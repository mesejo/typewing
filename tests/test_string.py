"""Tests for string operations with TypedTable on DuckDB.

Tests common string operations like upper, lower, contains, strip, replace, etc.
"""

from __future__ import annotations

import ibis
import pytest

from typewing import SemanticModel
from typewing.model import TypedTable


class TextData(SemanticModel):
    """Model for text data."""

    __tablename__ = "texts"

    id: int
    text: str
    description: str | None


@pytest.fixture
def duckdb_con():
    """Create a DuckDB connection with test data."""
    con = ibis.duckdb.connect()

    # Create texts table
    con.raw_sql(
        """
        CREATE TABLE texts (
            id INTEGER,
            text VARCHAR,
            description VARCHAR
        )
        """
    )

    # Insert test data
    con.raw_sql(
        """
        INSERT INTO texts VALUES
            (1, 'Hello World', 'greeting'),
            (2, 'PYTHON', 'language'),
            (3, '  spaces  ', 'whitespace'),
            (4, 'test123', 'alphanumeric'),
            (5, 'Hello Python', 'combined'),
            (6, 'abc', 'lowercase'),
            (7, 'ABC', 'uppercase'),
            (8, '', NULL)
        """
    )

    yield con
    con.disconnect()


def test_string_upper_lower(duckdb_con):
    """Test upper() and lower() methods."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text.upper().name("upper_text"),
            TextTable.text.lower().name("lower_text"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    # Check "Hello World" conversion
    row1 = result[result["id"] == 1].iloc[0]
    assert row1["upper_text"] == "HELLO WORLD"
    assert row1["lower_text"] == "hello world"

    # Check "PYTHON" conversion
    row2 = result[result["id"] == 2].iloc[0]
    assert row2["lower_text"] == "python"


def test_string_contains(duckdb_con):
    """Test contains() method."""
    TextTable = TextData.bind(duckdb_con)

    # Filter using contains
    query = TextTable.filter(TextTable.text.contains("Python"))

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) == 1
    assert result.iloc[0]["text"] == "Hello Python"


def test_string_strip(duckdb_con):
    """Test strip(), lstrip(), rstrip() methods."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text.strip().name("stripped"),
            TextTable.text.lstrip().name("lstripped"),
            TextTable.text.rstrip().name("rstripped"),
        ]
    ).filter(TextTable.id == 3)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["stripped"] == "spaces"
    assert row["lstripped"] == "spaces  "
    assert row["rstripped"] == "  spaces"


def test_string_length(duckdb_con):
    """Test length() method."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [TextTable.id, TextTable.text, TextTable.text.length().name("text_length")]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    # "Hello World" has 11 characters
    row = result[result["id"] == 1].iloc[0]
    assert row["text_length"] == 11


def test_string_concat(duckdb_con):
    """Test string concatenation."""
    TextTable = TextData.bind(duckdb_con)

    # Test column + literal
    query1 = TextTable.select(
        [TextTable.id, (TextTable.text + " suffix").name("with_suffix")]
    ).filter(TextTable.id == 6)

    assert isinstance(query1, TypedTable)
    result1 = query1.execute()
    assert result1.iloc[0]["with_suffix"] == "abc suffix"

    # Test literal + column
    query2 = TextTable.select(
        [TextTable.id, ("prefix " + TextTable.text).name("with_prefix")]
    ).filter(TextTable.id == 6)

    assert isinstance(query2, TypedTable)
    result2 = query2.execute()
    assert result2.iloc[0]["with_prefix"] == "prefix abc"

    # Test column + column
    query3 = TextTable.select(
        [
            TextTable.id,
            (TextTable.text + " - " + TextTable.description).name("combined"),
        ]
    ).filter(TextTable.id == 1)

    assert isinstance(query3, TypedTable)
    result3 = query3.execute()
    assert result3.iloc[0]["combined"] == "Hello World - greeting"


def test_string_substr(duckdb_con):
    """Test substr() method."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text.substr(0, 5).name("first_five"),
            TextTable.text.substr(6).name("from_six"),
        ]
    ).filter(TextTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["first_five"] == "Hello"
    assert row["from_six"] == "World"


def test_string_slicing(duckdb_con):
    """Test string slicing with bracket notation."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text[0:5].name("slice_start"),
            TextTable.text[6:].name("slice_end"),
            TextTable.text[1].name("single_char"),
        ]
    ).filter(TextTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["slice_start"] == "Hello"
    assert row["slice_end"] == "World"
    assert row["single_char"] == "e"


def test_string_replace(duckdb_con):
    """Test replace() method."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [TextTable.id, TextTable.text.replace("Python", "Java").name("replaced")]
    ).filter(TextTable.id == 5)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["replaced"] == "Hello Java"


def test_string_startswith_endswith(duckdb_con):
    """Test startswith() and endswith() methods."""
    TextTable = TextData.bind(duckdb_con)

    # Filter with startswith
    query1 = TextTable.filter(TextTable.text.startswith("Hello"))
    assert isinstance(query1, TypedTable)
    result1 = query1.execute()
    assert len(result1) == 2  # "Hello World" and "Hello Python"

    # Filter with endswith
    query2 = TextTable.filter(TextTable.text.endswith("World"))
    assert isinstance(query2, TypedTable)
    result2 = query2.execute()
    assert len(result2) == 1
    assert result2.iloc[0]["text"] == "Hello World"


def test_string_find(duckdb_con):
    """Test find() method."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text,
            TextTable.text.find("World").name("position"),
        ]
    ).filter(TextTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    # "World" starts at position 6 in "Hello World"
    assert result.iloc[0]["position"] == 6


def test_string_lpad_rpad(duckdb_con):
    """Test lpad() and rpad() methods."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text.lpad(10, "-").name("lpadded"),
            TextTable.text.rpad(10, "-").name("rpadded"),
        ]
    ).filter(TextTable.id == 6)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["lpadded"] == "-------abc"
    assert row["rpadded"] == "abc-------"


def test_string_reverse(duckdb_con):
    """Test reverse() method."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [TextTable.id, TextTable.text.reverse().name("reversed")]
    ).filter(TextTable.id == 6)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["reversed"] == "cba"


def test_string_repeat(duckdb_con):
    """Test repeat() method."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [TextTable.id, TextTable.text.repeat(3).name("repeated")]
    ).filter(TextTable.id == 6)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["repeated"] == "abcabcabc"


def test_string_left_right(duckdb_con):
    """Test left() and right() methods."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text.left(5).name("leftmost"),
            TextTable.text.right(5).name("rightmost"),
        ]
    ).filter(TextTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["leftmost"] == "Hello"
    assert row["rightmost"] == "World"


def test_string_like(duckdb_con):
    """Test like() method with pattern matching."""
    TextTable = TextData.bind(duckdb_con)

    # Find texts that start with "Hello"
    query = TextTable.filter(TextTable.text.like("Hello%"))

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert len(result) == 2  # "Hello World" and "Hello Python"


def test_string_operations_chained(duckdb_con):
    """Test chaining multiple string operations."""
    TextTable = TextData.bind(duckdb_con)

    # Chain: strip, upper, replace
    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text.strip().upper().replace("SPACES", "CLEANED").name("result"),
        ]
    ).filter(TextTable.id == 3)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["result"] == "CLEANED"


def test_string_with_mutate(duckdb_con):
    """Test string operations with mutate."""
    TextTable = TextData.bind(duckdb_con)

    query = TextTable.mutate(
        uppercase=TextTable.text.upper(),
        length=TextTable.text.length(),
        starts_with_hello=TextTable.text.startswith("Hello"),
    ).filter(TextTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    row = result.iloc[0]
    assert row["uppercase"] == "HELLO WORLD"
    assert row["length"] == 11
    assert row["starts_with_hello"]


def test_string_literal_operations(duckdb_con):
    """Test string operations on literals."""
    # Test with literal strings
    expr1 = ibis.literal("hello").upper()
    result1 = duckdb_con.execute(expr1)
    assert result1 == "HELLO"

    expr2 = ibis.literal("  trim  ").strip()
    result2 = duckdb_con.execute(expr2)
    assert result2 == "trim"

    expr3 = ibis.literal("test").repeat(2)
    result3 = duckdb_con.execute(expr3)
    assert result3 == "testtest"


def test_string_concat_with_join(duckdb_con):
    """Test string join operation."""
    # Test ibis.literal().join() with array
    expr = ibis.literal("-").join(["a", "b", "c"])
    result = duckdb_con.execute(expr)
    assert result == "a-b-c"


def test_string_split(duckdb_con):
    """Test split() method."""
    TextTable = TextData.bind(duckdb_con)

    # Split on space
    query = TextTable.select(
        [TextTable.id, TextTable.text.split(" ").name("parts")]
    ).filter(TextTable.id == 1)

    assert isinstance(query, TypedTable)

    result = query.execute()
    parts = result.iloc[0]["parts"]
    assert list(parts) == ["Hello", "World"]


def test_string_re_search(duckdb_con):
    """Test re_search() for regex matching."""
    TextTable = TextData.bind(duckdb_con)

    # Search for digits
    query = TextTable.select(
        [
            TextTable.id,
            TextTable.text,
            TextTable.text.re_search(r"\d+").name("has_digit"),
        ]
    )

    assert isinstance(query, TypedTable)

    result = query.execute()
    # "test123" should match
    row = result[result["id"] == 4].iloc[0]
    assert row["has_digit"]


def test_string_re_extract(duckdb_con):
    """Test re_extract() for extracting patterns."""
    TextTable = TextData.bind(duckdb_con)

    # Extract digits
    query = TextTable.select(
        [TextTable.id, TextTable.text.re_extract(r"(\d+)", 0).name("digits")]
    ).filter(TextTable.id == 4)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["digits"] == "123"


def test_string_re_replace(duckdb_con):
    """Test re_replace() for regex replacement."""
    TextTable = TextData.bind(duckdb_con)

    # Replace digits with "X"
    query = TextTable.select(
        [TextTable.id, TextTable.text.re_replace(r"\d+", "X").name("replaced")]
    ).filter(TextTable.id == 4)

    assert isinstance(query, TypedTable)

    result = query.execute()
    assert result.iloc[0]["replaced"] == "testX"
