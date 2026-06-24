import structlog
import math
from structlog.contextvars import bind_contextvars
from collections import deque
import typer
from typer._click.core import Parameter

from .player_discovery import create_player_a, create_player_b

log = structlog.get_logger(__name__)


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
        ctx: typer.Context | None = None,
        *params: Parameter | None,

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

class Engine:

    def __init__(self, ctx: typer.Context| None) -> None:
        self._ctx: typer.Context | None = ctx

    @property
    def ctx(self)->typer.Context | None:
        return self._ctx



    def play_loop(self, minVal:int, maxVal:int, playerAId:str, playerBId:str)->None:
        log.info("play_loop()")
        bind_contextvars(
            minVal=minVal,
            maxVal=maxVal)

        log.info("run_game()")

        # Validation with Graceful Exit
        if minVal >= maxVal:
            log.warning("Invalid range configuration")

            # Find the specific parameter object to associate the error with (optional but recommended)
            # We associate it with '--min' since it breaks the condition.
            minParam = next((p for p in type(self).ctx.command.params if p.name == "min_val"), None)
            maxParam = next((p for p in type(self).ctx.command.params if p.name == "max_val"), None)

            # Raise Typer's BadParameter. Typer will automatically format this
            # gracefully in the CLI.
            raise BadParameters(
                f"Minimum value ({minVal}) must be strictly less than maximum value ({maxVal}).",
                type(self).ctx,
                minParam,
                maxParam
            )



        if minVal >= maxVal:
            raise ValueError(f"Interval min_val {minVal} is more than interval max_val {maxVal}")

        # Calculate the number of attempts using the correct formula
        maxAttempts = math.floor(math.log2(maxVal - minVal + 1)) + 1

        if maxAttempts <1:
            raise ValueError(f"Unexpected maxAttempts {maxAttempts}. Should be at least 1")

        bind_contextvars(maxAttempts=maxAttempts)

        playerA = create_player_a(minVal, maxVal, maxAttempts, playerAId)
        playerB = create_player_b(minVal, maxVal, maxAttempts, playerBId)


        log.info(
            "Game starting",

            playerA=str(playerA),
            playerB=str(playerB)
        )


        typer.secho(f"🎮 Game is starting!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"Range: from {minVal} to {maxVal}")
        typer.echo(f"Maximum attempts: {maxAttempts}")
        typer.echo(f"Player A: {playerAId} | Player B: {playerBId}\n")

