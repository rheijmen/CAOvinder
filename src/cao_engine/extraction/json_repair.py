"""JSON repair utilities for LLM responses.

Handles common JSON errors in LLM outputs:
- Unterminated strings
- Missing closing braces/brackets
- Trailing commas
- Markdown code blocks
- Escape sequence errors
"""

import json
import re


def repair_json(text: str) -> str:
    """Attempt to repair common JSON errors in LLM responses.

    Args:
        text: Potentially broken JSON text from LLM

    Returns:
        Repaired JSON text (still needs to be validated with json.loads)

    Raises:
        json.JSONDecodeError: If repair is impossible
    """
    original = text

    # Step 1: Remove markdown code blocks if present
    text = re.sub(r'^```json\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```$', '', text, flags=re.MULTILINE)
    text = text.strip()

    # Step 2: Try to find the last complete JSON object
    # This handles unterminated strings at the end
    last_brace = text.rfind('}')
    if last_brace != -1:
        # Try to parse up to this point
        candidate = text[:last_brace + 1]
        try:
            json.loads(candidate)
            text = candidate
        except json.JSONDecodeError:
            # If that doesn't work, continue with full text
            pass

    # Step 3: Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # Step 4: Fix common escape sequence errors
    # Replace invalid escape sequences
    text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)

    # Step 5: Try to complete unterminated arrays/objects
    # Count opening and closing braces
    open_braces = text.count('{')
    close_braces = text.count('}')
    open_brackets = text.count('[')
    close_brackets = text.count(']')

    # Add missing closing brackets/braces
    text += ']' * (open_brackets - close_brackets)
    text += '}' * (open_braces - close_braces)

    # Step 6: Validate the result
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError as e:
        # If we still can't parse, try one more aggressive approach:
        # Extract everything between first { and last }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            extracted = match.group(0)
            try:
                json.loads(extracted)
                return extracted
            except json.JSONDecodeError:
                pass

        # Give up - raise the original error
        raise json.JSONDecodeError(
            f"Could not repair JSON. Original error: {e}",
            text,
            e.pos
        ) from e


def try_parse_with_repair(text: str) -> dict:
    """Try to parse JSON, with automatic repair if needed.

    Args:
        text: JSON text from LLM (may be broken)

    Returns:
        Parsed JSON dict

    Raises:
        json.JSONDecodeError: If parsing and repair both fail
    """
    # First try: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Second try: repair then parse
    repaired = repair_json(text)
    return json.loads(repaired)


def extract_json_from_mixed_content(text: str) -> dict | list:
    """Extract JSON from text that may contain non-JSON content.

    Useful when LLM adds explanatory text before/after JSON.

    Args:
        text: Mixed content containing JSON

    Returns:
        Extracted and parsed JSON (dict or list)

    Raises:
        ValueError: If no valid JSON found in text
    """
    # Try to find JSON object
    obj_match = re.search(r'\{.*\}', text, re.DOTALL)
    if obj_match:
        try:
            return try_parse_with_repair(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try to find JSON array
    arr_match = re.search(r'\[.*\]', text, re.DOTALL)
    if arr_match:
        try:
            return try_parse_with_repair(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("No valid JSON object or array found in text")
