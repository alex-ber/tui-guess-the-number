import ast
import decimal
from datetime import datetime, time
from enum import Enum
from typing import Any

# Handle bitarray optionally, as it is a third-party library
try:
    from bitarray import bitarray
except ImportError:
    class bitarray:  # type: ignore
        """Dummy class to prevent isinstance errors if bitarray is not installed."""
        pass


def str_to_bool(val: str | None, default: bool | None = None) -> bool:
    """
    Convert a string representation of truth to a boolean.
    Returns the default value if val is None.
    Raises ValueError if the value is not recognized, or if val is None and default is None.
    """
    if val is None:
        if default is not None:
            ret = default
            return ret
        raise ValueError("Cannot convert None to boolean without a default value.")

    val = val.strip().lower()

    if val in ('true', 't', 'yes', 'y', 'on', '1'):
        ret = True
        return ret
    if val in ('false', 'f', 'no', 'n', 'off', '0'):
        ret = False
        return ret

    raise ValueError(f"Cannot convert {val!r} to boolean.")


def _is_iterable(value: Any) -> bool:
    """Check if a value is iterable, safely excluding primitive strings and bytes."""
    if value is None or isinstance(value, (str, bytes)):
        return False

    try:
        iter(value)
        return True
    except TypeError:
        return False


def _is_mapping(value: Any) -> bool:
    """
    Check if a value behaves like a mapping (e.g., dictionary) safely.
    """
    if value is None or isinstance(value, (str, bytes)):
        return False

    items_attr = getattr(value, 'items', None)
    ret =  callable(items_attr)
    return ret


def _traverse_and_convert(obj: Any, is_raise_on_failure: bool, *enum_classes: type[Enum] | None) -> Any:
    """
    Recursively traverse iterables and apply conversions.
    Delegates all scalar types (including strings, bytes, time, etc.) to convert_scalar.
    """
    # 1. Handle dictionaries specifically to preserve key-value mappings
    if _is_mapping(obj):
        ret = {k: _traverse_and_convert(v, is_raise_on_failure, *enum_classes) for k, v in obj.items()}
        return ret

    # 2. If it's not iterable (which includes str, bytes, None, and custom scalars like Decimal/time),
    # delegate to convert_scalar for type processing or fallback.
    if not _is_iterable(obj):
        ret = convert_scalar(obj, is_raise_on_failure, *enum_classes)
        return ret

    # 3. Process generic iterables using pythonic iteration
    ret = []
    for v in obj:
        # Apply recursive conversion to all internal elements
        converted_value = _traverse_and_convert(v, is_raise_on_failure, *enum_classes)
        ret.append(converted_value)

    return ret

def convert_scalar(value: Any, is_raise_on_failure: bool = True, *enum_classes: type[Enum] | None) -> Any:
    """
    Attempt to convert a scalar string value to a specific type:
    Python literal, None, boolean, datetime, or Enum.
    Also handles special formatting for time, decimal, bytes, and bitarray (moved up to prevent dead code).
    """
    if value is None:
        return value

    # 1. Handle special formatting types BEFORE the string check to avoid unreachable dead code
    if isinstance(value, time):
        ret = value.strftime("%H:%M:%S")
        return ret

    if isinstance(value, decimal.Decimal):
        ret = str(value)
        return ret

    if isinstance(value, bytes):
        ret = value.decode('utf8').replace("'", '"')
        return ret

    if isinstance(value, bitarray):
        ret = value.to01()  # type: ignore
        return ret

    # Guard: If value is not a string after evaluating special types, return it as is
    if not isinstance(value, str):
        return value

    eval_error = None

    # 2. Attempt to parse as a basic Python literal (e.g., int, float, list, dict)
    try:
        parsed = ast.literal_eval(value)

        # If the evaluated literal is a collection, recursively process its nested elements
        if _is_iterable(parsed):
            ret = _traverse_and_convert(parsed, is_raise_on_failure, *enum_classes)
            return ret

        # If it parsed into a basic type (like int, float, or cleanly quoted string), return it
        ret = parsed
        return ret
    except (SyntaxError, ValueError) as e:
        # Evaluation failed, meaning it's likely a custom scalar format (e.g., datetime, unquoted bool).
        # We capture 'e' to chain it later if all subsequent conversion attempts fail.
        eval_error = e

    clean_val = value.strip()
    lower_val = clean_val.casefold()

    # 3. Check for explicit 'none'
    if lower_val == 'none':
        return None

    # 4. Check for boolean string representations
    try:
        ret = str_to_bool(clean_val)
        return ret
    except ValueError:
        pass

    # 5. Check for datetime formats
    try:
        ret = datetime.fromisoformat(clean_val)
        return ret
    except ValueError:
        pass

    try:
        ret = datetime.strptime(clean_val, "%Y-%m-%d %H:%M:%S")
        return ret
    except ValueError:
        pass

    # 6. Check for Enum membership (Note: First matching Enum takes precedence)
    if enum_classes:
        for enum_class in enum_classes:
            if enum_class is not None:
                try:
                    ret = enum_class(clean_val)
                    return ret
                except ValueError:
                    pass

    # 7. Failure handling with exception chaining
    if is_raise_on_failure:
        raise ValueError(
            f"convert_scalar() was unable to resolve {value!r} of type {type(value).__name__}"
        ) from eval_error

    return value


def parse_str(element: Any, is_raise_on_failure: bool = False, *enum_classes: type[Enum] | None) -> Any:
    """
    Parse a string containing nested structures or scalar values.
    """

    if not isinstance(element, str):
        return element

    # _traverse_and_convert immediately delegates string types to convert_scalar,
    # which inherently attempts ast.literal_eval and processes all fallback conversions.
    ret = _traverse_and_convert(element, is_raise_on_failure, *enum_classes)
    return ret
