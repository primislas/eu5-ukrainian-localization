import asyncio

from eukrainersalis.translators.gemini_translator import GeminiTranslator, YAMLTranslatorEncoder
from eukrainersalis.utils.file_utils import project_mod_dir, ru_localization_dir, en_localization_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.refinement_utils import get_skill_file
from eukrainersalis.utils.translation_utils import Language, LocFile, split_into_batches


def get_expected_suffixes() -> list[str]:
    expected_suffixes = [f"_UA_{suffix}_LOC" for suffix in ["GEN", "DAT", "ACC", "INST", "PREP"]]
    expected_suffixes.insert(0, "_ADJ")
    return expected_suffixes


def get_geography_translation_instructions():
    return get_skill_file("location_names").read_text()


def get_location_name_files():
    """ Get Localization files used in this script.

    input_file, output_file, output_cases_file = get_location_name_files()
    """


    input_location_names_file = en_localization_dir / "location_names" / "location_names_l_english.yml"
    output_location_names_file = ru_localization_dir / "location_names" / "location_names_l_russian_uk_ua_machine_translation.yml"
    output_location_name_cases_file = project_mod_dir / "main_menu" / "localization" / "russian" / "assets" / "location_names" / "location_name_cases_l_russian_uk_ua_machine_translation.yml"

    input_file = LocFile(input_location_names_file)
    output_file = LocFile(output_location_names_file)
    output_cases_file = LocFile(output_location_name_cases_file, language = Language.RUSSIAN)
    return input_file, output_file, output_cases_file



async def translate_location_names():
    input_file, output_file, output_cases_file = get_location_name_files()
    input_loc = input_file.load().get_localization()
    output_file.load()
    output_cases_file.load()
    untranslated_keys = validate_translations()

    # values_to_translate = [(k, v) for k, v in input_loc.items()]
    values_to_translate = [(k, input_loc.get(k)) for k in untranslated_keys]
    logger.info(f"Prepared {len(values_to_translate)} keys for translation")

    batches = split_into_batches(values_to_translate, 100)
    system_instruction_text = get_geography_translation_instructions()
    translator = GeminiTranslator(system_instruction_text=system_instruction_text)
    encoder = YAMLTranslatorEncoder()
    batch_idx = 0
    all_translations = 0
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
                if loc_key.endswith("_ADJ") or loc_key.endswith("_LOC"):
                    output_cases_file.set_localization_value(loc_key, value)
                else:
                    output_file.set_localization_value(loc_key, value)
            output_file.save()
            output_cases_file.save()
            all_translations += len(translated_values)
            logger.info(f"Translated {batch_idx}/{len(batches)} batches, {all_translations} loc keys")
        except Exception as e:
            logger.exception(f"Batch {batch_idx}/{len(batches)} failed: {e}")

    logger.info(f"Translated {len(input_loc)} values")


def validate_translations():
    input_file, output_file, output_cases_file = get_location_name_files()
    input_loc = input_file.load().get_localization()
    output_loc = output_file.load().get_localization()
    output_cases_loc = output_cases_file.load().get_localization()

    expected_suffixes = get_expected_suffixes()
    untranslated_keys = set()
    ungenerated_cases = set()
    for loc_key in input_loc.keys():
        if loc_key.endswith("_ADJ"):
            continue

        if not loc_key in output_loc:
            untranslated_keys.add(loc_key)
        if not all((loc_key + suffix in output_cases_loc.keys()) for suffix in expected_suffixes):
            ungenerated_cases.add(loc_key)

    if untranslated_keys:
        logger.warning(f"Missing translations for {len(untranslated_keys)} keys: {untranslated_keys}")
    if ungenerated_cases:
        logger.warning(f"Missing case translations for {len(ungenerated_cases)} keys: {ungenerated_cases}")

    return list(untranslated_keys | ungenerated_cases)


def reorder_translated_files():
    input_file, output_file, output_cases_file = get_location_name_files()
    input_loc = input_file.load().get_localization()
    output_file.load()
    output_cases_file.load()

    reordered_names: dict[str, str] = {}
    reordered_cases: dict[str, str] = {}
    expected_suffixes = get_expected_suffixes()
    for k, v in input_loc.items():
        if k.endswith("_ADJ"):
            continue

        name_val = output_file.get_localization_value(k)
        if name_val is None:
            logger.warning(f"Missing name translation for {k}")
        reordered_names[k] = name_val or v

        if output_cases_file is not None:
            for suffix in expected_suffixes:
                case_key = k + suffix
                existing_case_value = output_cases_file.get_localization_value(case_key)
                if existing_case_value is not None:
                    reordered_cases[case_key] = existing_case_value
                else:
                    logger.warning(f"Missing case translation for {case_key}")

    output_file.set_localization(reordered_names)
    output_file.save()
    output_cases_file.set_localization(reordered_cases)
    output_cases_file.save()


if __name__ == "__main__":
    # asyncio.run(translate_location_names())
    reorder_translated_files()
    validate_translations()
