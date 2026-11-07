import { Steps } from "antd";
import type { CaseStage, CaseStageEventOut, PatentType } from "../types";

// Prosecution flow per patent type (CNIPA): an invention goes through
// publication and substantive examination; utility models and designs are
// granted after preliminary examination only.
const INVENTION_STEPS = ["撰写提交", "受理", "初审合格", "公布", "实质审查", "授权", "登记"];
const SIMPLE_STEPS = ["撰写提交", "受理", "初步审查", "授权", "登记"];

const TERMINAL: Partial<Record<CaseStage, string>> = {
  驳回: "已驳回",
  视为撤回: "视为撤回",
  放弃: "已放弃",
  复审: "复审中",
  无效宣告: "无效宣告中",
};

function stepIndex(stage: CaseStage, invention: boolean): number | null {
  const pre: CaseStage[] = ["待确认", "待撰写", "撰写中", "已提交申请"];
  if (pre.includes(stage)) return 0;
  if (stage === "已受理") return 1;
  if (invention) {
    switch (stage) {
      case "补正":
        return 2; // 初审 corrections happen before 初审合格
      case "初审合格":
        return 2;
      case "已公布":
        return 3;
      case "实质审查":
      case "一审":
      case "二审":
      case "三审及以后":
        return 4;
      case "授权":
        return 5;
      case "缴费登记":
      case "已结案":
        return 6;
      default:
        return null;
    }
  }
  switch (stage) {
    case "补正":
    case "一审":
    case "二审":
    case "三审及以后":
    case "初审合格":
      return 2;
    case "授权":
      return 3;
    case "缴费登记":
    case "已结案":
      return 4;
    default:
      return null;
  }
}

interface Props {
  patentType: PatentType;
  currentStage: CaseStage;
  events: CaseStageEventOut[];
}

export default function CaseFlowSteps({ patentType, currentStage, events }: Props) {
  if (patentType === "未知") return null;
  const invention = patentType === "发明专利";
  const labels = invention ? INVENTION_STEPS : SIMPLE_STEPS;

  let current = stepIndex(currentStage, invention);
  const terminal = TERMINAL[currentStage];
  if (current === null) {
    // 驳回 / 复审 etc.: show the error on the step the case had reached.
    const reached = [...events]
      .reverse()
      .map((e) => stepIndex(e.stage, invention))
      .find((i) => i !== null);
    current = reached ?? 0;
  }
  const finished = currentStage === "已结案";

  return (
    <Steps
      size="small"
      style={{ marginBottom: 24 }}
      current={current}
      status={terminal ? "error" : finished ? "finish" : "process"}
      items={labels.map((title, i) => ({
        title,
        description:
          i === current && terminal
            ? terminal
            : i === current && !finished && currentStage !== title
              ? currentStage
              : undefined,
      }))}
    />
  );
}
