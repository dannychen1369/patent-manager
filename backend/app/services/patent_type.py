"""Derive the patent type from a CNIPA application number.

Per the CNIPA application-number standard (ZC 0006-2003), the application
type digit sits right after the year:

    2025 2 1713967 . 4      (since 2003: 4-digit year + type + 7-digit serial)
    85 1 00001 . 2          (before 2003: 2-digit year + type + 5-digit serial)

    1 = 发明, 2 = 实用新型, 3 = 外观设计,
    8 = PCT 发明进入中国国家阶段, 9 = PCT 实用新型进入中国国家阶段

The application number is authoritative, unlike keyword guessing on the
notice text (a 实用新型 notice can easily mention "发明" somewhere).
"""
import re

from ..models import PatentType

_TYPE_DIGIT_MAP = {
    "1": PatentType.INVENTION,
    "2": PatentType.UTILITY_MODEL,
    "3": PatentType.DESIGN,
    "8": PatentType.INVENTION,
    "9": PatentType.UTILITY_MODEL,
}


def patent_type_from_application_no(application_no: str | None) -> PatentType | None:
    if not application_no:
        return None
    # Drop the check digit (after the dot) and any prefix/spacing such as
    # "CN", "ZL", "201", spaces — keep only the digits of the core number.
    core = re.sub(r"\D", "", application_no.split(".")[0].upper().replace("ZL", "").replace("CN", ""))
    if len(core) == 12:
        return _TYPE_DIGIT_MAP.get(core[4])
    if len(core) == 13:
        # Check digit written without the dot (e.g. "2025217139674").
        return _TYPE_DIGIT_MAP.get(core[4])
    if len(core) in (8, 9):
        return _TYPE_DIGIT_MAP.get(core[2])
    return None
