import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os
import structlog
from .literar_coonverter import parse_str


class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger.
    Properly handles chunked writes and prevents data loss on exit.
    """
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.buf = ""  # Internal buffer for partial lines

    def write(self, buf):
        """
        Processes incoming string buffer.
        """
        # splitlines(keepends=True) allows us to know if the line was finished
        for line in buf.splitlines(keepends=True):
            if line.endswith('\n'):
                # Line is complete. Combine with buffer and log it.
                full_line = self.buf + line.rstrip()
                if full_line.strip():
                    self.logger.log(self.log_level, "Raw stream output", raw_text=full_line)
                self.buf = ""  # Clear the buffer
            else:
                # Line is incomplete (no \n). Add to buffer and wait for more.
                self.buf += line

    def flush(self):
        """
        Called by Python when the stream is being forced to flush (e.g., app exit).
        Dumps whatever is left in the buffer to prevent data loss.
        """
        if self.buf:
            clean_buf = self.buf.strip()
            if clean_buf:
                self.logger.log(self.log_level, "Raw stream output", raw_text=clean_buf)
            self.buf = ""


def initConf():
    """
    Initializes production-grade logging.
    Redirects all logs to a rotating file.
    """
    render_type = parse_str(os.getenv("LOG_RENDER_TYPE", "").upper())
    log_level = parse_str(os.getenv("LOG_LEVEL", "DEBUG").upper())
    log_console_color = parse_str(os.getenv("LOG_CONSOLE_COLOR", "FALSE").upper())
    log_stdout = parse_str(os.getenv("LOG_STDOUT", "TRUE").upper())


    # 1. Common processors (Pipeline).
    # They form the log structure (add time, level, etc.)
    # This list will be applied to both our logs and logs from third-party libraries.
    shared_processors = [
        structlog.contextvars.merge_contextvars,    #Look on contextvars on every call
        structlog.stdlib.add_log_level,      # Adds the log level field (info, error)
        structlog.stdlib.add_logger_name,    # Adds the module name (where the logger was called)
        structlog.stdlib.PositionalArgumentsFormatter(), # Support for old '%s' formatting
        #structlog.processors.TimeStamper(fmt="iso"),     # Time in ISO 8601 format
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),        # Support for stack_info=True
        structlog.processors.format_exc_info,            # Pretty exception output (exc_info=True)
        structlog.processors.UnicodeDecoder(),           # Protection against encoding issues
    ]

    # 2. Choose the final renderer (the last link in the pipeline)
    if render_type == "JSON":
        # In Docker/Prod output strict JSON
        renderer = structlog.processors.JSONRenderer()
    else:
        # In local development - console output
        renderer = structlog.dev.ConsoleRenderer(colors=log_console_color)

    # 3. Configure structlog itself
    structlog.configure(
        processors=shared_processors + [
            # Prepare data for passing to standard logging
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


    # 4. Use TimedRotatingFileHandler for automatic log rotation
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        # Force logs from third-party libraries to go through our shared_processors
        foreign_pre_chain=shared_processors,
    )

    # 5. Configure standard Python logging
    root_logger = logging.getLogger()
    root_logger.handlers.clear()    #You may reconsider this, but for most cases this is what you neeed

    # Ensure the logs directory exists
    os.makedirs("logs", exist_ok=True)

    #For standard logging using stdout
    handler = None
    if log_stdout:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
    else:
        # Configure rotating file handler
        # Rotates at midnight, keeps 10 backups, delays file creation until first log
        handler = TimedRotatingFileHandler(
            filename="logs/tui-guess-the-number.log",
            when="midnight",
            backupCount=10,
            delay=True,
            encoding="utf-8"
        )
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    logging.captureWarnings(True)

    log_redirector = structlog.get_logger("sys.stderr")
    sys.stderr = StreamToLogger(log_redirector, logging.ERROR)


# import asyncio
# from structlog.contextvars import bind_contextvars, clear_contextvars
#
# log = structlog.get_logger()
#
# async def some_deep_function():
#     # We didn't pass a logger here! We're calling the global one.
#     # But it will automatically pull player_id from contextvars of the current coroutine!
#     log.info("Doing something deep")
#
# async def handle_player(player_id: str):
#     # Instead of log.bind(), we bind variables directly into the async context (contextvars)
#     bind_contextvars(player_id=player_id)
#
#     log.info("Player connected")
#     await some_deep_function()
#
#     # Clear the context if we plan to reuse the thread/task
#     # (although in asyncio, the context dies on its own when the task completes)
#     clear_contextvars()
#
# async def main():
#     # Run two coroutines in parallel
#     await asyncio.gather(
#         handle_player("Alice"),
#         handle_player("Bob")
#     )



# from structlog.contextvars import bind_contextvars, clear_contextvars
# from fastapi import Request
#
# @app.middleware("http")
# async def structlog_middleware(request: Request, call_next):
#     # Clear any garbage left by previous requests on this Keep-Alive connection
#     clear_contextvars()
#
#     # Bind context for the current request
#     bind_contextvars(request_id="some-unique-id", path=request.url.path)
#
#     try:
#         response = await call_next(request)
#         return response
#     finally:
#         # Clean up our own context so we do not pollute the next request
#         clear_contextvars()
