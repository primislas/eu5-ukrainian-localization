import re
from pathlib import Path

from eukrainersalis.utils.ending_adaptation import ending_configs
from eukrainersalis.utils.file_utils import custom_localization_translation_dir_path, custom_localization_mod_dir_path
from eukrainersalis.utils.log_utils import logger


def _read_declarations(fpath: Path) -> dict[str, list[str]]:
    declaration_start_regex = r"(?P<identifier>[a-zA-Z_]+)\s+=\s+{\s*"
    declaration_start_pattern = re.compile(declaration_start_regex)
    declaration_end_regex = r"}\s*"
    declaration_end_pattern = re.compile(declaration_end_regex)

    declarations = {}
    current_identifier = None
    line_number = -1
    for line in fpath.read_text(encoding="utf-8-sig").splitlines():
        line_number += 1
        if match := declaration_start_pattern.match(line):
            current_identifier = match.group("identifier")
            if current_identifier not in declarations:
                declarations[current_identifier] = [line]
            else:
                logger.warning(f"Duplicate declaration for identifier: {current_identifier}")
                declarations[current_identifier].append(line)
            continue

        if declaration_end_pattern.match(line):
            if current_identifier is not None:
                declarations[current_identifier].append(line)
                current_identifier = None
            else:
                logger.warning(f"Unexpected end of declaration without start at line {line_number}: {line}")
            continue

        if current_identifier:
            declarations[current_identifier].append(line)
        elif line.strip() != "":
            logger.warning(f"Unexpected line outside of declarations at line {line_number}: {line}")

    logger.info(f"Found {len(declarations)} declarations")
    for dec in declarations.keys():
        print(dec)
    return declarations


def adapt_ru_to_ua(l: str) -> str:
    res = l.replace("_ru_", "_ua_").replace("_RU_", "_UA_").replace("_ru ", "_ua ").replace("_RU ", "_UA ")
    if res.endswith("_ru"):
        return res[:-3] + "_ua"
    return res


def write_lines_to_fpointer(fp, lines: list[str]):
    for l in lines:
        fp.write(l)
        fp.write("\n")


def write_lines_to_file(fpath: Path, lines: list[str]):
    with fpath.open("w", encoding="utf-8-sig") as f:
        write_lines_to_fpointer(f, lines)


def adapt_ru_custom_suffix():
    custom_suffix_file_path = custom_localization_translation_dir_path / "ru_EU5_custom_suffix.txt"
    declarations = _read_declarations(custom_suffix_file_path)

    output_file_path = custom_localization_mod_dir_path / "380_ua_custom_suffix.txt"
    with output_file_path.open("w", encoding="utf-8-sig") as f:
        for dec, lines in declarations.items():
            if dec.startswith("endlong") or dec.startswith("endrank"):
                continue

            migrated_lines = [adapt_ru_to_ua(l) for l in lines]
            write_lines_to_fpointer(f, migrated_lines)

        for prefix in ["endlong", "endrank"]:
            for ec in ending_configs:
                ending = ec["to"]
                if ending.startswith("pre"):
                    continue
                tag = f"{prefix}_{ending}"
                lines = [
                    f"{tag} = {{",
                    "	log_loc_errors = no",
                    "	parent = country_ua_flavor",
                    f"	suffix = \"_{tag}\"",
                    "	if_invalid_loc = return_empty",
                    "}",
                ]
                write_lines_to_fpointer(f, lines)


def adapt_ru_custom_loc():
    custom_ending_file_path = custom_localization_translation_dir_path / "ru_EU5_custom_loc.txt"
    declarations = _read_declarations(custom_ending_file_path)

    key_overwrites = []
    for k, lines in declarations.items():
        if k.startswith("end_") or k.startswith("predlog_") or k == "ety_vvo":
            # separate processing
            continue

        if k.startswith("LR_"):
            key_overwrites.append(k)
            continue

        migrated_lines = [adapt_ru_to_ua(l) for l in lines]
        fpath = custom_localization_mod_dir_path / f"380_ua_custom_loc_{k}.txt"
        write_lines_to_file(fpath, migrated_lines)

    for ec in ending_configs:
        to = ec["to"]
        template = declarations["end_fem"] if not to.startswith("pre") else declarations["predlog_kko"]
        migrated_lines = [adapt_ru_to_ua(l).replace("_fem", f"_{to}").replace("predlog_kko", to) for l in template]
        fname = f"ua_custom_loc_end_{to}.txt" if not to.startswith("pre") else f"ua_custom_loc_{to}.txt"
        fpath = custom_localization_mod_dir_path / fname
        write_lines_to_file(fpath, migrated_lines)

    if key_overwrites:
        fpath = custom_localization_mod_dir_path / f"380_ua_custom_loc.txt"
        with fpath.open("w", encoding="utf-8-sig") as cl_overwrite_f:
            for k in key_overwrites:
                migrated_lines = [adapt_ru_to_ua(l) for l in declarations[k]]
                write_lines_to_fpointer(cl_overwrite_f, migrated_lines)


def adapt_ru_custom_culture():
    custom_culture_file_path = custom_localization_translation_dir_path / "ru_EU5_custom_culture.txt"
    declarations = _read_declarations(custom_culture_file_path)
    output_file_path = custom_localization_mod_dir_path / "380_ua_custom_culture.txt"
    with output_file_path.open("w", encoding="utf-8-sig") as f:
        for dec, lines in declarations.items():
            migrated_lines = [adapt_ru_to_ua(l) for l in lines]
            write_lines_to_fpointer(f, migrated_lines)


if __name__ == "__main__":
    adapt_ru_custom_loc()
    adapt_ru_custom_suffix()
    adapt_ru_custom_culture()
