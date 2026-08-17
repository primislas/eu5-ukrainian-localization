import copy

from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.translation_utils import Language
from eukrainersalis.utils.yaml_utils import write_eu5_localization_yaml, load_eu5_yaml

if __name__ == "__main__":
    # pattern = r"держав([^н]|$)"
    # text = "блабла державний принцип держав"
    # modified_text = re.sub(pattern, r"країн\1", text)
    # print(modified_text)

    _fixed_declaration = 0
    _unfixed_dangling_concept = 0
    _localization_key = Language.RUSSIAN.localization_key
    for file in list_localization_files("russian_uk_ua_machine_translation"):
        _content = load_eu5_yaml(file)
        _ucontent = {_localization_key: {}}
        for k, v in _content.get(_localization_key, {}).items():
            if "ромадянськ" in v:
            # if "'religion'" in v or "_RU_" in v or "_ru_" in k or "_RU_" in k:
            # if "ru_rank_" in v or "RU_rank_" in v or "RU_rn" in v or "ru_rank_" in k or "RU_rank_" in k or "RU_rn" in k:
                uv = v
                uk = k

                # uv = uv.replace("_ru_", "_ua_")
                # uv = uv.replace("_RU_", "_UA_")
                # uk = uk.replace("_ru_", "_ua_").replace("_RU_", "_UA_")

                # uv = uv.replace("ru_rank_", "ua_rank_")
                # uv = uv.replace("RU_rank_", "UA_rank_")
                # uv = uv.replace("RU_rn", "UA_rn")
                # uk = k
                # uk = uk.replace("ru_rank_", "ua_rank_").replace("RU_rank_", "UA_rank_").replace("RU_rn", "UA_rn")

                # u = u.replace(" ", " ")
                # u = u.replace(" ", " ")
                # uv = uv.replace("Concept('religion', 'релігія')", "Concept('religion', 'віра')")
                # uv = uv.replace("Concept('religion', 'релігію')", "Concept('religion', 'віру')")
                # uv = uv.replace("Concept('religion', 'релігії')", "Concept('religion', 'віри')")
                # uv = uv.replace("Concept('religion', 'релігією')", "Concept('religion', 'вірою')")
                #
                # uv = uv.replace("Concept('religion', 'Релігія')", "Concept('religion', 'Віра')")
                # uv = uv.replace("Concept('religion', 'Релігію')", "Concept('religion', 'Віру')")
                # uv = uv.replace("Concept('religion', 'Релігії')", "Concept('religion', 'Віри')")
                # uv = uv.replace("Concept('religion', 'Релігією')", "Concept('religion', 'Вірою')")
                #
                # uv = uv.replace(".Custom('CL_tt')", ".GetKey")

                uv = uv.replace("громадянська війна", "міжусобна війна")
                uv = uv.replace("громадянської війни", "міжусобної війни")
                uv = uv.replace("громадянській війні", "міжусобній війні")
                uv = uv.replace("громадянську війну", "міжусобну війну")
                uv = uv.replace("громадянською війною", "міжусобною війною")

                uv = uv.replace("громадянські війни", "міжусобні війни")
                uv = uv.replace("громадянських війнах", "міжусобних війнах")
                uv = uv.replace("громадянськими війнами", "міжусобними війнами")
                uv = uv.replace("громадянським війнам", "міжусобним війнам")
                uv = uv.replace("громадянських війн", "міжусобних війн")

                uv = uv.replace("Громадянська війна", "Міжусобна війна")
                uv = uv.replace("Громадянської війни", "Міжусобної війни")
                uv = uv.replace("Громадянській війні", "Міжусобній війні")
                uv = uv.replace("Громадянську війну", "Міжусобну війну")
                uv = uv.replace("Громадянською війною", "Міжусобною війною")

                uv = uv.replace("Громадянські війни", "Міжусобні війни")
                uv = uv.replace("Громадянських війнах", "Міжусобних війнах")
                uv = uv.replace("Громадянськими війнами", "Міжусобними війнами")
                uv = uv.replace("Громадянським війнам", "Міжусобним війнам")
                uv = uv.replace("Громадянських війн", "Міжусобних війн")

                _ucontent[_localization_key][uk] = uv
                if uv != v or uk != k:
                    _fixed_declaration += 1
            else:
                _ucontent[_localization_key][k] = v

            #     _content[_localization_key][k] = v
            #     _fixed_declaration += 1
            # fixed = fix_concept_declarations(v)
            # if v != fixed:
            #     print(f"{os.path.basename(file)} -> {k}:")
            #     print(f"\t--- {v}")
            #     print(f"\t+++ {fixed}")
            #     fixed_declaration += 1
            #     content[localization_key][k] = fixed
            # else:
            #     if re.match(r"\[[a-z_]+', 'CONCEPT_PLACEHOLDER'\)\|[eE]]", v):
            #         print(f"{os.path.basename(file)}: {k}: {v}")
            #         print(f"\tFound unfixed dangling concept declaration")
            #         unfixed_dangling_concept += 1
        write_eu5_localization_yaml(_ucontent, file)
    # print(f"Fixed {fixed_declaration} concept declarations, {unfixed_dangling_concept} unfixed dangling concepts")
    print(f"Fixed {_fixed_declaration} declarations")
