import os
import re
from typing import Tuple

from eukrainersalis.utils.file_utils import list_localization_files
from eukrainersalis.utils.log_utils import logger
from eukrainersalis.utils.translation_utils import Language, LocFile

MATCHING_CLOSED_BRACKETS = {
    '(': ')',
    '[': ']',
    '{': '}',
    # '«': '»',
    '\'': '\''
}

SCOPE_REGEX = r"\[(?P<call>[^\|\]]+)(\|(?P<modifiers>[^\]]))?\]"
CONCEPT_REGEX = r"Concept\('(?P<game_concept>[a-zA-Z0-9_]+)',"
CSTRING_REGEX = r"Select_CString\((?P<call>[^,]+),.+"
CONCEPT_TOOLTIP_REGEX = r"#TOOLTIP:GAME_CONCEPT,(?P<tooltip_key>[^\s]+)\s+"
TOOLTIP_REGEX = r"#TOOLTIP:(?P<tooltip_type>[^,]+),(?P<tooltip_key>[^,]+),"
TOOLTIP_ID_REGEX = r"\$(?P<tooltip_id>[a-zA-Z0-9_]+?)(_tt)?\$"
ROOT_ESTATE_NAME_REGEX = r"ROOT\.GetCountry\.GetGovernment\.GetEstateName(?P<has_tooltip>WithNoTooltip)?\('(?P<estate_name>[a-z_]+)'\)"



def validate_brackets_in_text(text: str) -> bool:
    stack = []
    # TODO: how to properly iterate with index
    for i, c in enumerate(text):
        if c == "'":
            if not stack:
                continue

            if stack[-1] == "'":
                stack.pop()
            else:
                stack.append(c)
            continue

        if c in MATCHING_CLOSED_BRACKETS:
            stack.append(c)
        elif c in MATCHING_CLOSED_BRACKETS.values():
            expected_closing_bracket = MATCHING_CLOSED_BRACKETS[stack.pop()] if stack else None
            if expected_closing_bracket != c:
                if expected_closing_bracket:
                    logger.warning(f"Unmatched closing bracket at index {i}: expected {expected_closing_bracket}, got {c}; {text[:i]}")
                else:
                    logger.warning(f"Unexpected closing bracket at index {i}: {c}; {text[:i]}")
                return False
    return not stack


def validate_brackets():
    error_count = 0
    for file_path in list_localization_files(Language.UK_UA_MACHINE_TRANSLATION):
        loc_file = LocFile(file_path).load()
        for loc_key, loc_value in loc_file.get_localization().items():
            if not validate_brackets_in_text(loc_value):
                logger.warning(f"Unmatched brackets at key {loc_key} ({loc_file.name()})")
                error_count += 1
    logger.info(f"Validation complete. Found {error_count} bracket errors.")

    return error_count == 0


def normalize_extracted_call(call: str, modifiers: str | None = None) -> str:
    call = call.replace("','", "', '")
    # TODO: temporarily suppressing to reduce amount of noise
    call = call.replace("_with_icon", "")

    if "ShowReligionGroup" in call:
        call = call.replace("ShowReligionGroupName", "ShowReligionGroupNameOrAdjective")
        return call.replace("ShowReligionGroupAdjective", "ShowReligionGroupNameOrAdjective")

    if "ShowReligion" in call:
        call = call.replace("ShowReligionName", "ShowReligionNameOrAdjective")
        return call.replace("ShowReligionAdjective", "ShowReligionNameOrAdjective")

    if "LocationName(" in call:
        return call.replace("LocationName(", "LocationNameWithNoTooltip(")

    if "StatusNamePlural" in call:
        return call.replace("StatusNamePlural", "StatusName")

    # TODO: temporarily suppressing to reduce amount of noise
    if "GetSituationByKey" in call:
         return call.replace("GetSituationByKey", "ShowSituationName").replace(".GetNameWithNoTooltip", "").replace(".GetName", "")
    if "GetDynasty" in call and ".GetName" in call:
         return call.replace("GetDynasty", "ShowDynastyName").replace(".GetNameWithNoTooltip", "").replace(".GetName", "")
    if "GetUniqueInternationalOrganization" in call:
        return call.replace("GetUniqueInternationalOrganization", "GetInternationalOrganization").replace(".GetNameWithNoTooltip", "").replace(".GetName", "")

    if estate_name_match := re.search(ROOT_ESTATE_NAME_REGEX, call):
        return f"ShowEstateTypeName('{estate_name_match.group('estate_name')}')"

    if "." in call:
        return call.split(".")[0]

    return call


def extract_function_calls(text: str) -> set[str]:
    calls = set()

    if "TOOLTIP" in text:
        for tooltip_match in re.finditer(CONCEPT_TOOLTIP_REGEX, text):
            tooltip_key = tooltip_match.group("tooltip_key")
            calls.add(tooltip_key)

        for tooltip_match in re.finditer(TOOLTIP_REGEX, text):
            tooltip_type = tooltip_match.group("tooltip_type")
            tooltip_key = tooltip_match.group("tooltip_key")
            if tooltip_type == "GAME_CONCEPT":
                continue
            if tooltip_type == "COUNTRY":
                # Expectig a form like `[CountryScope.GetID]`
                tooltip_call = tooltip_key.replace(".GetID]", "")[1:]
            elif tooltip_type == "LOCATIONRANK":
                if ".Custom" in tooltip_key:
                    tooltip_call = ".".join(tooltip_key.split(".")[:-1])[1:]
                else:
                    tooltip_call = f"ShowLocationRankName('{tooltip_key}')"
            else:
                # tooltip_call = "Get" + "".join([word.capitalize() for word in tooltip_type.split("_")])
                normalized_tooltip_key = tooltip_key
                if tooltip_id_match := re.match(TOOLTIP_ID_REGEX, tooltip_key):
                    normalized_tooltip_key = tooltip_id_match.group("tooltip_id")

                # if tooltip_type == "SITUATION":
                #     tooltip_func = "GetSituationByKey"
                if tooltip_type == "INTERNATIONAL_ORGANIZATION":
                    tooltip_func = "GetInternationalOrganization"
                elif tooltip_type == "INTERNATIONAL_ORGANIZATION_TYPE":
                    tooltip_func = "GetInternationalOrganizationType"
                elif tooltip_type == "DISASTER_TYPE":
                    tooltip_func = "ShowDisasterName"
                elif tooltip_type == "GOVTYPE":
                    tooltip_func = "ShowGovernmentTypeName"
                elif tooltip_type == "ADVANCE_DEFINITION":
                    tooltip_func = "ShowAdvanceName"
                elif tooltip_type == "STATIC_MODIFIER":
                    tooltip_func = "ShowModifier"
                elif tooltip_type == "SCRIPTED_RELATION_TYPE":
                    tooltip_func = "ShowRelationTypeName"
                elif tooltip_type == "SCRIPTED_PEACE_TREATY":
                    tooltip_func = "ShowPeaceTreatyTypeName"
                elif tooltip_type == "ARTIST":
                    tooltip_func = "ShowArtistTypeName"
                elif tooltip_type == "PARLIAMENT_ISSUE":
                    tooltip_func = "ShowParliamentIssueTypeName"
                # elif tooltip_type == "ESTATE_TYPE":
                #     tooltip_func = "ShowEstateTypeName"
                else:
                    tooltip_func = "Show" + "".join([word.capitalize() for word in tooltip_type.split("_")]) + "Name"
                    tooltip_func = tooltip_func.replace("group", "Group").replace("rank", "Rank").replace("type", "Type").replace("category", "Category")
                    tooltip_func = tooltip_func.replace("UnitType", "UnitDefinition")
                    tooltip_func = tooltip_func.replace("Heirselection", "HeirSelection")

                tooltip_call = f"{tooltip_func}('{normalized_tooltip_key}')"

            calls.add(tooltip_call)

    modifiers = None
    for match in re.finditer(SCOPE_REGEX, text):
        group_dict = match.groupdict()
        call = group_dict["call"]
        modifiers = group_dict["modifiers"]

        if "Select_CString" in call and ".IsFemale" in call:
            if cstring_match := re.match(CSTRING_REGEX, call):
                call = cstring_match.group("call")

        if "Concept" in call:
            if concept_match := re.match(CONCEPT_REGEX, call):
                call = concept_match.group("game_concept")

        if modifiers:
            modifiers = modifiers.replace("u", "").replace("U", "").replace("l", "").replace("L", "")

        calls.add(call)

    normalized_calls = {normalize_extracted_call(c, modifiers) for c in calls}
    # TODO: should fix and properly match "ShowSocietalValueName('mysticism_vs_jurisprudence') vs ShowSocietyDirectionName('jurisprudence')
    normalized_calls = {c for c in normalized_calls if not c.startswith("ShowSociet")}
    # TODO: investigate links separately
    normalized_calls = {c for c in normalized_calls if not c.startswith("Link")}
    # TODO: Select_CString is hard to parse and adds a lot of noise
    normalized_calls = {c for c in normalized_calls if not c.startswith("Select_CString")}
    return normalized_calls


def smart_compare_calls(left_calls: set[str], right_calls: set[str]) -> Tuple[set[str], set[str]]:
    cleaned_up_left = set(left_calls)
    cleaned_up_right = set(right_calls)

    for cl in left_calls:
        for cr in right_calls:
            if cl == cr:
                cleaned_up_left.discard(cl)
                cleaned_up_right.discard(cr)
                continue

            # WithNoTooltip is often replaced by direct text or a tooltip
            if "WithNoTooltip" in cl:
                wtt = cl.replace("WithNoTooltip", "")
                cleaned_up_left.discard(cl)
                if wtt in cleaned_up_right:
                    cleaned_up_right.discard(wtt)
                continue

            if "WithNoTooltip" in cr:
                wtt = cr.replace("WithNoTooltip", "")
                # TODO: is there a way to safe remove from a set without error?
                cleaned_up_right.discard(cr)
                if wtt in cleaned_up_left:
                    cleaned_up_left.remove(wtt)
                continue

            # plural declarations are a common source of differences
            shorter, longer = sorted([cl, cr], key=len)
            if longer == shorter + "s" or longer == shorter + "es" or longer == shorter + "ing" or longer == shorter + "_plural" or longer.endswith("ies") and shorter.endswith("y"):
                cleaned_up_left.discard(cl)
                cleaned_up_right.discard(cr)
                continue

    if len(cleaned_up_left) + len(cleaned_up_right) == 1:
        if "ROOT" in cleaned_up_left or "ROOT" in cleaned_up_right:
            return set(), set()

    return cleaned_up_left, cleaned_up_right


def match_function_calls(loc_key: str, left: str, right: str) -> bool:
    if loc_key == "WE_PERFORM_assert_patronato_real_ACTION_EFFECTS":
        pass

    left_calls = extract_function_calls(left)
    right_calls = extract_function_calls(right)

    if left_calls != right_calls:
        ua_diff = left_calls.difference(right_calls)
        en_diff = right_calls.difference(left_calls)

        ua_diff, en_diff = smart_compare_calls(ua_diff, en_diff)

        if ua_diff:
            print(f"Unmatched function calls at key {loc_key}:")
            if ua_diff:
                print(f"\tdiff on UA side: {ua_diff}")
            if en_diff:
                print(f"\tdiff on EN side: {en_diff}")
            return False

        return True

    return True


def validate_function_calls():
    error_limit = 1000_000
    error_count = 0
    for file_path in list_localization_files(Language.UK_UA_MACHINE_TRANSLATION):
        if error_count >= error_limit:
            break

        ua_loc_file = LocFile(file_path).load()
        ua_loc = ua_loc_file.get_localization()

        en_loc_file_path = file_path.replace("/russian/", "/english/").replace(Language.UK_UA_MACHINE_TRANSLATION.file_suffix, Language.ENGLISH.file_suffix)
        if not os.path.exists(en_loc_file_path):
            continue

        en_loc_file = LocFile(en_loc_file_path).load()
        en_loc = en_loc_file.get_localization()

        for loc_key, loc_value in ua_loc.items():
            if error_count >= error_limit:
                break

            if not match_function_calls(loc_key, ua_loc[loc_key], en_loc[loc_key]):
                error_count += 1

    logger.info(f"Validation complete. Found {error_count} function call errors.")

    return error_count == 0


if __name__ == "__main__":
    # validate_brackets()
    validate_function_calls()
