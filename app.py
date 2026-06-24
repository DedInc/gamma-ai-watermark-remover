"""FastAPI entry point for the local Gamma watermark remover."""

import logging

from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes import APP_VERSION, router, templates
from utils.cleanup import create_lifespan, ensure_directories

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
CLEANUP_INTERVAL = 600
MAX_FILE_AGE = 3600

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

ensure_directories(UPLOAD_FOLDER, OUTPUT_FOLDER)

app = FastAPI(
    title="Gamma AI Watermark Remover",
    version=APP_VERSION,
    lifespan=create_lifespan(OUTPUT_FOLDER, CLEANUP_INTERVAL, MAX_FILE_AGE),
)
app.include_router(router)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> object:
    """Render HTTP errors as the main page with an error message."""
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"error_message": "Page not found."},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "index.html",
        {"error_message": f"Server error: {exc.detail}"},
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> object:
    """Catch unhandled exceptions and render a 500 error page."""
    return templates.TemplateResponse(
        request,
        "index.html",
        {"error_message": f"Internal server error: {exc}"},
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8999)
