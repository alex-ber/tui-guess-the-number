import logging
import structlog
import typer
from typer import Typer
from typing import Annotated
import math
from .logging_setup import init_conf as structLogInitConf

log = None

def validate_param(param_value, param_name):
    """
     Validates that a required parameter is not None.

     param_value (any): The value of the parameter to be validated.
     param_name (str): The name of the parameter to be used in the error message.

     Raises:
     ValueError: If the parameter value is None, indicating that the required parameter is missing.
     """
    if param_value is None:
        raise ValueError(f"Expected {param_name} param not found")

def _configure_logging():
    structLogInitConf()
    global log
    # Get the logger. Important: we get it from structlog, not from logging!
    log = structlog.get_logger(__name__)
    logging.getLogger("boto3").setLevel(logging.WARNING)

def run_game(
    min_val: Annotated[int, typer.Option("--min", help="Minimum value")] = 1,
    max_val: Annotated[int, typer.Option("--max", help="Maximum value")] = 1023,
    player_a: Annotated[str, typer.Option("--player-a", "-a", help="Player A type (the one who thinks of the number)")] = "human",
    player_b: Annotated[str, typer.Option("--player-b", "-b", help="Player B type (the one who guesses)")] = "human",
):
    """
    TUI Game: Guess the Number

    Starts the game with the given parameters.
    """

    bound_log = log.bind(
        min_val=min_val,
        max_val=max_val)

    # Validation with Graceful Exit
    if min_val >= max_val:
        bound_log.warning("Invalid range configuration")

        # Output user-friendly error to stdout
        typer.secho(
            f"❌ Error: Minimum value ({min_val}) must be strictly less than maximum value ({max_val}).",
            fg=typer.colors.RED,
            bold=True
        )
        # Mimic standard CLI hint
        typer.echo("Try '--help' for help.")

        # Exit silently
        raise typer.Exit(code=2)



    bound_log.info(
        "Game starting",

        player_a=player_a,
        player_b=player_b
    )

    # Calculate the number of attempts using the correct formula
    max_attempts = math.floor(math.log2(max_val - min_val + 1)) + 1

    bound_log = bound_log.bind(max_attempts=max_attempts)

    typer.secho(f"🎮 Game is starting!", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"Range: from {min_val} to {max_val}")
    typer.echo(f"Maximum attempts: {max_attempts}")
    typer.echo(f"Player A: {player_a} | Player B: {player_b}\n")

    # player_a_instance = load_player(player_a)
    # player_b_instance = load_player(player_b)
    # start_game_loop(...)

    #clear_contextvars()


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
