import { useEffect, useState } from "react";
import { Tour, type TourProps } from "antd";
import { api } from "../api/client";

/** Fired by the 使用指南 page to replay the tour. */
export const START_TOUR_EVENT = "pm-start-tour";

// Highlight the whole menu row, not just the link text inside it.
const nav = (id: string) => () =>
  (document.getElementById(id)?.closest("li") as HTMLElement | null) ?? document.body;

const STEPS: TourProps["steps"] = [
  {
    title: "欢迎使用专利管理系统",
    description:
      "下面用一分钟带你认识主要功能。所有数据都只保存在这台电脑上，不会上传。随时可以点「下一步」或右上角关闭。",
  },
  {
    title: "第 1 步：设置数据存储位置",
    description: "案件数据库、官文和资料文件存放的目录。建议改到会定期备份的磁盘或同步盘。",
    target: nav("nav-settings"),
    placement: "right",
  },
  {
    title: "第 2 步：添加代理人",
    description:
      "把所里的代理人加进名单，之后案件的承办人从名单里选。同名同姓可用技术领域、身份（执业/实习）区分，执业证号选填。",
    target: nav("nav-agents"),
    placement: "right",
  },
  {
    title: "第 3 步：企业管理",
    description: "每个客户企业名下挂着它的全部案件。也可以不手动建：录入官文时会按申请人自动建企业。",
    target: nav("nav-companies"),
    placement: "right",
  },
  {
    title: "第 4 步：录入官方文书",
    description:
      "点「选择文件夹」可以一次导入整个文件夹的官文（PDF/图片）。系统自动识别文书类型、申请号和期限；收到受理通知书会自动建案，重复的通知书会提示跳过。",
    target: nav("nav-upload"),
    placement: "right",
  },
  {
    title: "第 5 步：案件管理",
    description:
      "案件阶段由上传的通知书自动决定（以发文日最晚的为准），详情页按专利类型显示流程进度；一案双申会自动关联。",
    target: nav("nav-cases"),
    placement: "right",
  },
  {
    title: "第 6 步：每天看期限看板",
    description: "所有待处理期限按到期日排列，临近和超期的会醒目标出。",
    target: nav("nav-dashboard"),
    placement: "right",
  },
  {
    title: "第 7 步：核对期限规则",
    description:
      "系统内置的法定期限规则默认「未核对」。请在这里逐条确认后再依赖自动计算的期限；通知书上写明的期限会优先采用。",
    target: nav("nav-rules"),
    placement: "right",
  },
  {
    title: "完成",
    description: "以后想再看一遍，点左侧菜单最下方的「使用指南」。",
    target: nav("nav-guide"),
    placement: "right",
  },
];

export default function OnboardingTour() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    api
      .get<{ onboarding_done: boolean }>("/settings")
      .then((res) => {
        if (!res.data.onboarding_done) setOpen(true);
      })
      .catch(() => undefined);

    const replay = () => {
      setCurrent(0);
      setOpen(true);
    };
    window.addEventListener(START_TOUR_EVENT, replay);
    return () => window.removeEventListener(START_TOUR_EVENT, replay);
  }, []);

  const close = () => {
    setOpen(false);
    api.post("/settings/onboarding", { done: true }).catch(() => undefined);
  };

  return (
    <Tour
      open={open}
      current={current}
      onChange={setCurrent}
      onClose={close}
      onFinish={close}
      steps={STEPS}
    />
  );
}
