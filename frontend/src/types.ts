export type PatentType = "发明专利" | "实用新型" | "外观设计" | "未知";

export type CaseStage =
  | "待确认"
  | "待撰写"
  | "撰写中"
  | "已提交申请"
  | "已受理"
  | "初审阶段"
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
  "初审阶段",
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
  | "初步审查合格通知书"
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
  "初步审查合格通知书",
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

export interface CaseOut {
  id: number;
  internal_no: string;
  client_name: string;
  patent_name: string;
  patent_type: PatentType;
  application_no: string | null;
  application_date: string | null;
  current_stage: CaseStage;
  agent: string | null;
  notes: string | null;
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
  matched_case_id: number | null;
  matched_case_internal_no: string | null;
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
