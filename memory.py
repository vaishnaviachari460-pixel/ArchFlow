import re


def extract_revisions(text):
    return sorted({
        int(n)
        for n in re.findall(
            r"\brev(?:ision)?\s*[-#]?\s*(\d+)\b",
            str(text),
            re.I
        )
    })


def extract_materials(text):
    return sorted(set(
        re.findall(
            r"\b[A-Z]{1,5}-\d{2,5}\b",
            str(text)
        )
    ))


def _has_replacement_language(text):
    return bool(re.search(
        r"\b(?:replace|replacing|replacement|recommend(?:ed|s)?|substitut(?:e|ed|ion)|changed?|change(?:d)?\s+to|switch(?:ed)?\s+to)\b",
        str(text or ""),
        re.I
    ))


def _unavailable_materials(text):
    text = str(text or "")
    unavailable_pattern = re.compile(
        r"([A-Z]{1,5}-\d{2,5}).{0,80}?"
        r"(?:unavailable|out of stock|not available|discontinued)",
        re.I
    )
    reverse_pattern = re.compile(
        r"(?:unavailable|out of stock|not available|discontinued).{0,80}?"
        r"([A-Z]{1,5}-\d{2,5})",
        re.I
    )
    return set(
        match.upper()
        for match in (
            unavailable_pattern.findall(text)
            + reverse_pattern.findall(text)
        )
    )


def detect_changes(current_text, previous_communications):
    """
    Compare the current analysis with the immediately previous project
    communication.

    Only meaningful state changes are reported. Merely mentioning a new
    material in an otherwise unrelated conversation is not treated as a
    project change.
    """
    if not previous_communications:
        return {"changes": []}

    current_text = str(current_text or "")
    previous_text = str(previous_communications[0] or "")
    changes = []

    # ---------------------------------------------------------
    # Drawing revision change
    # ---------------------------------------------------------
    current_revisions = extract_revisions(current_text)
    previous_revisions = extract_revisions(previous_text)

    if current_revisions and previous_revisions:
        old = max(previous_revisions)
        new = max(current_revisions)

        if new != old:
            changes.append({
                "type": "REVISION CHANGE",
                "title": "Drawing revision changed",
                "previous": f"Rev {old}",
                "current": f"Rev {new}",
                "impact": (
                    "A different drawing revision has appeared in the "
                    "latest project communication."
                ),
                "action": (
                    f"Verify that all stakeholders are using Rev {new}."
                ),
            })

    # ---------------------------------------------------------
    # Material selection change
    # ---------------------------------------------------------
    current_materials = set(extract_materials(current_text))
    previous_materials = set(extract_materials(previous_text))

    added = current_materials - previous_materials
    removed = previous_materials - current_materials

    # A material difference alone is not enough. Require language that
    # indicates an actual replacement/change. The current conversation may
    # contain both the original and replacement material, so detect explicit
    # replacement wording even when the previous analysis had no material.
    material_change = None

    explicit_pair_patterns = [
        r"(?:originally|specified|approved)\s+(?:as|for)\s+([A-Z]{1,5}-\d{2,5}).{0,120}?(?:replace|replac(?:e|ing)|replacement).{0,80}?(?:with|by)\s+([A-Z]{1,5}-\d{2,5})",
        r"([A-Z]{1,5}-\d{2,5}).{0,120}?(?:replace|replac(?:e|ing)|replacement).{0,80}?(?:with|by)\s+([A-Z]{1,5}-\d{2,5})",
    ]

    for pattern in explicit_pair_patterns:
        match = re.search(pattern, current_text, re.I | re.S)
        if match:
            material_change = (match.group(1).upper(), match.group(2).upper())
            break

    if material_change:
        previous_value, current_value = material_change
        changes.append({
            "type": "MATERIAL CHANGE",
            "title": "Material selection changed",
            "previous": previous_value,
            "current": current_value,
            "impact": (
                "The material selection changed in the latest project "
                "communication."
            ),
            "action": (
                "Confirm the replacement material with the client and "
                "project team."
            ),
        })
    elif added and _has_replacement_language(current_text):
        previous_value = ", ".join(sorted(removed)) or ", ".join(sorted(previous_materials))
        current_value = ", ".join(sorted(added))
        if previous_value and current_value:
            changes.append({
                "type": "MATERIAL CHANGE",
                "title": "Material selection changed",
                "previous": previous_value,
                "current": current_value,
                "impact": (
                    "The material selection appears to have changed in the "
                    "latest communication."
                ),
                "action": (
                    "Confirm the replacement material with the client and "
                    "project team."
                ),
            })

    # ---------------------------------------------------------
    # Material availability change
    # ---------------------------------------------------------
    current_unavailable = _unavailable_materials(current_text)
    previous_materials_upper = {m.upper() for m in previous_materials}

    newly_unavailable = (
        current_unavailable & previous_materials_upper
    )

    if newly_unavailable:
        material_list = ", ".join(sorted(newly_unavailable))
        changes.append({
            "type": "AVAILABILITY CHANGE",
            "title": "Material availability changed",
            "previous": "Available / no issue detected",
            "current": f"{material_list} unavailable",
            "impact": (
                "Procurement may be affected by the newly reported "
                "availability issue."
            ),
            "action": (
                "Confirm supplier availability and evaluate an approved "
                "alternative."
            ),
        })

    return {"changes": changes}
