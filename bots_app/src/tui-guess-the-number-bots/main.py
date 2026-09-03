import os
from pathlib import Path
from dotenv import load_dotenv
import structlog

from structlog.contextvars import clear_contextvars, bind_contextvars
from alexber.utils.structlog_setup import initConf as structLogInitConf
from alexber.utils import thread_locals
from alexber.utils.literar_converter import parse_str

from contextlib import asynccontextmanager
from starlette.types import ASGIApp, Receive, Send, Scope

import uvicorn
from fastapi import FastAPI, Body, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import msgspec
from typing import Annotated, Any, NewType

from .players import BinarySearchBot, SmartGesserBot, bot_a_identification_info, bot_b_identification_info, bot_a_on_finished, bot_b_on_finished

def _configure_logging():
    cwd = Path.cwd()
    env_path = cwd / ".env"
    override = parse_str(os.getenv("IS_ENV_OVERRIDE", "FALSE").upper())
    load_dotenv(dotenv_path=env_path, override=override)

    structLogInitConf()
    #logging.getLogger("boto3").setLevel(logging.WARNING)

_configure_logging()

log = structlog.get_logger(__name__)

class StructlogASGIMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: dict, receive: Receive, send: Send) -> None:
        # We are only interested in HTTP requests (ignore WebSocket and Lifespan)
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # --- Start processing the HTTP request ---
        # Clear any garbage left by previous requests on this Keep-Alive connection
        clear_contextvars()

        # Bind context for the current request
        # In the ASGI scope, the path can be in bytes or a string (depending on the server),
        # but usually it is available via scope.get("path", "")
        bind_contextvars(request_id="some-unique-id", path=scope.get("path", ""))

        try:
            # Pass control further down the middleware chain.
            # We do NOT intercept send/receive, so BackgroundTasks and Streaming work perfectly!
            await self.app(scope, receive, send)
        finally:
            # Clean up our own context so we do not pollute the next request
            clear_contextvars()


class BaseExceptionGroupASGIMiddleware:
    """
    Catch-all for BaseExceptionGroup that bypasses Starlette's default ExceptionMiddleware.
    Must be placed inside the logging middleware to preserve log contexts!
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except BaseExceptionGroup as exc:
            # We catch it, reconstruct the request and pass it to our robust handler
            request = Request(scope, receive)
            response = await exception_group_handler(request, exc)

            # Send the generated JSONResponse through the ASGI interface
            await response(scope, receive, send)

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


def _flatten_exceptions(exc: Exception) -> list[Exception]:
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


async def exception_group_handler(request: Request, exc: BaseExceptionGroup):
    """
    Handles BaseExceptionGroup (Python 3.11+), unwrapping exceptions
    and preserving the system signals (like CancelledError).
    """

    # 1. NATIVE SPLIT (Written in C, blazingly fast)
    # Separates application exceptions (matched) from system exceptions (unmatched)
    matched, unmatched = exc.split(Exception)

    responses: list[JSONResponse] = []

    # 2. Process application exceptions safely
    flat_exceptions = []
    if matched:
        # Single pass flattening
        flat_exceptions = _flatten_exceptions(matched)

        log.error(
            "Exception group caught (application errors)",
            exception_type=type(matched).__name__,
            exc_info=matched
        )

    # 3. CRITICAL: Re-raise system exceptions immediately.
    # We do this AFTER processing app errors. If [ValueError, CancelledError]
    # occurred, ValueError is logged above, and CancelledError is raised here
    # so Uvicorn/AnyIO can correctly abort the request without returning JSON.
    if unmatched:
        raise unmatched

    for sub_exc in flat_exceptions:
        resp = await general_exception_handler(request, sub_exc)
        responses.append(resp)

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
    # =====================================================================
    # MIDDLEWARE REGISTRATION
    # WARNING: FastAPI adds middleware using list.insert(0).
    # This means the LAST middleware added becomes the OUTERMOST layer
    # (it is the first to receive the request and the last to send response).
    #
    # Expected execution order (Outside -> Inside):
    # 1. CORS
    # 2. Structlog (sets contextvars)
    # 3. BaseExceptionGroup (catches errors, uses contextvars for logging)
    # =====================================================================

    # 3. INNERMOST user middleware (Added first)
    app.add_middleware(BaseExceptionGroupASGIMiddleware)

    # 2. MIDDLE user middleware (Added second)
    # Wraps BaseExceptionGroup, meaning contextvars are active when exceptions are caught.
    app.add_middleware(StructlogASGIMiddleware)
    # #app.add_middleware(BaseHTTPMiddleware, dispatch=structlog_middleware)
    # #app.add_middleware(BaseHTTPMiddleware, dispatch=auth_dispatch)
    # #app.add_middleware(BaseHTTPMiddleware, dispatch=api_key_dispatch)


    # 1. OUTERMOST user middleware (Added last)
    # Ensures CORS headers are appended even if our exception handlers return a 500 response.
    app.add_middleware(
        CORSMiddleware, # type: ignore[arg-type]
        allow_origins=["*"], # type: ignore[arg-type]
        allow_credentials=True, # type: ignore[arg-type]
        allow_methods=["*"], # type: ignore[arg-type]
        allow_headers=["*"], # type: ignore[arg-type]
    )

    # =====================================================================
    # EXCEPTION HANDLERS REGISTRATION
    # =====================================================================
    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(ExceptionGroup, exception_group_handler) # type: ignore[arg-type]

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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

BOT_A_REGISTRY = {
    "smart_bot": BinarySearchBot()
}

BOT_B_REGISTRY = {
    "smart_bot": SmartGesserBot()
}

@app.get("/bots/a/{bot_id}/info")
def get_a_info(bot_id: str):
    log.info("get_a_info()", bot_id=bot_id)

    bot = BOT_A_REGISTRY.get(bot_id, None)
    if not bot:
        raise HTTPException(status_code=404, detail=f"Bot A {bot_id} not found")

    ret = bot_a_identification_info(bot)
    return ret

@app.get("/bots/b/{bot_id}/info")
def get_b_info(bot_id: str):
    log.info("get_b_info()", bot_id=bot_id)

    bot = BOT_B_REGISTRY.get(bot_id, None)
    if not bot:
        raise HTTPException(status_code=404, detail=f"Bot B {bot_id} not found")

    ret =  bot_b_identification_info(bot)
    return ret


# LegacyBool = NewType("LegacyBool", bool)
# LegacyDateTime = NewType("LegacyDateTime", datetime.datetime)
#
#
#
# def alexber_dec_hook(type_: type, obj: Any) -> Any:
#     # 1. If we expect a custom Bool or DateTime — trust parse_str
#     if type_ is LegacyBool or type_ is LegacyDateTime:
#         return parse_str(obj)
#
#     # # if we have some case that should be covered another way that parse_str() do
#     # # I'm using str_to_bool() just for demonstration purposes
#     # if type_ is LegacyBool:
#     #     # If the client sent a native bool, return it as is
#     #     if isinstance(obj, bool):
#     #         return obj
#     #     # Otherwise parse with your function (handles "yes", "on", "1")
#     #     return str_to_bool(str(obj))
#
#
#     # 2. If the field is Any
#     elif type_ is Any:
#         if isinstance(obj, str):
#             # If it's a string — try to find hidden types inside (dates, bool)
#             return parse_str(obj)
#         else:
#             # If it's already a native int, float, list, dict, bool — just pass it through
#             return obj
#
#     # 3. Fallback for unexpected types that we forgot to handle
#     raise TypeError(f"Type {type_} not supported by hook")
#
#
# class MyPayload(msgspec.Struct):
#     id: int
#     is_active: LegacyBool      # msgspec will call the hook!
#     created_at: LegacyDateTime # msgspec will call the hook!
#     price: decimal.Decimal     # msgspec will parse it internally at the C level! (No Any needed)
#     extra_payload: Any  # Here Any — is the only way!
#
# payload = msgspec.json.decode(body, type=MyPayload, dec_hook=any_dec_hook)
#


# class BasePayload(msgspec.Struct):
#     # min_val must be greater than or equal to 1
#     min_val: Annotated[int, msgspec.Meta(ge=1)]
#     max_val: int
#     # max_attempts must be greater than or equal to 1
#     max_attempts: Annotated[int, msgspec.Meta(ge=1)]
#
#     def __post_init__(self):
#         # Cross-field validation (business logic) remains here.
#         # We only check the relationship between max_val and min_val.
#         # Consistently raising msgspec's native validation exception
#         if self.max_val <= self.min_val:
#             # Consistently raising msgspec's native validation exception
#             raise msgspec.ValidationError(
#                 f"max_val ({self.max_val}) must be greater than min_val ({self.min_val})"
#             )


class BotAOnFinishedPayload(msgspec.Struct):
    is_win: bool
    reason: str


@app.post("/bots/a/{bot_id}/on_finished")
async def on_finished_a_bot(bot_id: str, request: Request):
    log.info("on_finished_a_bot()", bot_id=bot_id)

    bot = BOT_A_REGISTRY.get(bot_id, None)
    if not bot:
        raise HTTPException(status_code=404, detail=f"Bot A {bot_id} not found")

    body = await request.body()
    payload = msgspec.json.decode(body, type=BotAOnFinishedPayload)

    ret = bot_a_on_finished(payload.is_win, payload.reason)
    return ret

class BotBOnFinishedPayload(msgspec.Struct):
    max_attempts: int
    attempts: int
    is_win: bool
    reason: str

@app.post("/bots/b/{bot_id}/on_finished")
async def on_finished_b_bot(bot_id: str, request: Request):
    log.info("on_finished_b_bot()", bot_id=bot_id)

    bot = BOT_B_REGISTRY.get(bot_id, None)
    if not bot:
        raise HTTPException(status_code=404, detail=f"Bot B {bot_id} not found")

    body = await request.body()
    payload = msgspec.json.decode(body, type=BotBOnFinishedPayload)

    ret = bot_b_on_finished(payload.max_attempts, payload.attempts,payload.is_win,payload.reason)
    return ret




if __name__ == "__main__":
    print("API MAIN Function Initialized!")
    uvicorn.run(app, host='0.0.0.0', port=8081)

