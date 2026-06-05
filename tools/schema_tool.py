import os  # Read DATABASE_URL and other settings from the environment
import re  # Validate table names so we only run safe SQL

from dotenv import load_dotenv  # Load variables from the project .env file
from sqlalchemy import create_engine, inspect, text  # Connect to PostgreSQL and run queries

load_dotenv()  # Make DATABASE_URL available before we read it

DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL connection string (same as the FastAPI app)
if not DATABASE_URL:  # Fail fast if the database URL was not configured
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")  # Helpful message for setup

engine = create_engine(DATABASE_URL)  # Reusable connection pool to PostgreSQL


def _safe_table_name(table_name: str) -> str:
    """Allow only names that match our upload sanitization (letters, digits, underscores)."""
    name = table_name.strip().lower()  # Normalize input to lowercase PostgreSQL-style names
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):  # Reject names that could break SQL or inject code
        raise ValueError(f"Invalid table name: {table_name!r}")  # Tell the caller the name is not allowed
    return name  # Return the validated table name for queries


def get_schema(table_name: str) -> str:
    """
    Build a human-readable schema summary for an AI agent (e.g. Gemini).

    Includes column names, data types, total row count, and three example rows.
    """
    safe_name = _safe_table_name(table_name)  # Validate before any SQL uses the table name

    inspector = inspect(engine)  # SQLAlchemy helper to read database metadata
    if safe_name not in inspector.get_table_names(schema="public"):  # Check the table exists in public schema
        return f"Table '{safe_name}' was not found in the database."  # Clear message when the name is wrong

    columns = inspector.get_columns(safe_name, schema="public")  # List of dicts: name, type, nullable, etc.

    with engine.connect() as conn:  # Open one connection for the queries below
        row_count = conn.execute(  # Run a COUNT query for the full table size
            text(f"SELECT COUNT(*) FROM {safe_name}")  # safe_name is validated; safe to embed
        ).scalar()  # Fetch the single integer result
        sample_result = conn.execute(  # Fetch a few rows for the agent to see real values
            text(f"SELECT * FROM {safe_name} LIMIT 3")  # Only three rows to keep context small
        )
        sample_rows = sample_result.mappings().all()  # Rows as dict-like objects (column -> value)

    lines: list[str] = []  # Collect output lines before joining into one string
    lines.append(f"Table: {safe_name}")  # Header: which table this description is for
    lines.append(f"Row count: {row_count}")  # Total number of rows in the table
    lines.append("")  # Blank line for readability
    lines.append("Columns (name | data type):")  # Section header for schema
    for col in columns:  # One line per column from inspector metadata
        col_name = col["name"]  # Column name in PostgreSQL
        col_type = str(col["type"])  # SQLAlchemy type object as a readable string
        lines.append(f"  - {col_name} | {col_type}")  # Bullet line for the agent
    lines.append("")  # Blank line before sample data
    lines.append("Sample rows (up to 3):")  # Section header for example data
    if not sample_rows:  # Table exists but has zero rows
        lines.append("  (no rows)")  # Note empty table
    else:  # Format each sample row for the LLM
        for i, row in enumerate(sample_rows, start=1):  # Number rows 1, 2, 3
            pairs = [f"{key}={value!r}" for key, value in row.items()]  # key='value' for each column
            lines.append(f"  Row {i}: " + ", ".join(pairs))  # Single line per row

    return "\n".join(lines)  # One formatted string to pass as Gemini context
