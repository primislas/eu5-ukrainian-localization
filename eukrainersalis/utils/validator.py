from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language, LocFile

MATCHING_CLOSED_BRACKETS = {
    '(': ')',
    '[': ']',
    '{': '}',
    # '«': '»',
    '\'': '\''
}


def validate_brackets_in_text(text: str) -> bool:
    stack = []
    # TODO: how to properly iterate with index
    for i, c in enumerate(text):
        if c == "'":
            if not stack:
                continue

            if stack[-1] == "'":
                stack.pop()
            else:
                stack.append(c)
            continue

        if c in MATCHING_CLOSED_BRACKETS:
            stack.append(c)
        elif c in MATCHING_CLOSED_BRACKETS.values():
            expected_closing_bracket = MATCHING_CLOSED_BRACKETS[stack.pop()] if stack else None
            if expected_closing_bracket != c:
                if expected_closing_bracket:
                    logger.warning(f"Unmatched closing bracket at index {i}: expected {expected_closing_bracket}, got {c}; {text[:i]}")
                else:
                    logger.warning(f"Unexpected closing bracket at index {i}: {c}; {text[:i]}")
                return False
    return not stack


def validate_brackets():
    error_count = 0
    for file_path in list_localization_files(Language.UK_UA_MACHINE_TRANSLATION):
        loc_file = LocFile(file_path).load()
        for loc_key, loc_value in loc_file.get_localization().items():
            if not validate_brackets_in_text(loc_value):
                logger.warning(f"Unmatched brackets at key {loc_key} ({loc_file.name()})")
                error_count += 1
    logger.info(f"Validation complete. Found {error_count} bracket errors.")

    return error_count == 0


if __name__ == "__main__":
    validate_brackets()
