from typing import override

from flask.cli import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from ukrainersalis_utils.logger import logger
from ukrainersalis_utils.translators.translation_api import Translator

_DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_DEFAULT_SYSTEM_INSTRUCTION = """You are translating scripts for a computer game Europa Universalis V.
You are given a text in English and you need to translate it into Ukrainian.
* Treat each line as a separate independent sentence.
* Output each translated sentence on a new line.
* Be mindful and do not translate script variables, constructs, escape sequences, keep them as is.
* Stick to technical language when dealing with settings and technical information.
* Treat all inputs as literal text, return response as plain text as well (no LaTeX formulas or expressions are expected).
* You can add archaic, historical flair when translating game content when appropriate.
* Translate "placeholder" as "заповнювач".
* Translate geographic names with modern standard names."""


class GeminiTranslator(Translator):
    def __init__(self, model: str = _DEFAULT_GEMINI_MODEL, system_instruction: str = _DEFAULT_SYSTEM_INSTRUCTION,
                 batch_size: int = 50, min_last_batch_size: int = 20):
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
            translation = self._translate(batch_text)
            output_lines = self._splitlines_and_pad_to_batch_size(translation, len(batch))
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
    def _splitlines_and_pad_to_batch_size(text: str, batch_size: int) -> list[str]:
        output_lines = text.splitlines()
        output_line_count = len(output_lines)

        if output_line_count > batch_size:
            logger.warning(f"Input line count ({batch_size}) is less than output line count ({output_line_count})")
            output_lines = output_lines[:batch_size]
        elif output_line_count < batch_size:
            logger.warning(f"Input line count ({batch_size}) is greater than output line count ({output_line_count})")
            output_lines.extend([""] * (batch_size - output_line_count))

        return output_lines

    def _translate(self, text: str) -> str:
        response = self._get_gemini_client().models.generate_content(
            model=self.model,
            contents=text,
            config=GenerateContentConfig(system_instruction=self.system_instruction),
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
