import re
from collections import Counter

import tinycss2


TYPOGRAPHY_PROPERTIES = {
    "font-family",
    "font-size",
    "font-weight",
    "line-height",
}

# Color-bearing properties. Shorthand properties are included because
# background, border, and outline can contain color values too.
COLOR_PROPERTIES = {
    "color",
    "background",
    "background-color",
    "border",
    "border-color",
    "border-top",
    "border-top-color",
    "border-right",
    "border-right-color",
    "border-bottom",
    "border-bottom-color",
    "border-left",
    "border-left-color",
    "outline",
    "outline-color",
    "text-decoration",
    "text-decoration-color",
    "text-shadow",
    "box-shadow",
    "column-rule",
    "column-rule-color",
    "fill",
    "stroke",
    "caret-color",
    "accent-color",
}

NAMED_COLORS = {
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige",
    "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown",
    "burlywood", "cadetblue", "chartreuse", "chocolate", "coral",
    "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
    "darkgoldenrod", "darkgray", "darkgrey", "darkgreen", "darkkhaki",
    "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred",
    "darksalmon", "darkseagreen", "darkslateblue", "darkslategray",
    "darkslategrey", "darkturquoise", "darkviolet", "deeppink", "deepskyblue",
    "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite",
    "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod",
    "gray", "grey", "green", "greenyellow", "honeydew", "hotpink",
    "indianred", "indigo", " ivory", "ivory", "khaki", "lavender",
    "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral",
    "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgrey",
    "lightgreen", "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
    "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow", "lime",
    "limegreen", "linen", "magenta", "maroon", "mediumaquamarine",
    "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen",
    "mediumslateblue", "mediumspringgreen", "mediumturquoise", "mediumvioletred",
    "midnightblue", "mintcream", "mistyrose", "moccasin", "navajowhite", "navy",
    "oldlace", "olive", "olivedrab", "orange", "orangered", " orchid", "orchid",
    "palegoldenrod", "palegreen", "paleturquoise", "palevioletred", "papayawhip",
    " peachpuff", "peachpuff", "peru", "pink", "plum", "powderblue", "purple",
    "rebeccapurple", "red", "rosybrown", "royalblue", "saddlebrown", "salmon",
    "sandybrown", "seagreen", "seashell", " sienna", "sienna", "silver",
    "skyblue", "slateblue", "slategray", "slategrey", "snow", "springgreen",
    "steelblue", "tan", "teal", "thistle", "tomato", "turquoise", "violet",
    "wheat", "white", "whitesmoke", "yellow", "yellowgreen",
    "transparent", "currentcolor",
}

COLOR_FUNCTIONS = {
    "rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab",
    "oklch", "color", "color-mix",
}

HEX_RE = re.compile(
    r"(?<![\w-])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![\w-])"
)
COLOR_FUNCTION_RE = re.compile(
    r"\b(" + "|".join(sorted(COLOR_FUNCTIONS, key=len, reverse=True)) + r")\s*\(",
    re.IGNORECASE,
)


def normalize_css_value(tokens):
    """Serialize parsed CSS tokens into a readable string."""
    return tinycss2.serialize(tokens).strip()


def split_selectors(selector_text):
    """Split selector lists on commas outside parentheses and quoted strings."""
    selectors = []
    current = []
    depth = 0
    quote = None
    escaped = False

    for char in selector_text:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\":
            current.append(char)
            escaped = True
            continue

        if quote:
            current.append(char)
            if char == quote:
                quote = None
            continue

        if char in ("'", '"'):
            quote = char
            current.append(char)
        elif char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth = max(0, depth - 1)
            current.append(char)
        elif char == "," and depth == 0:
            item = "".join(current).strip()
            if item:
                selectors.append(item)
            current = []
        else:
            current.append(char)

    item = "".join(current).strip()
    if item:
        selectors.append(item)
    return selectors


def _remove_quoted_strings(value):
    """Remove quoted strings before scanning for color names/functions."""
    return re.sub(r"""(["']).*?(?<!\\)\1""", "", value)


def extract_colors(property_name, value):
    """Extract recognizable color literals from color-bearing properties."""
    if property_name.lower() not in COLOR_PROPERTIES:
        return []

    text = _remove_quoted_strings(value)
    found = []

    found.extend(match.group(0).lower() for match in HEX_RE.finditer(text))

    # Capture balanced function calls, e.g. rgb(10, 20, 30).
    for match in COLOR_FUNCTION_RE.finditer(text):
        opening = text.find("(", match.start())
        depth = 0
        for end in range(opening, len(text)):
            if text[end] == "(":
                depth += 1
            elif text[end] == ")":
                depth -= 1
                if depth == 0:
                    found.append(text[match.start():end + 1].strip().lower())
                    break

    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    found.extend(word for word in words if word in NAMED_COLORS)

    # Preserve first-seen order while removing duplicates from this value.
    return list(dict.fromkeys(found))


def parse_css(css_text, filename="uploaded.css"):
    """
    Parse CSS into JSON-serializable data.

    Counts qualified rules (including nested rules), individual comma-separated
    selectors, and declaration entries. Repeated properties are preserved.
    """
    if not isinstance(css_text, str):
        raise TypeError("CSS input must be a string.")

    result = {
        "filename": filename,
        "statistics": {},
        "rules": [],
        "colors": [],
        "typography": [],
        "parse_warnings": [],
    }

    all_selectors = []
    all_properties = []
    all_colors = []

    def process_rule_list(parsed_rules, context=None):
        for rule in parsed_rules:
            if rule.type == "error":
                result["parse_warnings"].append({
                    "message": rule.message,
                    "line": getattr(rule, "source_line", None),
                    "column": getattr(rule, "source_column", None),
                    "context": context,
                })
                continue

            if rule.type == "at-rule":
                at_name = f"@{rule.at_keyword}"
                prelude = normalize_css_value(rule.prelude)
                if prelude:
                    at_name = f"{at_name} {prelude}"

                nested_context = f"{context} > {at_name}" if context else at_name

                if rule.content is not None:
                    nested_rules = tinycss2.parse_rule_list(
                        rule.content,
                        skip_comments=True,
                        skip_whitespace=True,
                    )
                    process_rule_list(nested_rules, nested_context)
                continue

            if rule.type != "qualified-rule":
                continue

            selector_text = normalize_css_value(rule.prelude)
            selectors = split_selectors(selector_text)

            declaration_nodes = tinycss2.parse_declaration_list(
                rule.content,
                skip_comments=True,
                skip_whitespace=True,
            )

            declarations = []
            for node in declaration_nodes:
                if node.type == "error":
                    result["parse_warnings"].append({
                        "message": node.message,
                        "line": getattr(node, "source_line", None),
                        "column": getattr(node, "source_column", None),
                        "context": context,
                    })
                    continue

                if node.type != "declaration":
                    continue

                property_name = node.name.lower()
                value = normalize_css_value(node.value)
                if node.important:
                    value += " !important"

                declarations.append({
                    "property": property_name,
                    "value": value,
                    "important": bool(node.important),
                })
                all_properties.append(property_name)

                for color in extract_colors(property_name, value):
                    all_colors.append(color)

                if property_name in TYPOGRAPHY_PROPERTIES:
                    for selector in selectors:
                        result["typography"].append({
                            "selector": selector,
                            "property": property_name,
                            "value": value,
                            "context": context,
                        })

            result["rules"].append({
                "selector": selector_text,
                "selectors": selectors,
                "declarations": declarations,
                "context": context,
            })
            all_selectors.extend(selectors)

    parsed_rules = tinycss2.parse_stylesheet(
        css_text,
        skip_comments=True,
        skip_whitespace=True,
    )
    process_rule_list(parsed_rules)

    result["colors"] = sorted(set(all_colors))
    result["statistics"] = {
        "rules": len(result["rules"]),
        "selectors": len(all_selectors),
        "declarations": sum(len(rule["declarations"]) for rule in result["rules"]),
        "unique_colors": len(set(all_colors)),
        "unique_properties": len(set(all_properties)),
    }

    return result
