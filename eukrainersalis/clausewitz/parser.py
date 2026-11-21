import json
import re


def parse_clausewitz_to_dict(text):
    # Remove comments and tokenize
    text = re.sub(r'#.*', '', text)
    tokens = re.findall(r'\{|\}|=|"[^"]*"|[^\s\{\}=]+', text)

    def cast_value(val):
        val = val.strip('"')
        if val == 'yes':
            return True
        if val == 'no':
            return False
        return val

    def parse_block(index):
        pairs = []
        standalone = []

        while index < len(tokens):
            token = tokens[index]

            if token == '}':
                return finalize(pairs, standalone), index + 1

            # Key-value pair
            if index + 1 < len(tokens) and tokens[index + 1] == '=':
                key = token.strip('"')
                val_token = tokens[index + 2]

                if val_token == '{':
                    val, index = parse_block(index + 3)
                else:
                    val = cast_value(val_token)
                    index += 3
                pairs.append((key, val))
            else:
                # Standalone list item
                standalone.append(cast_value(token))
                index += 1

        return finalize(pairs, standalone), index

    def finalize(pairs, standalone):
        # Pure list block (e.g., sodra_osterbotten_province)
        if not pairs:
            return standalone

        # Build dictionary for key-value pairs
        result = {}
        for k, v in pairs:
            if k in result:
                if not isinstance(result[k], list):
                    result[k] = [result[k]]
                result[k].append(v)
            else:
                result[k] = v

        # If the block also had standalone items, store them under "_values"
        if standalone:
            result['_values'] = standalone

        return result

    parsed, _ = parse_block(0)
    return parsed


# Example usage:
raw_data = """
finland_area = { not_eligible_for_dynamic_country_name = yes
    sodra_osterbotten_province = { korsholm koppo pedersore storkyro karleby kaustby lappo vora }
    finland_province = { abo nystad poytis sauvo }
    nyland_province = { helsinge ekenas sjundea porvoo liljendal }
    vederlax valkeasaari kyyrola beryozovskoye heinjoki jaskis pyhajarvi puruvesi saima 
}
"""

data_dict = parse_clausewitz_to_dict(raw_data)
print(json.dumps(data_dict, indent=2))
