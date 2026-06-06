import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text
import io

from tools.schema_tool import get_schema
from agents.graph.graph import graph
from agents.state import GraphState

load_dotenv()

# Create FastAPI app
app = FastAPI(title="Autonomous Data Analyst API")

# Allow React frontend at localhost:3000 to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to PostgreSQL
engine = create_engine(os.getenv("DATABASE_URL"))


# ─── REQUEST MODELS ───────────────────────────────────────────

class InvestigateRequest(BaseModel):
    question: str        # The user's natural language question
    dataset_name: str    # The PostgreSQL table name to query


# ─── ENDPOINTS ────────────────────────────────────────────────

@app.get("/")
def root():
    # Health check — visit http://127.0.0.1:8000 to confirm API is running
    return {"status": "running", "message": "Autonomous Data Analyst API"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    # Read the uploaded CSV file into memory
    contents = await file.read()

    # Parse CSV with Pandas
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {str(e)}")

    # Clean the table name — remove spaces, lowercase, strip .csv extension
    raw_name = file.filename.replace(".csv", "")
    table_name = raw_name.lower().strip().replace(" ", "_").replace("-", "_")
    # Remove any character that is not a letter, number, or underscore
    table_name = "".join(c for c in table_name if c.isalnum() or c == "_")

    # Write the DataFrame to PostgreSQL as a new table
    try:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save to database: {str(e)}")

    return {
        "table_name": table_name,
        "rows": len(df),
        "columns": df.columns.tolist(),
        "message": f"Successfully uploaded {len(df)} rows into table '{table_name}'"
    }


@app.get("/datasets")
def list_datasets():
    # Return all uploaded tables with their row counts
    try:
        with engine.connect() as conn:
            # Get all table names from PostgreSQL
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]

            # Get row count for each table
            datasets = []
            for table in tables:
                count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
                datasets.append({"table_name": table, "row_count": count})

        return {"datasets": datasets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/investigate")
def investigate(request: InvestigateRequest):
    # Get schema for the requested table
    schema = get_schema(request.dataset_name)

    # Check if table exists — schema_tool returns an error string if not found
    if schema.startswith("Error") or schema.startswith("Table not found"):
        raise HTTPException(status_code=404, detail=f"Dataset '{request.dataset_name}' not found")

    # Build initial state for the LangGraph graph
    initial_state = GraphState(
        user_question=request.question,
        dataset_name=request.dataset_name,
        schema_context=schema,
        generated_sql="",
        sql_result="",
        error="",
        retry_count=0,
        needs_chart=False,
        needs_stats=False,
        chart_json="",
        stats_result="",
        insight="",
        final_answer=""
    )

    # Run the full agent graph
    try:
        result = graph.invoke(initial_state)
    except Exception as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
            raise HTTPException(
                status_code=429,
                detail=(
                    "Gemini API rate limit reached. Each question uses several AI calls. "
                    "Wait a minute and try again, or upgrade your Google AI API quota."
                ),
            )
        raise HTTPException(status_code=500, detail=f"Agent error: {err}")

    # Return all agent outputs to the frontend
    return {
        "question": request.question,
        "dataset": request.dataset_name,
        "sql": result["generated_sql"],
        "sql_result": result["sql_result"],
        "chart_json": result["chart_json"],
        "stats": result["stats_result"],
        "insight": result["final_answer"],
        "retry_count": result["retry_count"],
        "error": result["error"]
    }