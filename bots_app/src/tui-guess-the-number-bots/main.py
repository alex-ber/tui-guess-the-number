import structlog
from structlog.contextvars import clear_contextvars, bind_contextvars
from alexber.utils.structlog_setup import initConf as structLogInitConf
from alexber.utils import thread_locals

from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

import uvicorn
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)

def _configure_logging():
    structLogInitConf()
    #logging.getLogger("boto3").setLevel(logging.WARNING)


# Define the headers for CORS
cors_headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Credentials": "true"
}

async def cors_handling_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=cors_headers)

    response = await call_next(request)

    for key, value in cors_headers.items():
        response.headers[key] = value
    return response


async def structlog_middleware(request: Request, call_next):
    # Clear any garbage left by previous requests on this Keep-Alive connection
    clear_contextvars()

    # Bind context for the current request
    bind_contextvars(request_id="some-unique-id", path=request.url.path)

    try:
        response = await call_next(request)
        return response
    finally:
        # Clean up our own context so we do not pollute the next request
        clear_contextvars()



async def general_exception_handler(request: Request, exc: Exception):
    """
    Transparently converts unhandled Python exceptions (e.g., ValueError)
    into clean HTTP 500 JSON responses.
    """
    print("🔥 middleware reached")

    log.error("Unhandled bot exception", error=str(exc), path=request.url.path, exception_type=type(exc).__name__, exc_info=True)

    if isinstance(exc, HTTPException):
        log.error(f"HTTP Exception: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    return JSONResponse(
        status_code=500,
        content={
            "message": "An unexpected error occurred",
            "details": str(exc),
        }
    )


def initFastAPI(app: FastAPI):
    app.add_middleware(BaseHTTPMiddleware, dispatch=cors_handling_middleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=structlog_middleware)
    #app.add_middleware(BaseHTTPMiddleware, dispatch=auth_dispatch)
    #app.add_middleware(BaseHTTPMiddleware, dispatch=api_key_dispatch)
    app.add_exception_handler(Exception, general_exception_handler)


async def setup():
    log.info("setup()")
    thread_locals.initConfig()

    log.info("Finished setup()")

@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    # Clear any residual context before starting
    clear_contextvars()
    await setup()

    yield

    clear_contextvars()




app = FastAPI(lifespan=lifespan, debug=True, title="Guess The Number - Docker Bot Farm")
initFastAPI(app)


@app.get("/")
async def health_check():
    return {"status": "healthy"}



if __name__ == "__main__":
    print("API MAIN Function Initialized!")
    uvicorn.run(app, host='0.0.0.0', port=8081)

