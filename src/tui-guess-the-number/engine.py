import structlog
import math
from structlog.contextvars import bind_contextvars
from collections import deque
import typer
from typer._click.core import Parameter

from .player_discovery import create_player_a, create_player_b, GuessFeedback, PlayerA, PlayerB

log = structlog.get_logger(__name__)



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

        if not param_hints:
            return f"Invalid value: {self.message}"

        hint = _join_param_hints(*param_hints)
        return f"Invalid value for {hint}: {self.message}"

class Engine:

    def __init__(self, ctx: typer.Context| None) -> None:
        self._ctx: typer.Context | None = ctx

    @property
    def ctx(self)->typer.Context | None:
        return self._ctx





    def play_loop(self, min_val:int, max_val:int, player_a_id:str, player_b_id:str)->None:
        log.info("play_loop()")
        bind_contextvars(
            min_val=min_val,
            max_val=max_val)

        log.info("run_game()")

        # Validation with Graceful Exit
        if min_val >= max_val:
            log.warning("Invalid range configuration")

            # Find the specific parameter object to associate the error with (optional but recommended)
            # We associate it with '--min' since it breaks the condition.

            min_param = None
            max_param = None
            if self.ctx:
                min_param = next((p for p in self.ctx.command.params if p.name == "min_val"), None)
                max_param = next((p for p in self.ctx.command.params if p.name == "max_val"), None)

            # Typer will automatically format this gracefully in the CLI.
            raise BadParameters(
                f"Minimum value ({min_val}) must be strictly less than maximum value ({max_val}).",
                self.ctx,
                min_param,
                max_param
            )

        if min_val >= max_val:
            raise ValueError(f"Interval min_val {min_val} is more than interval max_val {max_val}")

        
        # Calculate the number of attempts using the correct formula
        max_attempts = math.floor(math.log2(max_val - min_val + 1)) + 1

        if max_attempts <1:
            raise ValueError(f"Unexpected max_attempts {max_attempts}. Should be at least 1")

        bind_contextvars(max_attempts=max_attempts)

        player_a: PlayerA = create_player_a(min_val, max_val, max_attempts, player_a_id)
        player_b: PlayerB = create_player_b(min_val, max_val, max_attempts, player_b_id)

        log.info(
            "Game starting",
            player_a_id=player_a_id,
            player_a_identification_info=player_a.get_identification_info(),
            player_b_id=player_b_id,
            player_b_identification_info=player_b.get_identification_info()
        )


        typer.secho(f"🎮 Game is starting!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"Range: from {min_val} to {max_val}")
        typer.echo(f"Maximum attempts: {max_attempts}")
        typer.echo(f"Player A: {player_a_id} | Player B: {player_b_id}\n")
        typer.echo(f"Player A: please think about the number within range.")

        lowest_d = {"attempt":0, "number":min_val - 1}
        highest_d = {"attempt":0, "number":max_val + 1}

        for i in range(1, max_attempts + 1):
            log.info("attempt number", attempt=i)


            typer.echo(f"Player B: Attempt {i} of {max_attempts}. Please make your guesses")
            num = player_b.make_your_guess(i)
            typer.echo(f"Player A: please check if the guess is correct.")
            result: GuessFeedback = player_a.is_guess_number(num)
            match result:
                case GuessFeedback.TOO_LOW:
                    lowest_d['number'] = num
                    lowest_d['attempt'] = i
                case GuessFeedback.TOO_HIGH:
                    highest_d['number'] = num
                    highest_d['attempt'] = i
                case GuessFeedback.EXACT:
                    typer.secho(f"Congratulations for player B! You wins in attempt {i} out of {max_attempts}", fg=typer.colors.GREEN, bold=True)
                    reason = "PlayerB correctly guessed the number"
                    feedback: str | None = player_a.on_finished(attempts=i, is_win=False, reason=reason)
                    if feedback:
                        typer.echo(feedback)
                    feedback = player_b.on_finished(attempts=i, is_win=True, reason=reason)
                    if feedback:
                        typer.echo(feedback)
                    return  # Exit the game
                case _:
                    raise ValueError(f"Unexpected result: {result}")

            typer.echo(f"The guess was {result}")

            lowest = lowest_d['number']
            highest = highest_d['number']

            if lowest + 1 >= highest:   #we must have at least 1 int number in interval [lowest, highest], where lowest<=highest
                lowest_on_attempt = lowest_d['attempt']
                highest_on_attempt = highest_d['attempt']
                log.warning("PlayerA is cheating",
                            lowest=lowest,
                            lowest_on_attempt=lowest_on_attempt,
                            highest=highest,
                            highest_on_attempt=highest_on_attempt
                            )
                reason = (f"Player A is caught cheating. On attempt {lowest_on_attempt}, he said that the guessed number is higher than {lowest}. "
                          f"On the other hand, on attempt {highest_on_attempt}, he said that the guessed number is lower than {highest}. "
                          f"But this is an impossible situation.")
                player_a.on_finished(attempts=i, is_win=False, reason=reason)
                player_b.on_finished(attempts=i, is_win=True, reason=reason)
                return # Exit the game


        typer.secho(f"All {max_attempts} attempts are exhausted. So PlayerA wins the game!", fg=typer.colors.GREEN, bold=True)
        log.info("All attempts are exhausted", max_attempts=max_attempts)

        reason = "Max number of attempts is exhausted"
        feedback:str| None = player_a.on_finished(attempts=max_attempts, is_win=True, reason=reason)
        if feedback:
            typer.echo(feedback)
        feedback = player_b.on_finished(attempts=max_attempts, is_win=False, reason=reason)
        if feedback:
            typer.echo(feedback)
