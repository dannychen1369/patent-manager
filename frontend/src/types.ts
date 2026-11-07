export type PatentType = "发明专利" | "实用新型" | "外观设计" | "未知";

export type CaseStage =
  | "待确认"
  | "待撰写"
  | "撰写中"
  | "已提交申请"
  | "已受理"
  | "初审合格"
  | "已公布"
  | "实质审查"
  | "一审"
  | "二审"
  | "三审及以后"
  | "补正"
  | "复审"
  | "无效宣告"
  | "授权"
  | "缴费登记"
  | "已结案"
  | "驳回"
  | "视为撤回"
  | "放弃";

export const CASE_STAGES: CaseStage[] = [
  "待确认",
  "待撰写",
  "撰写中",
  "已提交申请",
  "已受理",
  "初审合格",
  "已公布",
  "实质审查",
  "一审",
  "二审",
  "三审及以后",
  "补正",
  "复审",
  "无效宣告",
  "授权",
  "缴费登记",
  "已结案",
  "驳回",
  "视为撤回",
  "放弃",
];

export type DocType =
  | "交底书"
  | "受理通知书"
  | "缴纳申请费通知书"
  | "收费减缴审批通知书"
  | "初步审查合格通知书"
  | "发明专利申请公布通知书"
  | "进入实质审查阶段通知书"
  | "审查意见通知书"
  | "补正通知书"
  | "视为撤回通知书"
  | "驳回决定"
  | "复审通知书"
  | "复审请求受理通知书"
  | "无效宣告请求受理通知书"
  | "无效宣告审查决定"
  | "授权通知书"
  | "办理登记手续通知书"
  | "年费缴纳通知书"
  | "权利恢复相关通知书"
  | "其他";

export const DOC_TYPES: DocType[] = [
  "交底书",
  "受理通知书",
  "缴纳申请费通知书",
  "收费减缴审批通知书",
  "初步审查合格通知书",
  "发明专利申请公布通知书",
  "进入实质审查阶段通知书",
  "审查意见通知书",
  "补正通知书",
  "视为撤回通知书",
  "驳回决定",
  "复审通知书",
  "复审请求受理通知书",
  "无效宣告请求受理通知书",
  "无效宣告审查决定",
  "授权通知书",
  "办理登记手续通知书",
  "年费缴纳通知书",
  "权利恢复相关通知书",
  "其他",
];

export type DeadlineStatus = "待处理" | "已完成" | "已超期";

export const AGENT_ROLES = ["执业代理人", "实习代理人", "代理人助理"];
export const AGENT_FIELD_PRESETS = [
  "机械",
  "电学",
  "通信",
  "计算机/软件",
  "化学",
  "生物医药",
  "材料",
  "光学",
  "外观设计",
];

export interface AgentOut {
  id: number;
  name: string;
  role: string;
  field: string | null;
  license_no: string | null;
  phone: string | null;
  email: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  case_count: number;
}

/** "张伟（实习代理人）· 机械 · 证号尾号1234" — enough to tell 同名同姓 apart. */
export function agentLabel(a: AgentOut): string {
  const parts = [a.role === "执业代理人" ? a.name : `${a.name}（${a.role}）`];
  if (a.field) parts.push(a.field);
  if (a.license_no) parts.push(`证号尾号${a.license_no.slice(-4)}`);
  if (!a.is_active) parts.push("已停用");
  return parts.join(" · ");
}

export interface CompanyOut {
  id: number;
  name: string;
  credit_code: string | null;
  contact_person: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  address: string | null;
  notes: string | null;
  created_at: string;
  case_count: number;
  pending_deadline_count: number;
}

export interface CompanyDetailOut extends CompanyOut {
  cases: CaseOut[];
}

export interface CaseOut {
  id: number;
  internal_no: string;
  company_id: number | null;
  client_name: string;
  patent_name: string;
  patent_type: PatentType;
  application_no: string | null;
  application_date: string | null;
  current_stage: CaseStage;
  agent: string | null;
  notes: string | null;
  agent_id: number | null;
  twin_case_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CaseStageEventOut {
  id: number;
  stage: CaseStage;
  changed_at: string;
  note: string | null;
  source_document_id: number | null;
  is_done: boolean;
}

export interface DocumentOut {
  id: number;
  case_id: number | null;
  original_filename: string;
  doc_type: DocType;
  doc_variant: string | null;
  issue_date: string | null;
  application_no: string | null;
  applicant_name: string | null;
  patent_name: string | null;
  patent_type: PatentType | null;
  is_confirmed: boolean;
  created_at: string;
}

export interface DeadlineOut {
  id: number;
  case_id: number;
  document_id: number | null;
  deadline_type: string;
  due_date: string;
  status: DeadlineStatus;
  completed_at: string | null;
  note: string | null;
  created_at: string;
}

export interface DeadlineWithCaseOut extends DeadlineOut {
  case_internal_no: string;
  case_client_name: string;
  case_patent_name: string;
}

export interface CaseFileOut {
  id: number;
  case_id: number;
  category: string;
  round_no: string | null;
  original_filename: string;
  note: string | null;
  uploaded_at: string;
}

export const CASE_FILE_CATEGORY_PRESETS = [
  "交底材料",
  "撰写稿",
  "补正答复",
  "初审答复",
  "实审答复",
  "复审答复",
  "其他",
];

export interface CaseDetailOut extends CaseOut {
  stage_events: CaseStageEventOut[];
  documents: DocumentOut[];
  deadlines: DeadlineOut[];
  files: CaseFileOut[];
}

export interface SuggestedDeadline {
  deadline_type: string;
  due_date: string | null;
  rule_matched: boolean;
  note: string | null;
}

export interface DocumentParseResult {
  temp_file_path: string;
  original_filename: string;
  doc_type: DocType;
  doc_variant: string | null;
  raw_text: string;
  issue_date: string | null;
  application_no: string | null;
  applicant_name: string | null;
  patent_name: string | null;
  patent_type: PatentType | null;
  application_date: string | null;
  matched_case_id: number | null;
  matched_case_internal_no: string | null;
  matched_company_id: number | null;
  matched_company_name: string | null;
  duplicate_document_id: number | null;
  duplicate_case_id: number | null;
  duplicate_case_internal_no: string | null;
  duplicate_reason: string | null;
  dispatch_no: string | null;
  suggested_deadlines: SuggestedDeadline[];
}

export interface DeadlineRuleOut {
  id: number;
  doc_type: DocType;
  doc_variant: string | null;
  patent_type: PatentType | null;
  deadline_type: string;
  period_value: number;
  period_unit: string;
  description: string | null;
  is_active: boolean;
  is_verified: boolean;
}

/**
 * Patent type from a CNIPA application number's type digit (ZC 0006-2003):
 * 5th digit since 2003 (12-digit core), 3rd digit before (8-digit core).
 * 1=发明 2=实用新型 3=外观设计 8=PCT发明 9=PCT实用新型. Mirrors
 * backend/app/services/patent_type.py.
 */
export function patentTypeFromApplicationNo(appNo: string | null | undefined): PatentType | null {
  if (!appNo) return null;
  const core = appNo
    .split(".")[0]
    .toUpperCase()
    .replace(/ZL|CN/g, "")
    .replace(/\D/g, "");
  const digit = core.length === 12 || core.length === 13 ? core[4] : core.length === 8 || core.length === 9 ? core[2] : undefined;
  const map: Record<string, PatentType> = {
    "1": "发明专利",
    "2": "实用新型",
    "3": "外观设计",
    "8": "发明专利",
    "9": "实用新型",
  };
  return digit ? map[digit] ?? null : null;
}
