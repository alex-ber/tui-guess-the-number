
import structlog
from rich.prompt import IntPrompt, PromptBase
from enum import StrEnum

import msgpack
from fastapi import FastAPI, HTTPException, Request


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
    def is_guess_number(self, min_val:int, max_val:int, max_attempts: int, number:int) -> GuessFeedback:
        log.info("is_guess_number()", number = number)
        guess_result = GuessFeedbackPrompt.ask(f"Does it {number}?")
        return guess_result

    def get_identification_info(self) -> str:
        return type(self).__name__

    def on_finished(self, min_val:int, max_val:int, max_attempts: int, attempts:int, is_win:bool, reason:str) -> str|None:
        log.info("on_finished()", is_win = is_win, reason = reason)
        message = ""

        if is_win:
            message = f"Hurray! {reason}"
        else:
            message = f"I lose because of {reason}"

        return message



class HumanPlayerB:

    def make_your_guess(self, min_val:int, max_val:int, max_attempts: int, attempt:int) -> int:
        log.info("make_your_guess()")
        number = IntPrompt.ask(f"Make your guess.")
        return number

    def get_identification_info(self) -> str:
        return type(self).__name__

    def on_finished(self, min_val:int, max_val:int, max_attempts: int, attempts:int, is_win:bool, reason:str) -> str|None:
        log.info("on_finished()", message = is_win, reason = reason)
        message = ""
        if is_win:
            message = f"Hurray! It tooks me only {attempts} attempts out of {max_attempts} to guess it right! {reason}"
        else:
            message = f"Attempts {max_attempts} wasn't enough! {reason}"


        return message


