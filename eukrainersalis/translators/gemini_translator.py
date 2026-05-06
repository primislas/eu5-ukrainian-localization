import asyncio
import os
from importlib import resources
from typing import override

from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from eukrainersalis.utils.log_utils import logger
from eukrainersalis.translators.translator_api import Translator
from eukrainersalis.utils.translation_utils import POSTEDIT_TRANSLATION_FAILURE, SystemInstruction

load_dotenv()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_INSTRUCTIONS_PACKAGE = "eukrainersalis.resources.instructions"


def _load_instruction(name: str) -> str:
    try:
        return resources.files(_INSTRUCTIONS_PACKAGE).joinpath(f"{name}.txt").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Instruction file not found: {name}.txt (expected in {_INSTRUCTIONS_PACKAGE})")


class GeminiTranslator(Translator):
    def __init__(self, model: str = DEFAULT_GEMINI_MODEL, system_instruction_config: SystemInstruction = SystemInstruction.RU_UA):
        self.model = model
        self.system_instruction = _load_instruction(system_instruction_config)
        self._gemini: genai.Client | None = None
        self._current_loop: asyncio.AbstractEventLoop | None = None

    @override
    def translate(self, text: str) -> str:
        lines = text.splitlines()
        if not lines:
            return ""
        return "\n".join(asyncio.run(self.translate_batch_async(lines)))

    @override
    async def translate_batch_async(self, lines: list[str]) -> list[str]:
        """Translate a single batch of lines via one API call, with retry on line-count mismatch.

        Args:
            lines: Lines to translate (caller is responsible for batch sizing).

        Returns:
            Translated lines, same length as input.
        """
        if not lines:
            return []

        batch_text = "\n".join(lines)
        translation = await self._translate_to_match_line_count_async(batch_text, len(lines))
        return self._splitlines_and_pad_to_batch_size(translation, lines)

    def _get_gemini_client(self) -> genai.Client:
        """Get or create Gemini client, recreating if event loop changed."""
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

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

    @staticmethod
    def _splitlines_and_pad_to_batch_size(text: str, input_batch: list[str]) -> list[str]:
        batch_size = len(input_batch)
        output_lines = text.splitlines()
        output_line_count = len(output_lines)

        if output_line_count != batch_size:
            logger.warning(
                f"Input line count ({batch_size}) != output line count ({output_line_count}), "
                f"marking batch as failed:\n{text}"
            )
            output_lines = [POSTEDIT_TRANSLATION_FAILURE] * batch_size

        return output_lines

    async def _translate_to_match_line_count_async(self, text: str, expected_output_lines: int) -> str:
        """Translate with retry on line-count mismatch."""
        translation = await self._translate_async(text)
        if not translation or len(translation.splitlines()) != expected_output_lines:
            await asyncio.sleep(5)
            translation = await self._translate_async(text)
            # Occasional Gemini glitch
            if translation.startswith("Thought") or translation.startswith("THOUGHT") and "The user" in translation:
                await asyncio.sleep(10)
                translation = await self._translate_async(text)

        if not translation:
            translation = "\n".join([POSTEDIT_TRANSLATION_FAILURE] * expected_output_lines)

        return translation

    async def _translate_async(self, text: str) -> str:
        """Raw async API call."""
        response = await self._get_gemini_client().aio.models.generate_content(
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
    _gemini = GeminiTranslator(system_instruction_config=SystemInstruction.EN_UA)
    _contents = """$VALUE$
PLACEHOLDER
#color:{0.9,0.1,0.1} $VALUE$#!
Entries in this layer cannot overlap, so grouping operation with multiple entries is not supported. Please select only one entry."""
    _translation = _gemini.translate(_contents)
    logger.info(_translation)
