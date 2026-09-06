from enum import StrEnum
from typing import Any
import structlog
import random

log = structlog.get_logger(__name__)

def bot_a_on_finished(is_win:bool, reason:str) -> str|None:
    log.info("bot_a_on_finished()", is_win=is_win, reason=reason)
    message = ""

    if is_win:
        message = f"Hurray! {reason}"
    else:
        message = f"I lose because of {reason}"

    return message

def bot_b_on_finished(max_attempts: int, attempts:int, is_win:bool, reason:str) -> str|None:
    log.info("on_finished()", message = is_win, reason = reason)
    message = ""
    if is_win:
        message = f"Hurray! It tooks me only {attempts} attempts out of {max_attempts} to guess it right! {reason}"
    else:
        message = f"Attempts {max_attempts} wasn't enough! {reason}"


    return message

def get_sample(min_val:int, max_val:int, sampling_func: Any, max_retries:int=1000) -> float:
    """
    Get a sample from the specified distribution using common retry logic.

    :return: A sample from the specified distribution within the specified bounds.
    """
    log.info("get_sample()")
    for _ in range(max_retries):
        sampled_value = sampling_func()
        if min_val <= sampled_value <= max_val:
            return sampled_value

    raise ValueError(
        f"Failed to sample a valid value within the specified interval ({min_val}, {max_val}  after max retries {max_retries}).",

    )

class IdentificationInfoMixin:
    def get_identification_info(self) -> str:
        # Returns the actual Python class name dynamically (e.g., "SmartGuesserBot")
        return type(self).__name__

class GuessFeedback(StrEnum):
    TOO_LOW = "too low"
    TOO_HIGH = "too high"
    EXACT = "exact"

class SmartGuesserBot(IdentificationInfoMixin):
    def is_guess_number(self, game_id: str, min_val:int, max_val:int, attempt: int, number:int) -> GuessFeedback:
        log.info("is_guess_number()")

        # Defensive programming for internal Python calls (if bypassed msgspec).
        if not isinstance(min_val, int) or not isinstance(max_val, int):
            raise ValueError("Bounds must be strict integers.")

        if min_val >= max_val:
            raise ValueError(f"min_val {min_val} must be less than max_val {max_val}")

        # game_id arrived as a UUIDv7 string, for example, '018f1234-...'
        # Unique seed for a specific attempt in a specific game guarantees stateless reproducibility.
        # This makes the bot "unintentionally" cheat by changing the secret number on every attempt.
        current_seed = f"{self.get_identification_info()}_{game_id}_{attempt}"

        # Initialize a local stateless generator
        rng = random.Random(current_seed)
        secret_number = rng.randint(min_val, max_val)

        if number < secret_number:
            return GuessFeedback.TOO_LOW
        if number > secret_number:
            return GuessFeedback.TOO_HIGH

        return GuessFeedback.EXACT


class FairGuesserBot(IdentificationInfoMixin):
    def is_guess_number(self, game_id: str, min_val:int, max_val:int, attempt: int, number:int) -> GuessFeedback:
        log.info("is_guess_number()")

        # Defensive programming for internal Python calls (if bypassed msgspec).
        if not isinstance(min_val, int) or not isinstance(max_val, int):
            raise ValueError("Bounds must be strict integers.")

        if min_val >= max_val:
            raise ValueError(f"min_val {min_val} must be less than max_val {max_val}")

        # game_id arrived as a UUIDv7 string, for example, '018f1234-...'
        # The seed depends ONLY on the game_id, guaranteeing the same secret number across all attempts.
        #Note: random.Random() is PSEUDO-Random generator, for the same seed we will get exactly the same number.
        current_seed = f"{self.get_identification_info()}_{game_id}"

        # Initialize a local stateless generator
        rng = random.Random(current_seed)
        secret_number = rng.randint(min_val, max_val)

        if number < secret_number:
            return GuessFeedback.TOO_LOW
        if number > secret_number:
            return GuessFeedback.TOO_HIGH

        return GuessFeedback.EXACT





class BinarySearchBot(IdentificationInfoMixin):
    def make_your_guess(self, game_id: str, min_val: int, max_val: int, attempt: int, num:int) -> int:
        pass



