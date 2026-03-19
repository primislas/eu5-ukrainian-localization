from typing import override

from flask.cli import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig

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
    def __init__(self, model: str = _DEFAULT_GEMINI_MODEL, system_instruction: str = _DEFAULT_SYSTEM_INSTRUCTION):
        self.model = model
        self.system_instruction = system_instruction
        self._gemini: genai.Client | None = None

    @override
    def translate(self, text: str) -> str:
        """Translates the given text from English to Ukrainian using Gemini 2.5 Flash model.

        Args:
            text (str): The text to be translated.

        Returns:
            str: The translated text in Ukrainian.
        """
        if self._gemini is None:
            self._gemini = genai.Client()

        lines = text.splitlines()
        if not lines:
            return ""

        batches = []
        batch_size = 50
        min_last_batch_size = 20

        for i in range(0, len(lines), batch_size):
            batches.append(lines[i:i + batch_size])

        if len(batches) > 1 and len(batches[-1]) < min_last_batch_size:
            last_batch = batches.pop()
            batches[-1].extend(last_batch)

        translated_batches = []
        for batch in batches:
            batch_text = "\n".join(batch)
            response = self._gemini.models.generate_content(
                model=self.model,
                contents=batch_text,
                config=GenerateContentConfig(system_instruction=self.system_instruction),
            )
            translated_batches.append(response.text.strip())

        return "\n".join(translated_batches)


if __name__ == "__main__":
    load_dotenv()
    gemini = GeminiTranslator()
    contents = """$VALUE$
PLACEHOLDER
#color:{0.9,0.1,0.1} $VALUE$#!
Entries in this layer cannot overlap, so grouping operation with multiple entries is not supported. Please select only one entry."""
    translation = gemini.translate(contents)
    logger.info(translation)
