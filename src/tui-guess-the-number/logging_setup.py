import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os
import structlog


def init_conf():
    """
    Initializes production-grade logging.
    Redirects all logs to a rotating file.
    """
    env = os.getenv("ENV", "DEV").upper()
    log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()

    # 1. Common processors (Pipeline)
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


    # 1. Common processors (Pipeline).
    # They form the log structure (add time, level, etc.)
    # This list will be applied to both our logs and logs from third-party libraries.
    shared_processors = [
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
    if env == "PROD":
        # In Docker/Prod output strict JSON
        renderer = structlog.processors.JSONRenderer()
    else:
        # In local development - console output
        renderer = structlog.dev.ConsoleRenderer(colors=False)

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
    # handler = logging.StreamHandler(sys.stdout)
    # handler.setFormatter(formatter)

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
