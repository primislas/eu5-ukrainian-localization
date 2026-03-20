import re
from typing import override

from flask.cli import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from ukrainersalis_utils.logger import logger
from ukrainersalis_utils.translators.translation_api import Translator

_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEFAULT_SYSTEM_INSTRUCTION = """Role: You are a professional game localizer for the historical grand strategy game "Europa Universalis V".
Task: Translate English game script lines into Ukrainian.

### Rules:
1.  One-to-One Mapping: Translate each input line as a strictly independent unit. Every 1 line of input MUST result in exactly 1 line of output. Do not merge or split lines.
2.  Variable Preservation: Do NOT translate or modify script variables, engine constructs (items in square braces, in-between USD signs, expressions like '#L', '#1', other obvious scripting elements, e.g., '[GetPlayerName]', '[rebel|e]', '$COUNT$'), or escape sequences (e.g., \\n). Keep them exactly as they appear in the source.
3.  Historical Tone: Use a formal, archaic, or "chronicle" flair for narrative text and event descriptions. Use standard modern technical terms for UI settings, game mechanics.
4.  Specific Terms:
    *   "placeholder" -> "заповнювач"
    *   Geographic names: Use modern standard Ukrainian names.
    *   Names and last names: Use modern standard Ukrainian names.
5.  Low-Confidence Flagging: If you are uncertain about the translation of a proper noun (dynasty, ethnicity, culture), prefix it with 'POSTEDIT_'.
6.  Format: Output only the translated plain text. No explanations, no LaTeX, and no markdown formatting.

### Example:
Input:
[PROVINCE.GetName] does NOT have $COMPARATOR$ $NUM|V2$ [rebel|e] progress
This is a placeholder for the menu.
Output:
[PROVINCE.GetName] НЕ має $COMPARATOR$ $NUM|V2$ [rebel|e] прогресу
Це заповнювач для меню."""


class GeminiTranslator(Translator):
    def __init__(self, model: str = _DEFAULT_GEMINI_MODEL, system_instruction: str = _DEFAULT_SYSTEM_INSTRUCTION,
                 batch_size: int = 25, min_last_batch_size: int = 10):
        self.model = model
        self.system_instruction = system_instruction
        self._gemini: genai.Client | None = None
        self._batch_size = batch_size
        self._min_last_batch_size = min_last_batch_size

    @override
    def translate(self, text: str) -> str:
        """Translates the given text from English to Ukrainian using Gemini 2.5 Flash model.

        Args:
            text (str): The text to be translated.

        Returns:
            str: The translated text in Ukrainian.
        """

        lines = text.splitlines()
        if not lines:
            return ""

        batches = self._split_into_batches(lines)
        translations = []
        for batch in batches:
            batch_text = "\n".join(batch)
            translation = self._translate_to_match_line_count(batch_text, len(batch))
            output_lines = self._splitlines_and_pad_to_batch_size(translation, batch, len(translations))
            translations.extend(output_lines)
            logger.debug(f"Translated {len(translations)}/{len(lines)} phrases")

        return "\n".join(translations)

    def _get_gemini_client(self) -> genai.Client:
        if self._gemini is None:
            self._gemini = genai.Client(
                http_options=HttpOptions(
                    retry_options=HttpRetryOptions(
                        attempts=5,
                        initial_delay=15,
                        exp_base=2,
                        max_delay=480,
                    )
                )
            )
        return self._gemini

    def _split_into_batches(self, lines: list[str]):
        batches = []

        for i in range(0, len(lines), self._batch_size):
            batches.append(lines[i:i + self._batch_size])

        if len(batches) > 1 and len(batches[-1]) < self._min_last_batch_size:
            last_batch = batches.pop()
            batches[-1].extend(last_batch)

        return batches

    @staticmethod
    def _splitlines_and_pad_to_batch_size(text: str, input_batch: list[str], already_processed: int) -> list[str]:
        output_lines = text.splitlines()
        batch_size = len(input_batch)

        output_lines = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
        output_line_count = len(output_lines)

        if output_line_count > batch_size:
            logger.warning(
                f"Input line count ({batch_size}) is less than output line count ({output_line_count}), taking only {batch_size} first lines, records {already_processed}-{already_processed + batch_size}, translation:\n{text}")
            output_lines = output_lines[:batch_size]
        elif output_line_count < batch_size:
            logger.warning(
                f"Input line count ({batch_size}) is greater than output line count ({output_line_count}), padding with empty lines, records {already_processed}-{already_processed + batch_size}, translation:\n{text}")
            output_lines.extend([""] * (batch_size - output_line_count))

        return output_lines

    @staticmethod
    def _match_empty_phrases(output_lines: list[str], input_batch: list[str]) -> list[str]:
        """Aligns empty strings in output to match their positions in input.

        Scans input from left to right. If input has an empty string at an index,
        ensures output also has an empty string there, inserting it if it's not empty.
        If input has a non-empty string, ensures output has a non-empty string there,
        skipping any unexpected empty strings in output.
        """
        for i in range(len(input_batch)):
            if input_batch[i] == "":
                if i < len(output_lines) and output_lines[i] != "":
                    output_lines.insert(i, "")
            if i == len(output_lines):
                output_lines.append("")
        return output_lines

    @staticmethod
    def extract_response(translation_text: str) -> str:
        match = re.search(r"Thought:.*?Response:(.*)", translation_text, re.DOTALL)
        if match:
            return match.group(1).lstrip()
        return translation_text

    def _translate_to_match_line_count(self, text: str, expected_output_lines: int) -> str:
        translation = self._translate(text, expected_output_lines)
        translation = self.extract_response(translation)

        if len(translation.splitlines()) != expected_output_lines:
            # Oftentimes it's just a gemini glitch fixed on a retry
            translation = self._translate(text, expected_output_lines)
        translation = self.extract_response(translation)
        
        return translation

    def _translate(self, text: str, expected_output_lines: int) -> str:
        response = self._get_gemini_client().models.generate_content(
            model=self.model,
            contents=text,
            config=GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.15,
            ),
        )
        return response.text


if __name__ == "__main__":
    load_dotenv()
    _gemini = GeminiTranslator()
    _contents = """$VALUE$
PLACEHOLDER
#color:{0.9,0.1,0.1} $VALUE$#!
Entries in this layer cannot overlap, so grouping operation with multiple entries is not supported. Please select only one entry."""
    _translation = _gemini.translate(_contents)
    logger.info(_translation)
