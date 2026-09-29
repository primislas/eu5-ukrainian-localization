import os
import shutil
from pathlib import Path

from eukrainersalis.utils.file_utils import list_localization_files, mod_compatibility_dir
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language


def create_mod_uk_ua_files(mod: str):
    source_dir_path = Path(os.path.join(str(mod_compatibility_dir), mod)).resolve()
    source_mod_files = list_localization_files(Language.ENGLISH, source_dir=source_dir_path)
    for file in source_mod_files:
        base, name = os.path.split(file)
        compat_name = name.replace(Language.ENGLISH.value, Language.UK_UA_MACHINE_TRANSLATION.value)
        compat_path = os.path.join(base, compat_name)
        shutil.copy(file, compat_path)
        logger.info(f"Created {name} -> {compat_name}")
    logger.info(f"Created {len(source_mod_files)} compat template files")


if __name__ == "__main__":
    _mod = "ruthenia_and_steppe_fix"
    create_mod_uk_ua_files(_mod)
