import asyncio
from pathlib import Path

from eukrainersalis.translators.gemini_translator import GeminiTranslator, YAMLTranslatorEncoder
from eukrainersalis.utils.file_utils import translation_dir, get_key_file_lookup, project_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.refinement_utils import get_skill_file
from eukrainersalis.utils.translation_utils import Language, LocFile, split_into_batches
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml


def _get_jap_file_values(file_path: str) -> list[str]:
    txt = (project_dir / file_path).read_text(encoding="utf-8")
    vals: set[str] = set()
    for line in txt.splitlines():
        l = line.strip().replace("\t", " ").replace("{", "").replace("}", "").replace("=", "")
        if not l:
            continue
        for v in l.split(" "):
            v = v.strip()
            if v:
                vals.add(v)

    return list(sorted(vals))


def get_name_keys() -> list[str]:
    return _get_jap_file_values("japanese_names.txt")


def get_last_name_keys() -> list[str]:
    return _get_jap_file_values("japanese_last_names.txt")


def get_geography_keys() -> list[str]:
    return _get_jap_file_values("japanese_geography.txt")


def get_system_instruction_text() -> str:
    return get_skill_file("japanese_kovalenko_system").read_text()


async def translate_character_names():
    name_keys = get_name_keys()
    last_name_keys = get_last_name_keys()
    geography_keys = get_geography_keys()
    key_lookup = get_key_file_lookup()
    all_input_keys = name_keys + last_name_keys + geography_keys
    logger.info(f"Received {len(all_input_keys)} Japanese loc keys")

    files_to_load = set()
    all_keys = []
    for loc_key in all_input_keys:
        if not loc_key in key_lookup:
            logger.warning(f"Key {loc_key} not found in key lookup file")
        else:
            all_keys.append(loc_key)
            files_to_load.add(key_lookup[loc_key])
    logger.info(f"Identified {len(all_keys)} existing Japanese loc keys")

    source_localizations = {}
    target_localizations = {}
    for file_path in files_to_load:
        source_file_path = translation_dir / f"{file_path}{Language.ENGLISH.file_suffix}.yml".replace("/russian/", "/english/")
        source_localizations[file_path] = LocFile(source_file_path).load()
        target_file_path = translation_dir / f"{file_path}{Language.UK_UA_MACHINE_TRANSLATION.file_suffix}.yml"
        target_localizations[file_path] = LocFile(target_file_path).load()
    logger.info(f"Loaded {len(source_localizations)} source localizations and {len(target_localizations)} target localizations")

    def get_value(loc_key: str) -> str:
        return source_localizations[key_lookup[loc_key]].get_localization_value(loc_key)
    def update_value(loc_key: str, value: str):
        target_localizations[key_lookup[loc_key]].set_localization_value(loc_key, value)

    values_to_translate = [(k, get_value(k)) for k in all_keys]
    write_eu5_localization_yaml({t[0]: t[1] for t in values_to_translate}, project_dir / "japanese_english.yml")
    logger.info(f"Prepared {len(values_to_translate)} keys for translation")

    batches = split_into_batches(values_to_translate, 100)
    system_instruction_text = get_system_instruction_text()
    translator = GeminiTranslator(system_instruction_text=system_instruction_text)
    encoder = YAMLTranslatorEncoder()
    batch_idx = 0
    all_translations = {}
    for batch in batches:
        try:
            batch_idx += 1
            logger.info(f"Translating batch {batch_idx}/{len(batches)}...")
            text = encoder.encode(batch)
            translated_text = await translator.translate_batch_async(text)
            translated_values, errors = encoder.decode(translated_text)
            if errors:
                logger.warning(f"Batch {batch_idx}/{len(batches)} encountered {len(errors)} errors")
            for loc_key, value in translated_values.items():
                update_value(loc_key, value)
                all_translations[loc_key] = value
            write_eu5_localization_yaml(all_translations, project_dir / "japanese_kovalenko.yml")
            logger.info(f"Translated {batch_idx}/{len(batches)} batches, {len(all_translations)} loc keys")
        except Exception as e:
            logger.exception(f"Batch {batch_idx}/{len(batches)} failed: {e}")

    for loc_file in target_localizations.values():
        loc_file.save()

    logger.info(f"Translated {len(all_keys)} values in {len(target_localizations)} files")


if __name__ == "__main__":
    asyncio.run(translate_character_names())
