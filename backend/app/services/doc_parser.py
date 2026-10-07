"""Rule-based (regex/keyword) extraction of structured fields from OCR'd or
extracted document text. No AI/cloud calls — everything runs locally.

This is inherently best-effort: official document layouts vary over time and
across notice types. Extracted fields are always presented to the user for
confirmation before being saved (see documents router) rather than trusted
blindly.
"""
import re
from datetime import date

from ..models import DocType, PatentType

CN_DIGIT_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

# Ordered: decision/final-outcome documents are checked before procedural
# notice types. A rejection decision's reasoning almost always quotes the
# prior office action ("审查意见通知书") it's based on, so if that keyword is
# checked first, a real 驳回决定 document gets misclassified as an office
# action just because its body text mentions one. Checking the more
# "definitive" outcome types first (and, in detect_doc_type, restricting the
# search to the title area near the top of the document) avoids that.
DOC_TYPE_KEYWORDS: list[tuple[DocType, list[str]]] = [
    (DocType.REJECTION_DECISION, ["驳回决定"]),
    (DocType.INVALIDATION_DECISION, ["无效宣告请求审查决定", "无效宣告审查决定"]),
    # Full title phrase, not bare "视为撤回" — nearly every notice type (补正
    # 通知书, 审查意见通知书...) warns that non-response "将被视为撤回" as
    # boilerplate, which would otherwise false-match on the wrong document.
    (DocType.DEEMED_WITHDRAWN_NOTICE, ["视为撤回通知书"]),
    (DocType.GRANT_NOTICE, ["授予专利权通知书", "授权通知书"]),
    (DocType.REGISTRATION_NOTICE, ["办理登记手续通知书"]),
    (DocType.CORRECTION_NOTICE, ["补正通知书"]),
    (DocType.OFFICE_ACTION, ["审查意见通知书"]),
    (DocType.PRELIM_EXAM_PASS_NOTICE, ["初步审查合格通知书"]),
    (DocType.RECEIPT_NOTICE, ["受理通知书"]),
    (DocType.REEXAM_ACCEPTANCE_NOTICE, ["复审请求受理通知书"]),
    (DocType.REEXAM_NOTICE, ["复审通知书"]),
    (DocType.INVALIDATION_NOTICE, ["无效宣告请求受理通知书"]),
    (DocType.ANNUITY_NOTICE, ["年费缴纳通知书", "年费催缴通知书", "专利年费"]),
    (DocType.RESTORATION_NOTICE, ["权利恢复"]),
]

# Official notice titles are always near the top of page 1. Restricting
# keyword matching to this window (falling back to the whole text only if
# nothing matched) stops incidental mentions deeper in the body — e.g. a
# rejection decision's reasoning paragraph quoting "审查意见通知书" — from
# being mistaken for the document's own title/type.
TITLE_SEARCH_WINDOW = 800

PATENT_TYPE_KEYWORDS: list[tuple[PatentType, list[str]]] = [
    (PatentType.INVENTION, ["发明专利", "发明名称"]),
    (PatentType.UTILITY_MODEL, ["实用新型"]),
    (PatentType.DESIGN, ["外观设计"]),
]

# CNIPA notices frequently render dates with a letter-spaced/justified font
# (e.g. "2026 年 06 月 30 日"), which PDF text extraction turns into literal
# spaces between every token. \s* around each unit tolerates that.
DATE_PATTERN = re.compile(r"(\d{4})\s*[年.\-/]\s*(\d{1,2})\s*[月.\-/]\s*(\d{1,2})\s*日?")
_DATE_CORE = r"\d{4}\s*[年.\-/]\s*\d{1,2}\s*[月.\-/]\s*\d{1,2}\s*日?"
APPLICATION_NO_PATTERN = re.compile(r"(?:申请号|专利号)[／/]?(?:\(专利号\))?\s*[:：]\s*([0-9A-Za-z.]+)")
APPLICANT_PATTERN = re.compile(r"(?:申请人|专利权人)\s*[:：]\s*([^\n]+)")
PATENT_NAME_PATTERN = re.compile(r"(?:发明创造名称|发明名称|实用新型名称|外观设计名称|名称)\s*[:：]\s*([^\n]+)")
# Tolerates stray spaces between characters (common artifact of letter-spaced
# titles/labels in these notices) and both "发文日" / "发文日期" label variants.
ISSUE_DATE_LABEL_PATTERN = re.compile(rf"发\s*文\s*日\s*期?\s*[:：]?\s*({_DATE_CORE})")
VARIANT_PATTERN = re.compile(r"第([一二三四五六七八九十]+)次")

# Chinese text never legitimately contains spaces between characters, so any
# horizontal whitespace PDF extraction inserts between two CJK ideographs
# (common in letter-spaced titles like "第 一 次 补 正 通 知 书") is always
# safe to collapse before running keyword/label matching against the text.
# Deliberately [ \t] and NOT \s here — \s also matches newlines, and this
# text has a CJK character on nearly every line, so matching newlines would
# collapse real line breaks that other patterns (e.g. the `[^\n]+` line-based
# captures below) rely on to know where a field's value ends.
_CJK_GAP_PATTERN = re.compile(r"(?<=[一-鿿])[ \t]+(?=[一-鿿])")

# For keyword/phrase presence checks specifically (doc type / patent type /
# variant), line breaks don't carry meaning the way they do for the `[^\n]+`
# field-value captures above — but ordinary paragraph word-wrap can still
# split a keyword phrase exactly across a line (e.g. "审查员对上述实\n用新型
# 专利申请进行了初步审查" — "实用新型" broken across the wrap), causing a
# real false negative. So keyword matching gets its own, more aggressive
# normalization that also collapses newlines between CJK characters.
_CJK_GAP_PATTERN_ANY_WS = re.compile(r"(?<=[一-鿿])\s+(?=[一-鿿])")


def normalize_extracted_text(text: str) -> str:
    return _CJK_GAP_PATTERN.sub("", text)


def _normalize_for_keyword_search(text: str) -> str:
    return _CJK_GAP_PATTERN_ANY_WS.sub("", text)


def _parse_date(text: str) -> date | None:
    m = DATE_PATTERN.search(text)
    if not m:
        return None
    year, month, day = (int(g) for g in m.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def detect_doc_type(text: str) -> DocType:
    head = text[:TITLE_SEARCH_WINDOW]
    for doc_type, keywords in DOC_TYPE_KEYWORDS:
        if any(kw in head for kw in keywords):
            return doc_type
    # Title fell outside the window (unusually long header block, etc.) —
    # fall back to searching the whole document.
    for doc_type, keywords in DOC_TYPE_KEYWORDS:
        if any(kw in text for kw in keywords):
            return doc_type
    return DocType.OTHER


def detect_variant(text: str, doc_type: DocType) -> str | None:
    if doc_type not in (DocType.OFFICE_ACTION, DocType.CORRECTION_NOTICE):
        return None
    m = VARIANT_PATTERN.search(text)
    if m:
        cn_num = m.group(1)
        if cn_num in CN_DIGIT_MAP:
            return f"第{cn_num}次"
    if doc_type == DocType.CORRECTION_NOTICE and "主动" in text:
        return "主动补正"
    return None


def detect_patent_type(text: str) -> PatentType | None:
    for patent_type, keywords in PATENT_TYPE_KEYWORDS:
        if any(kw in text for kw in keywords):
            return patent_type
    return None


def extract_application_no(text: str) -> str | None:
    m = APPLICATION_NO_PATTERN.search(text)
    return m.group(1).strip() if m else None


def extract_applicant(text: str) -> str | None:
    m = APPLICANT_PATTERN.search(text)
    if not m:
        return None
    return m.group(1).strip().strip("，,")


def extract_patent_name(text: str) -> str | None:
    m = PATENT_NAME_PATTERN.search(text)
    return m.group(1).strip() if m else None


def extract_issue_date(text: str) -> date | None:
    labeled = ISSUE_DATE_LABEL_PATTERN.search(text)
    if labeled:
        return _parse_date(labeled.group(1))
    # No labeled "发文日" found (label OCR'd wrong, or a layout that doesn't use
    # that wording) — official notices place the issue date near the top of
    # page 1, so prefer a bare date found there over one found deeper in the
    # body (which is more likely to be an unrelated date, e.g. an application
    # filing date mentioned in the text).
    near_top = _parse_date(text[:600])
    if near_top:
        return near_top
    return _parse_date(text)


def parse_document(text: str) -> dict:
    # Normalize once for all matching below; the caller keeps the original
    # (un-normalized) text for raw_text storage/display.
    normalized = normalize_extracted_text(text)
    # Keyword/phrase detection (doc type, patent type, variant) uses the more
    # aggressive newline-collapsing normalization, since a keyword phrase can
    # legitimately be split across a line wrap even when nothing was OCR'd
    # wrong. Field-value extraction below stays on `normalized`, which keeps
    # real newlines intact — those regexes rely on `[^\n]+` to know where a
    # field's value ends.
    keyword_text = _normalize_for_keyword_search(normalized)
    doc_type = detect_doc_type(keyword_text)
    return {
        "doc_type": doc_type,
        "doc_variant": detect_variant(keyword_text, doc_type),
        "issue_date": extract_issue_date(normalized),
        "application_no": extract_application_no(normalized),
        "applicant_name": extract_applicant(normalized),
        "patent_name": extract_patent_name(normalized),
        "patent_type": detect_patent_type(keyword_text),
    }
