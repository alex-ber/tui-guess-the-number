
import structlog
from rich.prompt import IntPrompt, PromptBase
from enum import StrEnum


class GuessFeedback(StrEnum):
    TOO_LOW = "too low"
    TOO_HIGH = "too high"
    EXACT = "exact"




class GuessFeedbackPrompt(PromptBase[GuessFeedback]):
    """A prompt that returns an GuessFeedback.

    Example:
        >>> guess_result = GuessFeedbackPrompt.ask("Does it 500?")

    """

    response_type = GuessFeedback
    validate_error_message = "[prompt.invalid]Please enter a valid guess: either 'too low' or 'too high' or 'exact'"


log = structlog.get_logger(__name__)


class HumanPlayerA:
    def prepare_to_play(self, min_val:int, max_val:int, max_attempts: int) -> None:
        log.info("prepare_to_play()")

    def is_guess_number(self, number:int) -> GuessFeedback:
        log.info("is_guess_number()", number = number)
        guess_result = GuessFeedbackPrompt.ask(f"Does it {number}?")
        return guess_result

    def get_identification_info(self) -> str:
        return type(self).__name__

    def on_finished(self, attempts:int, is_win:bool, reason:str) -> str|None:
        log.info("on_finished()")
        message = ""

        if is_win:
            message = f"Hurray! {reason}"
        else:
            message = f"I lose because of {reason}"

        return message



class HumanPlayerB:
    def prepare_to_play(self, min_val: int, max_val: int, max_attempts: int) -> None:
        log.info("prepare_to_play()")
        self.lowest = min_val
        self.highest = max_val
        self.max_attempts = max_attempts

    def make_your_guess(self, attempt:int) -> int:
        log.info("make_your_guess()")
        number = IntPrompt.ask(f"Make your guess.")
        return number

    def get_identification_info(self) -> str:
        return type(self).__name__

    def on_finished(self, attempts:int, is_win:bool, reason:str) -> str|None:
        log.info("on_finished()")
        message = ""
        if is_win:
            message = f"Hurray! It tooks me only {attempts} attempts out of {self.max_attempts} to guess it right! {reason}"
        else:
            message = f"Attempts {self.max_attempts} wasn't enough! {reason}"


        return message


