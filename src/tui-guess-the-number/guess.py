import functools
from typing import get_type_hints
import logging
import structlog
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

import typer
from typer import Typer

from typing import Annotated

from .logging_setup import initConf as structLogInitConf

from structlog.contextvars import bind_contextvars, clear_contextvars

log = None

# def validate_param(param_value, param_name):
#     """
#      Validates that a required parameter is not None.

#      param_value (any): The value of the parameter to be validated.
#      param_name (str): The name of the parameter to be used in the error message.

#      Raises:
#      ValueError: If the parameter value is None, indicating that the required parameter is missing.
#      """
#     if param_value is None:
#         raise ValueError(f"Expected {param_name} param not found")

def _join_param_hints(*param_hints):
    assert param_hints
    return " / ".join(repr(x) for x in param_hints)


class BadParameters(typer.BadParameter):
    """An exception that formats out a standardized error message for a
    bad parameters.  This is useful when thrown from a callback or type as
    Click will attach contextual information to it (for instance, which
    parameters it is are).
    """

    def __init__(
        self,
        message: str,
        ctx: "Context" | None = None,
        *params: "Parameter" | None,

    ) -> None:
        super().__init__(message, ctx)
        self.params = params

    def format_message(self) -> str:
        if not self.params:
            return f"Invalid value: {self.message}"

        length = len(self.params)
        param_hints = deque(maxlen=length)
        for param in self.params:
            if param is not None:
                param_hint = param.get_error_hint(self.ctx)  # type: ignore
                param_hints.append(param_hint)


        hint = _join_param_hints(*param_hints)
        return f"Invalid value for {hint}: {self.message}"

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
        bind_contextvars(
            min_val=min_val,
            max_val=max_val)

        log.info("run_game()")

        # Validation with Graceful Exit
        if min_val >= max_val:
            log.warning("Invalid range configuration")

            # Find the specific parameter object to associate the error with (optional but recommended)
            # We associate it with '--min' since it breaks the condition.
            min_param = next((p for p in ctx.command.params if p.name == "min_val"), None)
            max_param = next((p for p in ctx.command.params if p.name == "max_val"), None)

            # Raise Typer's BadParameter. Typer will automatically format this
            # gracefully in the CLI.
            raise BadParameters(
                f"Minimum value ({min_val}) must be strictly less than maximum value ({max_val}).",
                ctx,
                min_param,
                max_param
            )



        log.info(
            "Game starting",

            player_a=player_a,
            player_b=player_b
        )

        # Calculate the number of attempts using the correct formula
        max_attempts = math.floor(math.log2(max_val - min_val + 1)) + 1

        bind_contextvars(max_attempts=max_attempts)

        typer.secho(f"🎮 Game is starting!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"Range: from {min_val} to {max_val}")
        typer.echo(f"Maximum attempts: {max_attempts}")
        typer.echo(f"Player A: {player_a} | Player B: {player_b}\n")

        # player_a_instance = load_player(player_a)
        # player_b_instance = load_player(player_b)
        # start_game_loop(...)
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
