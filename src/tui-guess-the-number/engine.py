import structlog
import math
from structlog.contextvars import bind_contextvars
import typer

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

class Engine:
    def create_player_a(self, minVal:int, maxVal:int, max_attempts:int, player_id:str):
        log.info("create_player_a", player_a_id = str(player_id))
        return ""

    def create_player_b(self, minVal:int, maxVal:int, max_attempts:int, player_id:str):
        log.info("create_player_b", player_b_id = str(player_id))
        return ""


    def play_loop(self, minVal:int, maxVal:int, playerAId:str, playerBId:str)->None:
        log.info("play_loop()")
        validate_param(minVal, "minVal")
        validate_param(maxVal, "maxVal")

        if minVal >= maxVal:
            raise ValueError(f"Interval min_val {minVal} is more than interval max_val {maxVal}")

        # Calculate the number of attempts using the correct formula
        maxAttempts = math.floor(math.log2(maxVal - minVal + 1)) + 1

        if maxAttempts <1:
            raise ValueError(f"Unexpected maxAttempts {maxAttempts}. Should be at least 1")

        bind_contextvars(maxAttempts=maxAttempts)

        playerA = self.create_player_a(minVal, maxVal, maxAttempts, playerAId)
        playerB = self.create_player_b(minVal, maxVal, maxAttempts, playerBId)


        log.info(
            "Game starting",

            playerA=str(playerA),
            playerB=str(playerB)
        )


        typer.secho(f"🎮 Game is starting!", fg=typer.colors.GREEN, bold=True)
        typer.echo(f"Range: from {minVal} to {maxVal}")
        typer.echo(f"Maximum attempts: {maxAttempts}")
        typer.echo(f"Player A: {playerAId} | Player B: {playerBId}\n")

