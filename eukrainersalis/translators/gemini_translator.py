import asyncio
import json
import os
from abc import ABC, abstractmethod
from importlib import resources
from typing import override, Tuple

from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from eukrainersalis.translators.translator_api import Translator
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import SystemInstruction
from eukrainersalis.utils.yaml_utils import localization_to_yaml, localization_from_yaml

load_dotenv()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_INSTRUCTIONS_PACKAGE = "eukrainersalis.resources.instructions"


def _load_instruction(name: str) -> str:
    try:
        return resources.files(_INSTRUCTIONS_PACKAGE).joinpath(f"{name}.txt").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"Instruction file not found: {name}.txt (expected in {_INSTRUCTIONS_PACKAGE})")


class TranslatorEncoder(ABC):
    @abstractmethod
    def encode(self, data: list[tuple[str, str]]) -> str:
        pass

    @abstractmethod
    def decode(self, data: str) -> Tuple[dict[str, str], list[Exception]]:
        pass


class JSONLTranslatorEncoder(TranslatorEncoder):
    def encode(self, data: list[tuple[str, str]]) -> str:
        json_lines = [json.dumps({t[0]: t[1]}, ensure_ascii=False) for t in data]
        return "\n".join(json_lines)

    def decode(self, data: str) -> Tuple[dict[str, str], list[Exception]]:
        translated_lines = data.split("\n")
        translated_batch: dict[str, str] = {}
        errors: list[Exception] = []
        for line in translated_lines:
            if len(line.strip()) == 0:
                continue

            def add_json_line(text: str):
                json_line = json.loads(text)
                for k, v in json_line.items():
                    if k in translated_batch:
                        logger.warning(
                            f"Overwriting already existing translation for {k}: {translated_batch[k]} ---> {v}")
                    translated_batch[k] = v

            try:
                add_json_line(line)
            except Exception:
                try:
                    # sometimes running into failing escape sequences
                    line = line.replace("\\", "\\\\")
                    add_json_line(line)
                except Exception as e:
                    logger.error(f"Expected a JSON but received:\n" + line)
                    errors.append(e)

        return translated_batch, errors


class YAMLTranslatorEncoder(TranslatorEncoder):
    def encode(self, data: list[tuple[str, str]]) -> str:
        data_dict = {t[0]: t[1] for t in data}
        return localization_to_yaml(data_dict)

    def decode(self, data: str) -> Tuple[dict[str, str], list[Exception]]:
        translated_batch: dict[str, str] = {}
        errors: list[Exception] = []
        for line in data.split("\n"):
            if len(line.strip()) == 0:
                continue

            try:
                localization = localization_from_yaml(line)
                for k, v in localization.items():
                    if k in translated_batch:
                        logger.warning(
                            f"Overwriting already existing translation for {k}: {translated_batch[k]} ---> {v}")
                    translated_batch[k] = v
            except Exception as e:
                logger.error(f"Failed to parse a yaml translation: {e}. Incoming text:\n{line}")
                errors.append(e)

        return translated_batch, errors


class GeminiTranslator(Translator):

    def __init__(self, model: str = DEFAULT_GEMINI_MODEL, system_instruction_config: SystemInstruction | None = None,
                 system_instruction_text: str | None = None):
        self.model = model
        if system_instruction_config is not None:
            self.system_instruction = _load_instruction(system_instruction_config)
        elif system_instruction_text is not None:
            self.system_instruction = system_instruction_text
        else:
            raise ValueError("Either system_instruction_config or system_instruction_text must be provided")

        self._gemini: genai.Client | None = None
        self._current_loop: asyncio.AbstractEventLoop | None = None
        self._retry_options = HttpRetryOptions(
            attempts=5,
            initial_delay=15,
            exp_base=2,
            max_delay=480,
        )

    @override
    def translate(self, text: str) -> str:
        return asyncio.run(self.translate_batch_async(text))

    @override
    async def translate_batch_async(self, text: str, match_line_count: bool = False) -> str:
        """Translate a single batch of lines via one API call, with retry on line-count mismatch.

        Args:
            text: Lines to translate (caller is responsible for batch sizing).
            match_line_count: Whether to retry on line-count mismatch.

        Returns:
            Translated lines, same length as input.
        """
        if not len(text.strip()):
            return ""

        translation = await self._translate_async(text)
        if match_line_count:
            expected_output_lines = text.count("\n") + 1
            result_lines = translation.count("\n") + 1
            if not translation or result_lines != expected_output_lines:
                await asyncio.sleep(5)
                translation = await self._translate_async(text)

        # Occasional Gemini glitch
        if translation.startswith("Thought") or translation.startswith("THOUGHT") and "The user" in translation:
            await asyncio.sleep(10)
            translation = await self._translate_async(text)

        return translation

    def _init_genai_client(self) -> genai.Client:
        return genai.Client(
            http_options=HttpOptions(retry_options=self._retry_options)
        )

    def _get_gemini_client(self) -> genai.Client:
        """Get or create Gemini client, recreating if event loop changed."""
        # try:
        #     current_loop = asyncio.get_running_loop()
        # except RuntimeError:
        #     current_loop = None
        #
        # if self._gemini is None or self._current_loop != current_loop:
        #     self._gemini = self._init_genai_client()
        #     self._current_loop = current_loop
        #
        # return self._gemini or self._init_genai_client()
        return self._init_genai_client()

    async def _translate_async(self, text: str) -> str:
        """Raw async API call."""
        async with self._init_genai_client().aio as aclient:
            response = await aclient.models.generate_content(
                model=self.model,
                contents=text,
                config=GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.15,
                ),
            )
            return response.text
