import asyncio
from typing import override

from flask.cli import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from eukrainersalis.utils.log_utils import logger
from eukrainersalis.translators.translator_api import Translator
from eukrainersalis.utils.translation_utils import POSTEDIT_TRANSLATION_FAILURE

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_SYSTEM_INSTRUCTION = """Role: You are a professional game localizer for the historical grand strategy game "Europa Universalis V".
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
RU_UA_SYSTEM_INSTRUCTION = """Role: You are a professional game localizer for the historical grand strategy game "Europa Universalis V".
Task: Translate Ukraine game script lines into Ukrainian.

### Rules:
1.  One-to-One Mapping: Translate each input line as a strictly independent unit. Every 1 line of input MUST result in exactly 1 line of output. Do not merge or split lines.
2.  Variable Preservation: Do NOT translate or modify script variables, engine constructs (items in square braces, in-between USD signs, expressions like '#L', '#1', other obvious scripting elements, e.g., '[GetPlayerName]', '[rebel|e]', '$COUNT$'), or escape sequences (e.g., \\n). Keep them exactly as they appear in the source.
3.  Historical Tone: Use an archaic, flowery or "chronicle" flair for narrative text and event descriptions. Use standard modern technical terms for UI settings, game mechanics.
4.  Specific Terms:
    *   "заглушка" -> "заповнювач", when it's the only word in the line, or when it clearly applies to menus and settings.
    *   Geographic names: Use modern standard Ukrainian names.
    *   Names and last names: Use modern standard Ukrainian names.
5.  Low-Confidence Flagging: If you are uncertain about the translation of a proper noun (dynasty, ethnicity, culture), prefix it with 'POSTEDIT_'.
6.  Translate only Russian text. Do not translate any other language.
7.  Attempt to keep sentence structure as close to the original as possible.
8.  Sometimes you'll encounter constructs which signify gender-based endings, such as "ая", "ое", "ии". These are endings, translate them to corresponding Ukrainian endings. For example, "ие" - "і", "ая" - "а", "ое" - "е", "ий" - "ий", "ые" - "і", etc.
9.  Sometimes you'll encounter adjectives without endings. Translate them to Ukrainian adjectives and also remove endings. For example, "французск" -> "французськ", "немецк" -> "німецьк", etc.
10.  Keep NBSP symbols, if available in the source text, in-between equivalent words in translated text, if applicable and structure isn't too different.
11.  Format: Output only the translated plain text. Only the result. No thoughts, no explanation, no LaTeX, and no markdown formatting.

### Example:
Input:
[PROVINCE.GetName] отсутствует $COMPARATOR$ $NUM|V2$ [rebel|e] прогрес
Это заглушка для меню
[Concept('language','Язык')|e]: #L [CountryCultureLateralView.GetCulture.GetLanguage.GetName|l]ое#!
Output:
[PROVINCE.GetName] відсутній $COMPARATOR$ $NUM|V2$ [rebel|e] прогрес
Це заповнювач для меню.
[Concept('language','Мова')|e]: #L [CountryCultureLateralView.GetCulture.GetLanguage.GetName|l]е#!"""


class GeminiTranslator(Translator):
    def __init__(self, model: str = DEFAULT_GEMINI_MODEL, system_instruction: str = DEFAULT_SYSTEM_INSTRUCTION,
                 batch_size: int = 25, min_last_batch_size: int = 10, max_concurrent_batches: int = 8):
        self.model = model
        self.system_instruction = system_instruction
        self._gemini: genai.Client | None = None
        self._batch_size = batch_size
        self._min_last_batch_size = min_last_batch_size
        self._max_concurrent_batches = max_concurrent_batches
        self._current_loop: asyncio.AbstractEventLoop | None = None

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

        # Run all batches concurrently, preserving order
        translations = asyncio.run(self._translate_batches_async(batches))

        return "\n".join(translations)

    async def translate_async(self, text: str) -> str:
        """Async version of translate for use within async contexts.

        Args:
            text (str): The text to be translated.

        Returns:
            str: The translated text in Ukrainian.
        """
        lines = text.splitlines()
        if not lines:
            return ""

        batches = self._split_into_batches(lines)
        translations = await self._translate_batches_async(batches)

        return "\n".join(translations)

    async def _translate_batches_async(self, batches: list[list[str]]) -> list[str]:
        """Translates all batches concurrently while preserving order.

        Args:
            batches: List of text batches to translate

        Returns:
            Flat list of all translated lines in order
        """
        # Create semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(self._max_concurrent_batches)

        # Calculate total lines for progress tracking
        total_lines = sum(len(batch) for batch in batches)
        total_batches = len(batches)

        # Create tasks for all batches - gather preserves order
        tasks = [
            self._translate_batch_async(i, batch, semaphore, total_batches, total_lines)
            for i, batch in enumerate(batches)
        ]

        # Execute concurrently with limited parallelism, results maintain order
        # return_exceptions=True prevents one failure from canceling all tasks
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results, handling exceptions
        translations = []
        for batch_idx, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"Batch {batch_idx + 1}/{total_batches} failed: {result}")
                # Fill with empty strings to maintain line count
                translations = [POSTEDIT_TRANSLATION_FAILURE] * len(batches[batch_idx])
            else:
                translations.extend(result)

        return translations

    async def _translate_batch_async(self, batch_index: int, batch: list[str],
                                     semaphore: asyncio.Semaphore, total_batches: int,
                                     total_lines: int) -> list[str]:
        """Translates a single batch asynchronously.

        Args:
            batch_index: Index of this batch (for logging)
            batch: Lines to translate
            semaphore: Semaphore to limit concurrent requests
            total_batches: Total number of batches
            total_lines: Total number of lines across all batches

        Returns:
            Translated lines for this batch
        """
        async with semaphore:
            batch_text = "\n".join(batch)
            translation = await self._translate_to_match_line_count_async(batch_text, len(batch))
            output_lines = self._splitlines_and_pad_to_batch_size(translation, batch)

            # Calculate completed phrases
            if batch_index + 1 == total_batches:
                completed_phrases = total_lines
            else:
                completed_phrases = (batch_index + 1) * self._batch_size

            logger.debug(f"Translated {completed_phrases}/{total_lines} phrases")

            return output_lines

    def _get_gemini_client(self) -> genai.Client:
        """Get or create Gemini client, recreating if event loop changed."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop - will be created by asyncio.run()
            current_loop = None

        # Recreate client if event loop changed or client doesn't exist
        if self._gemini is None or self._current_loop != current_loop:
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
            self._current_loop = current_loop

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
    def _splitlines_and_pad_to_batch_size(text: str, input_batch: list[str]) -> list[str]:
        output_lines = text.splitlines()
        batch_size = len(input_batch)

        output_lines = GeminiTranslator._match_empty_phrases(output_lines, input_batch)
        output_line_count = len(output_lines)

        if output_line_count > batch_size:
            logger.warning(
                f"Input line count ({batch_size}) is less than output line count ({output_line_count}), assuming an error, translation:\n{text}")
            output_lines = [POSTEDIT_TRANSLATION_FAILURE] * batch_size
        elif output_line_count < batch_size:
            logger.warning(
                f"Input line count ({batch_size}) is greater than output line count ({output_line_count}), assuming an error, translation:\n{text}")
            output_lines = [POSTEDIT_TRANSLATION_FAILURE] * batch_size

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

    async def _translate_to_match_line_count_async(self, text: str, expected_output_lines: int) -> str:
        """Async version of translate with retry for line count mismatch."""
        translation = await self._translate_async(text, expected_output_lines)
        if not translation or len(translation.splitlines()) != expected_output_lines:
            await asyncio.sleep(5)
            translation = await self._translate_async(text, expected_output_lines)
            # Occasional Gemini glitch
            if translation.startswith("Thought") or translation.startswith("THOUGHT") and "The user" in translation:
                await asyncio.sleep(10)
                translation = await self._translate_async(text, expected_output_lines)

        if not translation:
            translation = "\n".join(["POSTEDIT_FAILED_TRANSLATION"] * expected_output_lines)

        return translation

    async def _translate_async(self, text: str, expected_output_lines: int) -> str:
        """Async translation using native genai async API."""
        response = await self._get_gemini_client().aio.models.generate_content(
            model=self.model,
            contents=text,
            config=GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.15,
            ),
        )
        return response.text

    def _translate_to_match_line_count(self, text: str, expected_output_lines: int) -> str:
        translation = self._translate(text, expected_output_lines)
        if len(translation.splitlines()) != expected_output_lines:
            translation = self._translate(text, expected_output_lines)

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
