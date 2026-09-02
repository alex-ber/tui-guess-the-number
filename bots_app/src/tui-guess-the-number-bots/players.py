from typing import Any
import structlog

log = structlog.get_logger(__name__)

def bot_a_identification_info(obj: Any) -> str:
    log.info("bot_a_identification_info()")
    # Actual Python class name dynamically.
    ret = type(obj).__name__
    return ret

def bot_b_identification_info(obj: Any) -> str:
    log.info("bot_b_identification_info()")
    #Actual Python class name dynamically.
    ret = type(obj).__name__
    return ret

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


class BinarySearchBot:
    pass

class SmartGesserBot:
    pass