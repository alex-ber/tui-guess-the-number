import os
from pathlib import Path
from dotenv import load_dotenv
import structlog
from structlog.contextvars import clear_contextvars, bind_contextvars
from collections import deque
from alexber.utils.structlog_setup import initConf as structLogInitConf
from alexber.utils import thread_locals
from alexber.utils.literar_coonverter import parse_str

from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware

import uvicorn
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import msgspec
from typing import Annotated

from .players import BinarySearchBot

def _configure_logging():
    cwd = Path.cwd()
    env_path = cwd / ".env"
    override = parse_str(os.getenv("IS_ENV_OVERRIDE", "FALSE").upper())
    load_dotenv(dotenv_path=env_path, override=override)

    structLogInitConf()
    #logging.getLogger("boto3").setLevel(logging.WARNING)

_configure_logging()

log = structlog.get_logger(__name__)



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

    # Handle parsing and validation errors caused by the client (422 status)
    if isinstance(exc, (msgspec.ValidationError, msgspec.DecodeError)):
        # We log this as a warning because it's a client error, not a server crash
        log.warning("Validation/Decode Error", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)}
        )

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


def _flatten_exceptions(exc: BaseException) -> list[Exception]:
    """
    Extracts all standard Exception instances in a SINGLE PASS using DFS.

    A single pass using lists is strictly faster in CPython than a two-pass
    counting approach. Python's list appends are amortized O(1) in C,
    whereas executing `isinstance()` and attribute lookups twice (to count
    and then populate) adds significant Python bytecode overhead.
    """
    flat: list[Exception] = []

    # Using a list as a stack for Depth-First Search (DFS)
    stack: list[BaseException] = [exc]

    while stack:
        # pop() from the end of a list is strictly O(1) and very cache-friendly
        current = stack.pop()

        if isinstance(current, BaseExceptionGroup):
            # extend() effectively pushes all sub-exceptions onto the stack
            stack.extend(current.exceptions)
        elif isinstance(current, Exception):
            # Standard application exceptions are collected
            flat.append(current)

    return flat


async def exception_group_handler(request: Request, exc: ExceptionGroup):
    """
    Handles ExceptionGroup (Python 3.11+), unwrapping exceptions
    and preserving the system signals (like CancelledError).
    """

    # 1. NATIVE SPLIT (Written in C, blazingly fast)
    # Separates application exceptions (matched) from system exceptions (unmatched)
    matched, unmatched = exc.split(Exception)

    responses: list[JSONResponse] = []

    # 2. Process application exceptions safely
    if matched:
        # Single pass flattening
        flat_exceptions = _flatten_exceptions(matched)

        log.error(
            "Exception group caught (application errors)",
            exception_type=type(matched).__name__,
            exc_info=matched
        )

        for sub_exc in flat_exceptions:
            resp = await general_exception_handler(request, sub_exc)
            responses.append(resp)

    # 3. CRITICAL: Re-raise system exceptions immediately.
    # We do this AFTER processing app errors. If [ValueError, CancelledError]
    # occurred, ValueError is logged above, and CancelledError is raised here
    # so Uvicorn/AnyIO can correctly abort the request without returning JSON.
    if unmatched:
        raise unmatched

    # 4. Failsafe for empty groups
    if not responses:
        log.error("Empty group caught (application errors)")
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

    # 5. SMART UNWRAPPING: Preserve the API contract for single exceptions
    # Because BaseHTTPMiddleware / AnyIO wraps even single errors.
    length: int = 0 if not responses else len(responses)
    if length == 1:
        return responses[0]

    # 6. Aggregate multiple concurrent exceptions
    final_status = max((r.status_code for r in responses), default=500)

    # Using a standard list is optimal here because we need a sequence
    # to pass into the JSON response anyway. Avoids the [*deque] unpacking overhead.
    aggregated_details: list[dict] = []

    for r in responses:
        body_data = None
        try:
            # msgspec handles bytes natively and is blazing fast
            body_data = msgspec.json.decode(r.body)
        except Exception as e2:
            log.error("Parsing response body exception", error=str(e2), path=request.url.path, exception_type=type(e2).__name__, exc_info=True)
            body_data = "Could not parse response body"

        aggregated_details.append({
            "status_code": r.status_code,
            "response": body_data
        })

    return JSONResponse(
        status_code=final_status,
        content={
            "message": f"Multiple exceptions occurred ({length} total)",
            "details": aggregated_details,
        }
    )




def initFastAPI(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(BaseHTTPMiddleware, dispatch=structlog_middleware)
    #app.add_middleware(BaseHTTPMiddleware, dispatch=auth_dispatch)
    #app.add_middleware(BaseHTTPMiddleware, dispatch=api_key_dispatch)

    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(ExceptionGroup, exception_group_handler)


async def setup():
    log.info("setup()")
    thread_locals.initConfig()

    log.info("Finished setup()")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Clear any residual context before starting
    clear_contextvars()
    await setup()

    yield

    clear_contextvars()




app = FastAPI(lifespan=lifespan, debug=False, title="Guess The Number - Docker Bot Farm")
initFastAPI(app)

BOT_REGISTRY = {
    "smart_bot": BinarySearchBot()
}

@app.get("/bots/{bot_id}/info")
def get_info(bot_id: str):
    bot = BOT_REGISTRY.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    # Return the actual Python class name dynamically (e.g., "BinarySearchBot")
    return {"class_name": type(bot).__name__}


class PreparePayload(msgspec.Struct):
    # min_val must be greater than or equal to 1
    min_val: Annotated[int, msgspec.Meta(ge=1)]
    max_val: int
    # max_attempts must be greater than or equal to 1
    max_attempts: Annotated[int, msgspec.Meta(ge=1)]

    def __post_init__(self):
        # Cross-field validation (business logic) remains here.
        # We only check the relationship between max_val and min_val.
        # Consistently raising msgspec's native validation exception
        if self.max_val <= self.min_val:
            # Consistently raising msgspec's native validation exception
            raise msgspec.ValidationError(
                f"max_val ({self.max_val}) must be greater than min_val ({self.min_val})"
            )

@app.post("/bots/{bot_id}/prepare")
async def prepare_bot(bot_id: str, request: Request):
    bot = BOT_REGISTRY.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    body = await request.body()
    payload = msgspec.json.decode(body, type=PreparePayload)

    try:
        # We try to get the method reference first.
        # This prevents masking an AttributeError that might happen INSIDE the method.
        prepare_func = bot.prepare_to_play
    except AttributeError:
        # Fallback: the method doesn't exist on this bot instance, do nothing
        pass
    else:
        # The method exists, now we can safely call it
        prepare_func(
            min_val=payload.min_val,
            max_val=payload.max_val,
            max_attempts=payload.max_attempts
        )

    return {"status": "ready"}

@app.post("/bots/{bot_id}/make_guess")
def make_guess(
    bot_id: str,
    # embed=True allows sending {"attempt": 1} without defining a Pydantic model
    attempt: int = Body(..., embed=True)
):
    bot = BOT_REGISTRY.get(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    guess = bot.make_your_guess(attempt)
    return {"guess": guess}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}



if __name__ == "__main__":
    print("API MAIN Function Initialized!")
    uvicorn.run(app, host='0.0.0.0', port=8081)

