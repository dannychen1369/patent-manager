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
from .patent_type import patent_type_from_application_no

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
    # Real titles name the type: 授予发明专利权通知书 / 授予实用新型专利权通知书 /
    # 授予外观设计专利权通知书 — none contain the bare "授予专利权通知书".
    (
        DocType.GRANT_NOTICE,
        [
            "授予发明专利权通知书",
            "授予实用新型专利权通知书",
            "授予外观设计专利权通知书",
            "授予专利权通知书",
            "授权通知书",
        ],
    ),
    (DocType.REGISTRATION_NOTICE, ["办理登记手续通知书"]),
    (DocType.CORRECTION_NOTICE, ["补正通知书"]),
    (DocType.OFFICE_ACTION, ["审查意见通知书"]),
    # Also matches the combined "发明专利申请公布及进入实质审查阶段通知书",
    # so it must come before the plain publication notice.
    (DocType.SUBSTANTIVE_EXAM_NOTICE, ["进入实质审查阶段通知书"]),
    (DocType.PUBLICATION_NOTICE, ["申请公布通知书"]),
    (DocType.PRELIM_EXAM_PASS_NOTICE, ["初步审查合格通知书"]),
    # 复审请求受理通知书 / 无效宣告请求受理通知书 both contain "受理通知书",
    # so they must be checked before the plain 受理通知书 (new application).
    (DocType.REEXAM_ACCEPTANCE_NOTICE, ["复审请求受理通知书"]),
    (DocType.INVALIDATION_NOTICE, ["无效宣告请求受理通知书"]),
    (DocType.REEXAM_NOTICE, ["复审通知书"]),
    (DocType.FEE_REDUCTION_NOTICE, ["收费减缴审批通知书", "费用减缴审批通知书", "费用减缓审批通知书"]),
    (DocType.FEE_PAYMENT_NOTICE, ["缴纳申请费通知书"]),
    (DocType.RECEIPT_NOTICE, ["受理通知书"]),
    (DocType.ANNUITY_NOTICE, ["年费缴纳通知书", "年费催缴通知书", "专利年费"]),
    (DocType.RESTORATION_NOTICE, ["权利恢复"]),
]

# Every CNIPA notice prints a fixed 6-digit form code (表格编号) in its footer,
# right before the "纸件申请，回函请寄" line (often with a version like
# "2023.03" in between). The code identifies the notice type exactly, so
# it's checked before any title keyword guessing. Codes here are taken from
# real notices; unknown codes simply fall back to keyword matching.
FORM_CODE_PATTERN = re.compile(r"(?<!\d)(\d{6})\s*(?:\d{4}\.\d{2}\s*)?纸件申请")
FORM_CODE_DOC_TYPES: dict[str, DocType] = {
    "200101": DocType.RECEIPT_NOTICE,  # 专利申请受理通知书
    "200021": DocType.FEE_REDUCTION_NOTICE,  # 收费减缴审批通知书
    "200305": DocType.REJECTION_DECISION,  # 驳回决定（初审，实用新型）
    "210407": DocType.REJECTION_DECISION,  # 驳回决定（实审，发明）
    "220301": DocType.OFFICE_ACTION,  # 审查意见通知书
    "220302": DocType.CORRECTION_NOTICE,  # 补正通知书
}

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
# Filing date, printed on 受理通知书 and repeated on most later notices.
APPLICATION_DATE_LABEL_PATTERN = re.compile(rf"申\s*请\s*日\s*期?\s*[:：]?\s*({_DATE_CORE})")
# Examiners can issue any number of rounds, so accept 第十一次 / 第二十三次 and
# Arabic 第3次 too, not just a single character.
VARIANT_PATTERN = re.compile(r"第\s*([一二三四五六七八九十]+|\d{1,2})\s*次")

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


def extract_form_code(text: str) -> str | None:
    m = FORM_CODE_PATTERN.search(text)
    return m.group(1) if m else None


def detect_doc_type(text: str) -> DocType:
    form_code = extract_form_code(text)
    if form_code in FORM_CODE_DOC_TYPES:
        return FORM_CODE_DOC_TYPES[form_code]
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


_CN_UNITS = "一二三四五六七八九"


def cn_to_int(cn: str) -> int | None:
    """一 → 1, 十 → 10, 十一 → 11, 二十 → 20, 二十三 → 23, "3" → 3."""
    if cn.isdigit():
        return int(cn)
    if "十" not in cn:
        return CN_DIGIT_MAP.get(cn) if len(cn) == 1 else None
    tens, _, ones = cn.partition("十")
    if len(tens) > 1 or len(ones) > 1:
        return None
    tens_val = CN_DIGIT_MAP.get(tens, 0) if tens else 1
    ones_val = CN_DIGIT_MAP.get(ones, 0) if ones else 0
    return tens_val * 10 + ones_val


def int_to_cn(n: int) -> str:
    if n < 10:
        return _CN_UNITS[n - 1]
    tens, ones = divmod(n, 10)
    return (_CN_UNITS[tens - 1] if tens > 1 else "") + "十" + (_CN_UNITS[ones - 1] if ones else "")


def variant_ordinal(variant: str | None) -> int | None:
    """"第三次" → 3; None for 主动补正 / no variant."""
    if not variant:
        return None
    m = VARIANT_PATTERN.fullmatch(variant.strip())
    return cn_to_int(m.group(1)) if m else None


def detect_variant(text: str, doc_type: DocType) -> str | None:
    if doc_type not in (DocType.OFFICE_ACTION, DocType.CORRECTION_NOTICE):
        return None
    m = VARIANT_PATTERN.search(text)
    if m:
        n = cn_to_int(m.group(1))
        if n and 1 <= n <= 99:
            # Always stored in the canonical Chinese form ("第三次"), which
            # stage mapping and deadline rules key on.
            return f"第{int_to_cn(n)}次"
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


# Fee notices state the payment deadline as an actual date ("申请人应当于
# 2026年12月8日之前缴纳下列费用"), unlike reply deadlines which are a period
# counted from the issue date. Read the date itself rather than computing it.
PAYMENT_DEADLINE_PATTERN = re.compile(rf"应\s*当\s*于\s*({_DATE_CORE})\s*之\s*前\s*缴\s*纳")
PAYMENT_TOTAL_PATTERN = re.compile(r"共\s*计\s*[:：]?\s*([\d,.]+)\s*元")


def extract_stated_deadlines(text: str) -> list[dict]:
    """Deadlines whose due date is printed in the notice itself."""
    normalized = _normalize_for_keyword_search(normalize_extracted_text(text))
    results = []
    m = PAYMENT_DEADLINE_PATTERN.search(normalized)
    if m:
        due = _parse_date(m.group(1))
        total = PAYMENT_TOTAL_PATTERN.search(normalized)
        label = "缴纳费用期限" + (f"（共计{total.group(1)}元）" if total else "")
        if due:
            results.append({"deadline_type": label, "due_date": due})
    return results


# Reply periods are usually printed in the notice ("申请人应当自收到本通知之日
# 起两个月内陈述意见"). Anchored on "应当" so boilerplate like "可以在收到本通知
# 之日起6个月内向北京知识产权法院起诉" is not mistaken for the reply period.
STATED_PERIOD_PATTERN = re.compile(
    r"应\s*当\s*自\s*收\s*到\s*本\s*通\s*知\s*书?\s*之\s*日\s*起\s*的?\s*"
    r"([一二三四五六两]|\d{1,2})\s*个\s*月\s*内"
)


def extract_stated_period_months(text: str) -> int | None:
    normalized = _normalize_for_keyword_search(normalize_extracted_text(text))
    m = STATED_PERIOD_PATTERN.search(normalized)
    if not m:
        return None
    raw = m.group(1)
    return int(raw) if raw.isdigit() else {"两": 2, **CN_DIGIT_MAP}.get(raw)


DISPATCH_NO_PATTERN = re.compile(r"发\s*文\s*序\s*号\s*[:：]?\s*(\d{10,20})")


def extract_dispatch_no(text: str) -> str | None:
    m = DISPATCH_NO_PATTERN.search(text)
    return m.group(1) if m else None


def extract_application_date(text: str) -> date | None:
    m = APPLICATION_DATE_LABEL_PATTERN.search(text)
    return _parse_date(m.group(1)) if m else None


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
    application_no = extract_application_no(normalized)
    return {
        "doc_type": doc_type,
        "doc_variant": detect_variant(keyword_text, doc_type),
        "issue_date": extract_issue_date(normalized),
        "application_date": extract_application_date(normalized),
        "application_no": application_no,
        "form_code": extract_form_code(normalized),
        "dispatch_no": extract_dispatch_no(normalized),
        "applicant_name": extract_applicant(normalized),
        "patent_name": extract_patent_name(normalized),
        # The type digit in the application number is authoritative; keyword
        # guessing is only a fallback for notices without a number yet.
        "patent_type": patent_type_from_application_no(application_no)
        or detect_patent_type(keyword_text),
    }
