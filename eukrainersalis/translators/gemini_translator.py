import asyncio
import os
from typing import override

from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, HttpOptions, HttpRetryOptions

from eukrainersalis.utils.log_utils import logger
from eukrainersalis.translators.translator_api import Translator
from eukrainersalis.utils.translation_utils import POSTEDIT_TRANSLATION_FAILURE


load_dotenv()
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

EN_UA_SYSTEM_INSTRUCTION = """Role: You are a professional game localizer for the historical grand strategy game "Europa Universalis V".
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
Task: Translate Russian game localization into Ukrainian. Each key-value is encoded as jsonl (one line - one json object with one key-value pair)..

### Rules:
1.  Keep JSON keys as is, translate only values.
2.  Variable Preservation: Do NOT translate or modify script variables, engine constructs (items in square braces, in-between USD signs, expressions like '#L', '#1', other obvious scripting elements, e.g., '[GetPlayerName]', '[rebel|e]', '$COUNT$'), or escape sequences (e.g., \\n). Keep them exactly as they appear in the source.
3.  Historical Tone: Use an archaic, flowery or "chronicle" flair for narrative text and event descriptions. Use standard modern technical terms for UI settings, game mechanics.
4.  Specific Terms:
    *   "заглушка" -> "заповнювач", when it's the only word in the line, or when it clearly applies to menus and settings.
    *   Geographic names: Use modern standard Ukrainian names.
    *   Names and last names: Use modern standard Ukrainian names.
    *   "махараджа" -> "магараджа", "Махараджья" -> "Магараджія", "Кингитанга" -> "Кінгітанга"
    *   "nobles"/"аристократы" -> "знать"
    *   "clergy"/"священники" -> "духовенство"
    *   "peasants"/"простолюдины" -> "простолюд"
5.  Low-Confidence Flagging: If you are uncertain about the translation of a proper noun (dynasty, ethnicity, culture), prefix it with 'POSTEDIT_'.
6.  Translate only Russian text. Do not translate any other language.
7.  Attempt to keep sentence structure as close to the original as possible.
8.  Sometimes you'll encounter constructs which signify gender-based endings, such as "ая", "ое", "ии". These are endings, translate them to corresponding Ukrainian endings. For example, "ие" - "і", "ая" - "а", "ое" - "е", "ий" - "ий", "ые" - "і", etc.
9.  Sometimes you'll encounter adjectives without endings. Translate them to Ukrainian adjectives and also remove endings. For example, "французск" -> "французськ", "немецк" -> "німецьк", "казахск" -> "казахськ", etc. This is a standard case for keys ending with "_ADJ".
10.  Keep NBSP symbols, if available in the source text, in-between equivalent words in translated text, if applicable and structure isn't too different.
11.  Always translate Russian text in "EqualTo_string" function and other functions and keep capitalization as in the source, e.g. "EqualTo_string('Вице-королевство', '$RANK$')" -> "EqualTo_string('Віцекоролівство', '$RANK$')"
12.  Translate "район" in 'location(s)' concept as "місцевість", e.g.: "Concept('locations', 'районы')" -> "Concept('locations', 'місцевості')",  "Concept('location', 'район')" -> "Concept('location', 'місцевість')"
13.  Format: Output only the result. No thoughts, no explanation, no LaTeX, and no markdown formatting. One-to-one mapping is expected - one output line with translated json per one input jsonl.

### Example:
Input:
{"some.event.ley": "[PROVINCE.GetName] отсутствует $COMPARATOR$ $NUM|V2$ [rebel|e] прогрес"}
{"MENU_ITEM": "Это заглушка для меню\\n"}
{"culture_languageKEY": "[Concept('language','Язык')|e]: #L [CountryCultureLateralView.GetCulture.GetLanguage.GetName|l]ое#!"}
{"GLH_horde_ADJ": "Золотоордынск"}
{"cotton.declension": "[AddTextIf(EqualTo_string('Хлопок', TARGET_GOODS.GetNameWithNoTooltip), 'хлопка')|l]"}
{"Goods_GetNameWithNoTooltip_RU_GEN": "[AddTextIf(EqualTo_string('Лошади', TARGET_GOODS.GetNameWithNoTooltip), 'Лошадей')|l]"}
Output:
{"some.event.ley": "[PROVINCE.GetName] відсутній $COMPARATOR$ $NUM|V2$ [rebel|e] прогрес"}
{"MENU_ITEM": "Це заповнювач для меню\\n"}
{"culture_languageKEY": "[Concept('language','Мова')|e]: #L [CountryCultureLateralView.GetCulture.GetLanguage.GetName|l]е#!"}
{"GLH_horde_ADJ": "Золотоординськ"}
{"cotton.declension": "[AddTextIf(EqualTo_string('Бавовна', TARGET_GOODS.GetNameWithNoTooltip), 'бавовни')|l]"}
{"Goods_GetNameWithNoTooltip_RU_GEN": "[AddTextIf(EqualTo_string('Коні', TARGET_GOODS.GetNameWithNoTooltip), 'Коней')|l]"}"""


class GeminiTranslator(Translator):
    def __init__(self, model: str = DEFAULT_GEMINI_MODEL, system_instruction: str = EN_UA_SYSTEM_INSTRUCTION):
        self.model = model
        self.system_instruction = system_instruction
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
    _gemini = GeminiTranslator()
    _contents = """$VALUE$
PLACEHOLDER
#color:{0.9,0.1,0.1} $VALUE$#!
Entries in this layer cannot overlap, so grouping operation with multiple entries is not supported. Please select only one entry."""
    _translation = _gemini.translate(_contents)
    logger.info(_translation)
