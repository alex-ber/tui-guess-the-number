import functools
from typing import get_type_hints
import math
from collections import deque

#MONKEY_PATHING:

import inspect
import typer.rich_utils

_original_get_rich_console = typer.rich_utils._get_rich_console

def patched_get_rich_console(*args, **kwargs):
    # Get the signature of the original function
    sig = inspect.signature(_original_get_rich_console)

    # "Bind" the arguments passed to the wrapper to the parameters of the original function.
    # bind() will automatically unpack *args and **kwargs and map them to argument names.
    bound_args = sig.bind(*args, **kwargs)

    # Fill in arguments with default values (if stderr wasn't passed at all)
    bound_args.apply_defaults()

    # Now we are guaranteed to have access to 'stderr' by key,
    # regardless of how it was passed. Force it to False:
    bound_args.arguments['stderr'] = False

    # Call the original function, unpacking the corrected arguments back
    return _original_get_rich_console(*bound_args.args, **bound_args.kwargs)

#Apply the monkey-patch
typer.rich_utils._get_rich_console = patched_get_rich_console

import logging
import structlog
import typer
from typer import Typer
from typing import Annotated
from structlog.contextvars import clear_contextvars
from .logging_setup import initConf as structLogInitConf
from .engine import Engine



log = None



def _configure_logging():
    structLogInitConf()
    global log
    # Get the logger. Important: we get it from structlog, not from logging!
    log = structlog.get_logger(__name__)
    logging.getLogger("boto3").setLevel(logging.WARNING)

def run_game(
    ctx: typer.Context,
    min_val: Annotated[int, typer.Option("--min", help="Minimum value")] = 1,
    max_val: Annotated[int, typer.Option("--max", help="Maximum value")] = 1023,
    player_a: Annotated[str, typer.Option("--player-a", "-a", help="Player A type (the one who thinks of the number)")] = "human",
    player_b: Annotated[str, typer.Option("--player-b", "-b", help="Player B type (the one who guesses)")] = "human",
):
    """
    TUI Game: Guess the Number

    Starts the game with the given parameters.
    """

    ## Clear any residual context before starting
    clear_contextvars()
    try:
        log.info("run_game()")
        runner: Engine = Engine(ctx)
        runner.play_loop(min_val, max_val, player_a, player_b)

    finally:
        clear_contextvars()






def main():
    #typer.run(run_game)
    app = Typer(add_completion=False,
                context_settings={"help_option_names": ["-h", "--help"]},
                suggest_commands=False,
                pretty_exceptions_enable=False,
                pretty_exceptions_short=False
                )
    app.command()(run_game)
    _configure_logging()
    app()


if __name__ == "__main__":
    main()
