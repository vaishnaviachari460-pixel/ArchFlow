import re
from datetime import datetime, timedelta


SPEAKER_NAMES = (
    "Client|Architect|Contractor|Supplier|Consultant|Fabricator|"
    "Installer|Site Engineer|Electrical Contractor|Project Manager"
)
SPEAKER_MARKER = re.compile(rf"(?<!\w)({SPEAKER_NAMES})\s*:", re.IGNORECASE)
MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def group_messages(text):
    if not text:
        return []
    text = str(text).replace("\r", "\n")
    matches = list(SPEAKER_MARKER.finditer(text))
    if not matches:
        cleaned = clean_text(text)
        return [{"speaker": "", "text": cleaned}] if cleaned else []

    messages = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = clean_text(text[match.end():end])
        if body:
            messages.append({"speaker": match.group(1).strip(), "text": body})
    return messages


def extract_revisions(text):
    return sorted({int(n) for n in re.findall(r"\brev(?:ision)?\s*[-#]?\s*(\d+)\b", str(text), re.I)})


def extract_materials(text):
    return sorted(set(re.findall(r"\b[A-Z]{1,5}-\d{2,5}\b", str(text))))


def format_date(date_object):
    return date_object.strftime("%d %B %Y").lstrip("0") + f" ({date_object.strftime('%A')})"


def _parse_date(day, month, year=None):
    year = year or datetime.now().year
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(
                f"{day} {month} {year}",
                fmt
            )
        except ValueError:
            pass
    return None


def _next_weekday(name, reference=None):
    reference = reference or datetime.now()
    target = WEEKDAYS.index(name.capitalize())
    delta = (target - reference.weekday()) % 7
    if delta == 0:
        delta = 7
    return reference + timedelta(days=delta)


def detect_deadlines(text):
    text = clean_text(text)
    deadlines = []
    seen = set()
    current_year = datetime.now().year

    def add(value):
        if value and value not in seen:
            seen.add(value)
            deadlines.append(value)

    month_pattern = re.compile(
        rf"\b(\d{{1,2}})\s+({MONTH_NAMES})(?:\s+(\d{{4}}))?\b", re.I
    )
    for match in month_pattern.finditer(text):
        day, month, year = int(match.group(1)), match.group(2), match.group(3)
        parsed = _parse_date(day, month, int(year) if year else current_year)
        if parsed:
            add(format_date(parsed))

    for match in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text):
        day, month, year = map(int, match.groups())
        year += 2000 if year < 100 else 0
        try:
            add(format_date(datetime(year, month, day)))
        except ValueError:
            pass

    if re.search(r"\btoday\b", text, re.I):
        add(format_date(datetime.now()))
    if re.search(r"\btomorrow\b", text, re.I):
        add(format_date(datetime.now() + timedelta(days=1)))

    # Weekdays are converted to an actual upcoming date. This prevents the UI
    # from displaying an ambiguous value such as only "Friday".
    for weekday in WEEKDAYS:
        if re.search(rf"\b{weekday}\b", text, re.I):
            add(format_date(_next_weekday(weekday)))

    return deadlines


def detect_deadline_details(text):
    details = []
    for message in group_messages(text):
        body = clean_text(message["text"])
        if not body:
            continue
        message_deadlines = detect_deadlines(body)
        if not message_deadlines:
            continue
        action = extract_explicit_action_from_message(body)
        details.append({
            "deadline": message_deadlines[0],
            "action": action["action"] if action else None,
            "owner": message["speaker"] or "Project Team",
        })
    return details


def is_actual_decision(text):
    t = clean_text(text).lower()
    if not t:
        return False
    pending = [
        r"\bplease\s+(?:check|confirm|verify|review|approve|advise)\b",
        r"\b(?:awaiting|pending)\s+(?:approval|confirmation)\b",
        r"\b(?:approval|confirmation)\s+(?:is\s+)?required\b",
        r"\bsubject\s+to\s+(?:approval|confirmation)\b",
        r"\bwithout\s+approval\b",
    ]
    if any(re.search(p, t) for p in pending):
        return False
    decisions = [
        r"\bi\s+approve(?:d)?\b", r"\bwe\s+approve(?:d)?\b",
        r"^approved\s*[.!?,]?\s*$",
        r"^approved\s*[.!?,]?\s+(?:proceed|continue|go|use|implement|purchase)\b",
        r"\bapproved\s+to\s+proceed\b", r"\bapproved\s+for\s+use\b",
        r"\bapproval\s+granted\b", r"\bproceed\s+with\b",
        r"\bproceed\s+as\s+approved\b", r"\bdecision\s+is\b",
        r"\bconfirmation\s+received\b", r"^accepted\s*[.!]?\s*$",
        r"^rejected\s*[.!]?\s*$", r"\bgo\s+ahead\b",
        r"\bdo\s+not\s+proceed\b", r"\bcannot\s+proceed\b",
    ]
    return any(re.search(p, t) for p in decisions)


def detect_decisions(text):
    result = []
    for message in group_messages(text):
        body = clean_text(message["text"])
        if body and is_actual_decision(body):
            result.append({"decision": body, "owner": message["speaker"] or "Project Team"})
    return result


def clean_action_text(text):
    action = clean_text(text)
    action = re.sub(r"^(?:please|kindly)\s+", "", action, flags=re.I)
    action = re.sub(r"^(?:i|we|team)\s+will\s+", "", action, flags=re.I)
    action = re.sub(r"^must\s+(?:be\s+)?", "", action, flags=re.I)
    action = re.sub(r"^need\s+to\s+", "", action, flags=re.I)
    action = re.sub(r"\s+by\s+(?:\d{1,2}\s+(?:" + MONTH_NAMES + r")(?:\s+\d{4})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|today|tomorrow|(?:" + "|".join(WEEKDAYS) + r"))\b", "", action, flags=re.I)
    action = re.sub(r"[.!?]+$", "", action)
    return action.strip()


def _is_explicit_action(message):
    t = message.lower().strip()
    patterns = [
        r"\bmust\s+(?:be\s+)?(?:completed|submitted|shared|verified|reviewed|confirmed|checked|approved|prepared|provided|sent|finalized|updated|inspected|delivered)\b",
        r"\b(?:i|we|team)\s+will\s+(?:verify|review|submit|check|confirm|prepare|share|complete|provide|send|update|finalize|inspect|coordinate|arrange|deliver)\b",
        r"\bneed\s+to\s+(?:check|confirm|verify|review|prepare|submit|complete|share|provide|update|finalize)\b",
        r"\b(?:please|kindly)\s+(?:check|confirm|verify|review|prepare|submit|share|complete|provide|update|finalize|ensure|coordinate|arrange)\b",
        r"^(?:prepare|check|confirm|verify|review|submit|share|complete|provide|update|finalize|coordinate|arrange|inspect|ensure)\b",
    ]
    return any(re.search(p, t) for p in patterns)


def extract_explicit_action_from_message(message, speaker=""):
    if not _is_explicit_action(message) or is_actual_decision(message):
        return None
    deadlines = detect_deadlines(message)
    return {
        "action": clean_action_text(message),
        "owner": speaker or "Project Team",
        "deadline": deadlines[0] if deadlines else None,
    }


def detect_explicit_actions(text):
    actions = []
    for message in group_messages(text):
        action = extract_explicit_action_from_message(message["text"], message["speaker"])
        if action and action["action"]:
            actions.append(action)
    return actions


def create_action(action, owner, deadline=None):
    return {"action": action, "owner": owner or "Project Team", "deadline": deadline}


def contains_any(text, words):
    return any(word.lower() in text.lower() for word in words)


def detect_risks(text):
    text = clean_text(text)
    lower = text.lower()
    risks = []
    revisions = extract_revisions(text)
    if len(revisions) >= 2 and min(revisions) != max(revisions):
        risks.append({
            "risk": "Drawing revision conflict",
            "description": f"Different drawing revisions are being referenced (Rev {min(revisions)} and Rev {max(revisions)}).",
            "severity": "HIGH",
            "category": "REVISION",
        })
    if contains_any(lower, ["unavailable", "not available", "out of stock", "discontinued"]):
        risks.append({
            "risk": "Material availability issue",
            "description": "A required material is currently unavailable or out of stock.",
            "severity": "HIGH",
            "category": "MATERIAL",
        })
    if contains_any(lower, ["delayed", "delay", "behind schedule", "late", "one week"]):
        risks.append({
            "risk": "Potential project delay",
            "description": "The communication indicates a schedule or delivery delay.",
            "severity": "HIGH",
            "category": "SCHEDULE",
        })
    if "cannot be extended" in lower or "cannot extend" in lower:
        risks.append({
            "risk": "Deadline may be affected",
            "description": "A fixed project deadline may be affected by current work or delivery issues.",
            "severity": "HIGH",
            "category": "DEADLINE",
        })
    if "supplier" in lower and any(x in lower for x in ["alternative", "availability", "out of stock", "unavailable"]):
        risks.append({
            "risk": "Procurement risk",
            "description": "Material procurement may require an alternative or supplier confirmation.",
            "severity": "MEDIUM",
            "category": "PROCUREMENT",
        })
    return risks


def detect_actions(text, deadlines=None, risks=None, decisions=None):
    actions = detect_explicit_actions(text)
    unique = []
    seen = set()
    for action in actions:
        key = (action["action"].lower(), action["owner"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(action)
    return unique


def generate_summary(text, risks, decisions, actions, deadlines):
    count = len(group_messages(text))
    parts = [f"{count} communication item{'s' if count != 1 else ''} analyzed."]
    if risks:
        parts.append("Key risks: " + ", ".join(r["risk"] for r in risks) + ".")
    if decisions:
        parts.append(f"{len(decisions)} decision{'s' if len(decisions) != 1 else ''} detected.")
    if actions:
        parts.append(f"{len(actions)} action{'s' if len(actions) != 1 else ''} identified.")
    if deadlines:
        parts.append(f"{len(deadlines)} deadline{'s' if len(deadlines) != 1 else ''} detected.")
    return " ".join(parts)


def calculate_project_health(risks):
    high = sum(r.get("severity") == "HIGH" for r in risks)
    medium = sum(r.get("severity") == "MEDIUM" for r in risks)
    if high:
        return "HIGH RISK"
    if medium >= 2:
        return "AT RISK"
    if medium == 1:
        return "WATCH"
    return "HEALTHY"


def calculate_priority(risks):
    if any(r.get("severity") == "HIGH" for r in risks):
        return "HIGH"
    if any(r.get("severity") == "MEDIUM" for r in risks):
        return "MEDIUM"
    return "LOW"


def generate_health_reasons(risks):
    return [r.get("description", r.get("risk", "")) for r in risks] or ["No major project risks detected."]


def generate_health_explanation(risks):
    if not risks:
        return "No major project risks were detected."
    high = sum(r.get("severity") == "HIGH" for r in risks)
    if high:
        return f"{len(risks)} risk signal{'s' if len(risks) != 1 else ''} detected, including {high} high-severity risk{'s' if high != 1 else ''}."
    return f"{len(risks)} medium-severity risk{'s' if len(risks) != 1 else ''} detected."


def detect_material_events(text):
    lower = text.lower()
    materials = extract_materials(text)
    events = []
    if materials:
        events.append({"materials": materials, "status": "REFERENCED"})
    if contains_any(lower, ["unavailable", "out of stock", "not available", "discontinued"]):
        events.append({"materials": materials, "status": "UNAVAILABLE"})
    if "approve" in lower and materials:
        events.append({"materials": materials, "status": "APPROVAL MENTIONED"})
    if any(x in lower for x in ["order", "ordering", "procurement", "purchase"]):
        events.append({"materials": materials, "status": "PROCUREMENT MENTIONED"})
    return events


def analyze_communication(text):
    if not text or not str(text).strip():
        return {
            "summary": "No communication provided.", "risks": [], "risk_details": [],
            "decisions": [], "actions": [], "deadlines": [], "deadline_details": [],
            "project_health": "HEALTHY", "priority": "LOW", "health_reasons": ["No communication provided."],
            "health_explanation": "No communication provided.", "revisions": [], "materials": [],
            "message_count": 0,
        }

    deadlines = detect_deadlines(text)
    decisions = detect_decisions(text)
    risks = detect_risks(text)
    actions = detect_actions(text, deadlines, risks, decisions)
    deadline_details = detect_deadline_details(text)
    health = calculate_project_health(risks)

    return {
        "summary": generate_summary(text, risks, decisions, actions, deadlines),
        "risks": risks,
        "risk_details": risks,
        "decisions": decisions,
        "actions": actions,
        "deadlines": deadlines,
        "deadline_details": deadline_details,
        "project_health": health,
        "priority": calculate_priority(risks),
        "health_reasons": generate_health_reasons(risks),
        "health_explanation": generate_health_explanation(risks),
        "revisions": extract_revisions(text),
        "materials": extract_materials(text),
        "material_events": detect_material_events(text),
        "message_count": len(group_messages(text)),
    }
