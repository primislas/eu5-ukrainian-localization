import json
import os
import re

from eukrainersalis.translators.gemini_translator import GeminiTranslator, YAMLTranslatorEncoder
from eukrainersalis.utils.file_utils import get_main_menu_localization_file, generated_country_names_file_path, \
    skill_instructions_dir, ru_localization_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language, LocFile, split_into_batches, PENDING_TRANSLATION
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml

_REF_PATTERN = re.compile(r"\$(?P<ref_key>.+)\$")


def select_all_country_tags(language: Language = Language.ENGLISH):
    country_names_file = get_main_menu_localization_file("country_names", language)
    location_names_file = get_main_menu_localization_file("location_names/location_names", language)
    formable_countries_file = get_main_menu_localization_file("formable_countries", language)

    location_names = LocFile(location_names_file).load().get_localization()
    formable_countries = LocFile(formable_countries_file).load().get_localization()
    country_names = LocFile(country_names_file).load().get_localization()

    selected_country_names = {}
    for k, v in country_names.items():
        if not k.endswith("_ADJ"):
            continue

        tag = k[:-4]
        if tag == "DUMMY":
            continue

        if tag in country_names:
            tag_value = country_names[tag]
            if ref_match := re.match(_REF_PATTERN, tag_value):
                ref_key = ref_match.group("ref_key")
                if ref_key in formable_countries:
                    selected_country_names[tag] = formable_countries[ref_key]
                elif ref_key in location_names:
                    selected_country_names[tag] = location_names[ref_key]
                elif ref_key in country_names:
                    selected_country_names[tag] = country_names[ref_key]
                else:
                    logger.warning(f"Unresolved reference key: {ref_key}")
            else:
                selected_country_names[tag] = country_names[tag]

    return selected_country_names


def prepare_generated_file(tags: dict[str, str] | None = None):
    tags = tags or select_all_country_tags()

    orig_country_names_file = ru_localization_dir / "country_names_l_russian_uk_ua_machine_translation.yml"
    orig_tags = LocFile(orig_country_names_file).load().get_localization()
    custom_case_file_path = ru_localization_dir / "EU5_customizable_localization_ru_countries_l_russian_uk_ua_machine_translation.yml"
    custom_loc = LocFile(custom_case_file_path).load().get_localization()

    combined_loc = {}
    for tag, en_val in tags.items():
        combined_loc[tag] = orig_tags.get(tag, en_val)
        if (tag_adj := f"{tag}_ADJ") in orig_tags:
            combined_loc[tag_adj] = orig_tags.get(tag_adj, PENDING_TRANSLATION)
        for suffix in ["GEN", "DAT", "ACC", "INST", "PREP"]:
            ua_suffix = f"{tag}_UA_{suffix}_CL"
            combined_loc[ua_suffix] = custom_loc.get(ua_suffix, PENDING_TRANSLATION)

    for k in custom_loc.keys():
        if not k.endswith("_UA_GEN_CL"):
            continue
        if not k in combined_loc:
            logger.warning(f"Missing translation for {k.replace('_UA_GEN_CL', '')}")

    write_eu5_localization_yaml({Language.UK_UA_MACHINE_TRANSLATION.lang_key: combined_loc}, generated_country_names_file_path)



def _get_country_names_system_instruction() -> str:
    file_path = skill_instructions_dir / "country_names.txt"
    return file_path.read_text(encoding="utf-8")


def translate_country_names():
    tags = select_all_country_tags()
    logger.info(f"Loaded {len(tags)} country names:\n{json.dumps(tags, indent=2, ensure_ascii=False)}")
    batch_size = int(os.getenv("BATCH_SIZE", 50))
    generated_file = LocFile(generated_country_names_file_path).load()
    localization = generated_file.get_localization()

    tag_pairs = [(k, v) for k, v in tags.items()]
    batches = split_into_batches(tag_pairs, batch_size)

    system_instruction_text = _get_country_names_system_instruction()
    translator = GeminiTranslator(system_instruction_text=system_instruction_text)
    encoder = YAMLTranslatorEncoder()
    total_translated = 0
    for batch in batches:
        try:
            data_input = encoder.encode(batch)
            data_output = translator.translate(data_input)
            translated_loc, errors = encoder.decode(data_output)
            for k, v in translated_loc.items():
                localization[k] = v
            generated_file.save()
            total_translated += len(batch)
            logger.debug(f"Translated {total_translated}/{len(tags)} country names")
        except RuntimeError as e:
            logger.exception(f"Error translating batch: {e}")

    untranslated_tags = []
    for tag, value in tags.items():
        if localization[tag] == PENDING_TRANSLATION:
            untranslated_tags.append(tag)

    logger.warning(f"Untranslated {len(untranslated_tags)} tags: {untranslated_tags}")
    logger.info(f"Translated {len(tags) - len(untranslated_tags)}/{len(tags)} country names:\n{json.dumps(localization, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    # prepare_generated_file()
    translate_country_names()
