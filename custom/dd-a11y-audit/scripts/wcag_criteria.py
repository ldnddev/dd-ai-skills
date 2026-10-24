#!/usr/bin/env python3
"""WCAG 2.2 success criteria for the scanned level.

One catalog. The report lists criteria whose axe SC tag was not in the run.
4.1.1 Parsing was removed in WCAG 2.2 and is not in this list.
"""

# (id, level, name). Level is the criterion's own level.
WCAG22 = (
    ("1.1.1", "A", "Non-text Content"),
    ("1.2.1", "A", "Audio-only and Video-only (Prerecorded)"),
    ("1.2.2", "A", "Captions (Prerecorded)"),
    ("1.2.3", "A", "Audio Description or Media Alternative (Prerecorded)"),
    ("1.2.4", "AA", "Captions (Live)"),
    ("1.2.5", "AA", "Audio Description (Prerecorded)"),
    ("1.2.6", "AAA", "Sign Language (Prerecorded)"),
    ("1.2.7", "AAA", "Extended Audio Description (Prerecorded)"),
    ("1.2.8", "AAA", "Media Alternative (Prerecorded)"),
    ("1.2.9", "AAA", "Audio-only (Live)"),
    ("1.3.1", "A", "Info and Relationships"),
    ("1.3.2", "A", "Meaningful Sequence"),
    ("1.3.3", "A", "Sensory Characteristics"),
    ("1.3.4", "AA", "Orientation"),
    ("1.3.5", "AA", "Identify Input Purpose"),
    ("1.3.6", "AAA", "Identify Purpose"),
    ("1.4.1", "A", "Use of Color"),
    ("1.4.2", "A", "Audio Control"),
    ("1.4.3", "AA", "Contrast (Minimum)"),
    ("1.4.4", "AA", "Resize Text"),
    ("1.4.5", "AA", "Images of Text"),
    ("1.4.6", "AAA", "Contrast (Enhanced)"),
    ("1.4.7", "AAA", "Low or No Background Audio"),
    ("1.4.8", "AAA", "Visual Presentation"),
    ("1.4.9", "AAA", "Images of Text (No Exception)"),
    ("1.4.10", "AA", "Reflow"),
    ("1.4.11", "AA", "Non-text Contrast"),
    ("1.4.12", "AA", "Text Spacing"),
    ("1.4.13", "AA", "Content on Hover or Focus"),
    ("2.1.1", "A", "Keyboard"),
    ("2.1.2", "A", "No Keyboard Trap"),
    ("2.1.3", "AAA", "Keyboard (No Exception)"),
    ("2.1.4", "A", "Character Key Shortcuts"),
    ("2.2.1", "A", "Timing Adjustable"),
    ("2.2.2", "A", "Pause, Stop, Hide"),
    ("2.2.3", "AAA", "No Timing"),
    ("2.2.4", "AAA", "Interruptions"),
    ("2.2.5", "AAA", "Re-authenticating"),
    ("2.2.6", "AAA", "Timeouts"),
    ("2.3.1", "A", "Three Flashes or Below Threshold"),
    ("2.3.2", "AAA", "Three Flashes"),
    ("2.3.3", "AAA", "Animation from Interactions"),
    ("2.4.1", "A", "Bypass Blocks"),
    ("2.4.2", "A", "Page Titled"),
    ("2.4.3", "A", "Focus Order"),
    ("2.4.4", "A", "Link Purpose (In Context)"),
    ("2.4.5", "AA", "Multiple Ways"),
    ("2.4.6", "AA", "Headings and Labels"),
    ("2.4.7", "AA", "Focus Visible"),
    ("2.4.8", "AAA", "Location"),
    ("2.4.9", "AAA", "Link Purpose (Link Only)"),
    ("2.4.10", "AAA", "Section Headings"),
    ("2.4.11", "AA", "Focus Not Obscured (Minimum)"),
    ("2.4.12", "AAA", "Focus Not Obscured (Enhanced)"),
    ("2.4.13", "AAA", "Focus Appearance"),
    ("2.5.1", "A", "Pointer Gestures"),
    ("2.5.2", "A", "Pointer Cancellation"),
    ("2.5.3", "A", "Label in Name"),
    ("2.5.4", "A", "Motion Actuation"),
    ("2.5.5", "AAA", "Target Size (Enhanced)"),
    ("2.5.6", "AAA", "Concurrent Input Mechanisms"),
    ("2.5.7", "AA", "Dragging Movements"),
    ("2.5.8", "AA", "Target Size (Minimum)"),
    ("3.1.1", "A", "Language of Page"),
    ("3.1.2", "AA", "Language of Parts"),
    ("3.1.3", "AAA", "Unusual Words"),
    ("3.1.4", "AAA", "Abbreviations"),
    ("3.1.5", "AAA", "Reading Level"),
    ("3.1.6", "AAA", "Pronunciation"),
    ("3.2.1", "A", "On Focus"),
    ("3.2.2", "A", "On Input"),
    ("3.2.3", "AA", "Consistent Navigation"),
    ("3.2.4", "AA", "Consistent Identification"),
    ("3.2.5", "AAA", "Change on Request"),
    ("3.2.6", "A", "Consistent Help"),
    ("3.3.1", "A", "Error Identification"),
    ("3.3.2", "A", "Labels or Instructions"),
    ("3.3.3", "AA", "Error Suggestion"),
    ("3.3.4", "AA", "Error Prevention (Legal, Financial, Data)"),
    ("3.3.5", "AAA", "Help"),
    ("3.3.6", "AAA", "Error Prevention (All)"),
    ("3.3.7", "A", "Redundant Entry"),
    ("3.3.8", "AA", "Accessible Authentication (Minimum)"),
    ("3.3.9", "AAA", "Accessible Authentication (Enhanced)"),
    ("4.1.2", "A", "Name, Role, Value"),
    ("4.1.3", "AA", "Status Messages"),
)

_LEVEL_RANK = {"A": 1, "AA": 2, "AAA": 3}


def sc_axe_tag(sc_id):
    """axe success-criterion tag for a dotted id. 1.4.10 -> wcag1410."""
    return "wcag" + sc_id.replace(".", "")


def criteria_for_level(level):
    """Criteria required at this scan level. AA includes A. Unknown levels use AA."""
    rank = _LEVEL_RANK.get(level or "AA", _LEVEL_RANK["AA"])
    return [
        {"id": sc_id, "level": sc_level, "name": name}
        for sc_id, sc_level, name in WCAG22
        if _LEVEL_RANK[sc_level] <= rank
    ]


def criteria_not_run(level, checked_tags):
    """Criteria at ``level`` whose axe tag is absent from the run."""
    checked = set(checked_tags or [])
    return [
        sc for sc in criteria_for_level(level)
        if sc_axe_tag(sc["id"]) not in checked
    ]
