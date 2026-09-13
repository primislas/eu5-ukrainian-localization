import asyncio
import json
import os
from dataclasses import dataclass
from enum import StrEnum
from importlib import resources
from importlib.resources.abc import Traversable
from typing import Callable

from dotenv import load_dotenv

from eukrainersalis.translators.gemini_translator import GeminiTranslator
from eukrainersalis.utils.file_utils import list_localization_files, project_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.migration_utils import MigrationManager
from eukrainersalis.utils.translation_utils import Language, LocFile, split_into_batches, TranslationResult, \
    TranslationLocKeyFileManager
from eukrainersalis.utils.yaml_utils import load_eu5_yaml

_INSTRUCTION_PACKAGE = "eukrainersalis.resources.instructions"
_INSTRUCTION_SKILL_REL_PATH = "skills/refinement"
_INSTRUCTION_ROLE_FILE = "role"


def _get_refinement_skill_file(file_name_without_extension: str) -> Traversable:
    return resources.files(_INSTRUCTION_PACKAGE).joinpath(f"{_INSTRUCTION_SKILL_REL_PATH}/{file_name_without_extension}.txt")


def select_none(_: str) -> bool:
    return False


def select_administration_refinement(text: str) -> bool:
    return "адміністра" in text


def select_center_refinement(text: str) -> bool:
    return "центр" in text


def select_talent_refinement(text: str) -> bool:
    return "талант" in text or "талановит" in text


def select_territory_refinement(text: str) -> bool:
    return "територі" in text


class RefinementSkill(StrEnum):
    ADMINISTRATION = "administration"
    CENTER = "center"
    TALENT = "talent"
    TERRITORY = "territory"

    def get_filter(self) -> Callable[[str], bool]:
        match self:
            case RefinementSkill.TERRITORY:
                return select_territory_refinement
            case _:
                return lambda text: False

    def get_system_instruction(self) -> str:
        role = _get_refinement_skill_file(_INSTRUCTION_ROLE_FILE).read_text()
        skill_task = _get_refinement_skill_file(self).read_text()
        return role + "<task_instructions>\n" + skill_task + "\n</task_instructions>"


@dataclass
class RefinementManager:
    refinement_id: str
    refinement_skill: RefinementSkill
    refinement_tracker_dir: str = project_dir / "migrations"
    max_files: int = 50
    entries_threshold: int = 85
    batch_size: int = 25
    language: Language = Language.RUSSIAN
    max_concurrency: int = 1

    def __init__(self, refinement_id: str, refinement_skill: RefinementSkill, entries_threshold: int = 85):
        self.refinement_id = refinement_id
        self.refinement_skill = refinement_skill
        self._refinement_tracker = MigrationManager(
            migration_id=self.refinement_id,
            migration_tracker_dir=self.refinement_tracker_dir,
        )
        self.entries_threshold = entries_threshold

        self._translator = GeminiTranslator(system_instruction_text=self.refinement_skill.get_system_instruction())


    def select_files(self, filter_func: Callable[[str], bool], max_files: int | None = None, entries_threshold: int | None = None) -> list[LocFile]:
        if not filter_func:
            return []

        max_files = self.max_files if max_files is None else max_files
        entries_threshold = self.entries_threshold if entries_threshold is None else entries_threshold

        matching_files = []
        matching_keys_total = 0
        localization_key = self.language.localization_key
        for file in list_localization_files(Language.UK_UA_MACHINE_TRANSLATION):
            if self._refinement_tracker.is_processed(file):
                continue

            matching_keys = []
            content = load_eu5_yaml(file)
            localization: dict[str, str] = content.get(localization_key, {})
            for k, v in localization.items():
                v_lower = v.lower()
                if "територі" in v_lower:
                    print(k)
                if filter_func(v_lower):
                    matching_keys.append(k)
            if matching_keys:
                loc_file = LocFile(file, matching_keys, content, localization_key)
                matching_files.append(loc_file)
                matching_keys_total += len(matching_keys)
            else:
                self._refinement_tracker.mark_processed(file)
            if matching_keys_total >= entries_threshold or len(matching_files) >= max_files:
                break

        return matching_files


    async def translate_batch(
            self,
            batch: list[tuple[str, str]],
            api_semaphore: asyncio.Semaphore,
            batch_idx: int,
            total_batches: int,
    ) -> TranslationResult:
        """Translate one batch and immediately save progress to file."""
        batch_size = len(batch)
        result = TranslationResult(total_records=batch_size, total_submitted_records=batch_size, submitted_records=batch)
        async with api_semaphore:
            lines = [json.dumps({k: v}, ensure_ascii=False) for k, v in batch]
            try:
                translated_lines = await self._translator.translate_batch_async(lines)
            except Exception as e:
                logger.error(f"Batch {batch_idx + 1}/{total_batches} failed: {e}")
                batch_keys = [t[0] for t in batch]
                batch_keys_str = ", ".join(batch_keys)
                logger.debug(f"Failed batch keys are: {batch_keys_str}")
                result.add_error(e)
                return result

        successful_translations = 0
        # async with write_lock:
        translated_batch: dict[str, str] = {}
        for line in translated_lines:
            # line = translation_postprocessing(line)
            json_line: dict[str, str] = {}
            try:
                json_line = json.loads(line)
            except Exception:
                try:
                    # sometimes running into failing escape sequences
                    line = line.replace("\\", "\\\\")
                    json_line = json.loads(line)
                except Exception as e:
                    logger.error(f"Expected a JSON but received: " + line)
                    result.add_error(e)
            if json_line:
                for k, v in json_line.items():
                    if len(v) == 0:
                        translated_batch[k] = "POSTEDIT_EMPTY_TRANSLATION"
                    else:
                        translated_batch[k] = v
                        successful_translations += 1

        result.translated_records = successful_translations
        result.translated_localizations = translated_batch
        return result


    async def translate_and_save_batch(
            self,
            batch: list[tuple[str, str]],
            translation_mgr: TranslationLocKeyFileManager,
            api_semaphore: asyncio.Semaphore,
            batch_idx: int,
            total_batches: int,
    ) -> TranslationResult:
        translation = await self.translate_batch(batch, api_semaphore, batch_idx, total_batches)
        loc_files = await translation_mgr.write_translated_keys(translation.translated_localizations)
        translated_files = [f for f in loc_files if translation_mgr.is_file_translated(f)]
        for file in translated_files:
            self._refinement_tracker.mark_processed(file.file_path)

        return translation

    def select_filter(self):
        match self.refinement_skill:
            case RefinementSkill.TERRITORY:
                return select_territory_refinement
            case RefinementSkill.TALENT:
                return select_talent_refinement
            case RefinementSkill.CENTER:
                return select_center_refinement
            case RefinementSkill.ADMINISTRATION:
                return select_administration_refinement


    async def refine(self):
        logger.info(f"Refining: {self.refinement_id}...")
        api_semaphore = asyncio.Semaphore(self.max_concurrency)
        refinement_filter = self.select_filter()

        skill_files = self.select_files(refinement_filter, max_files=500)
        if not skill_files:
            logger.info(f"Found no files in need of refinement.")
            return

        logger.info(f"Selected {len(skill_files)} files for refinement with {sum([len(t_file.selected_keys) for t_file in skill_files])} loc keys.")
        file_by_key = {}
        unrefined_values = {}
        for t_file in skill_files:
            for key in t_file.selected_keys:
                file_by_key[key] = t_file
            unrefined_values = unrefined_values | t_file.select_values()

        batches = split_into_batches(list(unrefined_values.items()), self.batch_size)
        batches_count = len(batches)
        translation_mgr = TranslationLocKeyFileManager(skill_files)
        tasks = [
            self.translate_and_save_batch(
                batch,
                translation_mgr=translation_mgr,
                api_semaphore=api_semaphore,
                batch_idx=batch_idx,
                total_batches=batches_count
            )
            for batch_idx, batch in enumerate(batches)
        ]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[TranslationResult] = [t for t in completed_tasks if isinstance(t, TranslationResult)]
        total_submitted_records = sum([r.total_submitted_records for r in results])
        total_refined_records = sum([r.translated_records for r in results])
        logger.info(f"Refinement {self.refinement_id} completed with {total_refined_records}/{total_submitted_records} refined keys across {len(skill_files)} files.")


if __name__ == "__main__":

    load_dotenv()
    _refinement_skill = RefinementSkill.TALENT
    _version = os.getenv("MIGRATION_TO")
    _refinement_id = f"refinement-{_refinement_skill.value}-{_version}"
    _refinement_mgr = RefinementManager(_refinement_id, RefinementSkill.TALENT, entries_threshold=20)
    asyncio.run(_refinement_mgr.refine())
