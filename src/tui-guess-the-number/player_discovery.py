import structlog
from typing import Protocol

log = structlog.get_logger(__name__)

from ._players import HumanPlayerA as _HumanPlayerA , HumanPlayerB as _HumanPlayerB, GuessFeedback


class PlayerA(Protocol):
    """
    Contract for PlayerA: picks a random number.
    """
    def prepare_to_play(self, min_val:int, max_val:int, max_attempts: int) -> None:
        """min and max boundaries for the number to be picked.
        The opponent will have max_attempts to guess the number."""
        ...

    def is_guess_number(self, number:int) -> GuessFeedback:
        """Does number you've picked is the passed number? If no, does it too low or to high?"""
        ...

    def get_identification_info(self) -> str:
        """Return your real class/id name"""
        ...

    def on_finished(self, attempts:int, is_win:bool, reason:str) -> str|None:
        """The result of the game. How many attempts were made, did you win or lose? What the reason."""
        ...



class PlayerB(Protocol):
    """
    Contract for PlayerB: guess the number.
    """
    def prepare_to_play(self, min_val: int, max_val: int, max_attempts: int) -> None:
        """min and max boundaries for the number to be guessed.
        You will have max_attempts to guess the number."""
        ...

    def make_your_guess(self, attempt:int) -> int:
        """Make your guess. This is current attempt number"""
        ...

    def get_identification_info(self) -> str:
        """Return your real class/id name"""
        ...

    def on_finished(self, attempts:int, is_win:bool, reason:str) -> str|None:
        """The result of the game. How many attempts were made, did you win or lose? What the reason."""
        ...


def create_player_a(min_val:int, max_val:int, max_attempts:int, player_id:str) -> PlayerA:
    log.info("create_player_a", player_a_id = str(player_id))
    #TODO: extend to real lookup, first based on another Docker, second based on MCP server
    player: PlayerA = _HumanPlayerA()
    player.prepare_to_play(min_val, max_val, max_attempts)
    return player

def create_player_b(min_val:int, max_val:int, max_attempts:int, player_id:str) -> PlayerB:
    log.info("create_player_b", player_b_id = str(player_id))
    # TODO: extend to real lookup, first based on another Docker, second based on MCP server
    player: PlayerB = _HumanPlayerB()
    player.prepare_to_play(min_val, max_val, max_attempts)
    return player

