import io
import json
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    HealthResponse, 
    setup_logging, 
    ProcessConfig, 
    ProcessingReport, 
    log_requests, 
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport
)
from data_pipeline import create_cleaning_report, process_data, validate_dataframe

from src.storage import MOVIE_COLUMNS

logger = logging.getLogger(__name__)
setup_logging(verbose=True)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    return HealthResponse(status="ok", version="1.0.0")

@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    """Read a CSV upload and replace the stored movie collection."""
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix != ".csv":
        logger.warning(f"Unsupported file format: {suffix}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{suffix}'. Please upload a .csv file.",
        )

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        logger.warning(f"Empty CSV upload: {filename}")
        raise HTTPException(status_code=400, detail="The CSV file is empty.")
    except pd.errors.ParserError as e:
        logger.warning(f"CSV parse error in {filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")
    except UnicodeDecodeError:
        logger.warning(f"Encoding error in {filename}")
        raise HTTPException(status_code=400, detail="The file could not be decoded.")

    if sorted(df.columns) != sorted(MOVIE_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain exactly these columns: {MOVIE_COLUMNS}",
        )
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV contains no data rows")
    df = df[MOVIE_COLUMNS]

    storage.save(df)
    logger.info(f"Uploaded movies: filename={filename}, rows={len(df)}")
    return MovieUploadInfo(
        filename=filename,
        rows=len(df),
        columns=len(df.columns),
        column_names=list(df.columns),
    )
    
#MOVIES REPLACE DATASETS:

@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    data = storage.select_columns(MOVIE_COLUMNS, limit=limit)
    total_rows = storage.count_movies()
    logger.info(f"Retrieved movies: returned_rows={len(data)}, total_rows={total_rows}")
    return {"data": data, "total_rows": total_rows}

@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1),
    ):
    try:
        results = storage.query_movies(columns, min_rating, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    logger.info(
        f"Queried movies: columns={columns}, min_rating={min_rating}, "
        f"returned_rows={len(results)}"
    )
    return results

@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    """Validate and process the stored movies using MP1 functions."""
    data = storage.get()
    if data.empty:
        logger.warning("Process requested but no movies are stored")
        raise HTTPException(status_code=400, detail="No movies stored")

    config_dict = config.model_dump()
    required_columns = config.validation.required_columns
    numeric_columns = config.validation.numeric_columns

    missing = [c for c in numeric_columns if c not in data.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Numeric columns not found: {missing}")

    rows_before_validation = len(data)
    try:
        data = validate_dataframe(data, required_columns, numeric_columns)
        validation_removed = rows_before_validation - len(data)
        original = data.copy()
        cleaned = process_data(data, config_dict)
        report = create_cleaning_report(original, cleaned)
    except ValueError as error:
        logger.warning(f"Processing failed: {error}")
        raise HTTPException(status_code=400, detail=str(error))

    storage.save(cleaned)
    logger.info(
        f"Processed movies: validation_removed={validation_removed}, "
        f"rows_before={report['rows_before']}, rows_after={report['rows_after']}"
    )
    return {
        "validation_rows_removed": validation_removed,
        "cleaning_report": report,
    }