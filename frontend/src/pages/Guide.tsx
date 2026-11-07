import { Alert, Button, Steps, Typography } from "antd";
import { Link } from "react-router-dom";
import { START_TOUR_EVENT } from "../components/OnboardingTour";

const { Title, Paragraph } = Typography;

const STEPS = [
  {
    title: <Link to="/settings">设置数据存储位置</Link>,
    description: "选一个会定期备份的目录存放数据库和官文。迁移会整体移动现有数据，迁移后需重启程序。",
  },
  {
    title: <Link to="/agents">添加代理人</Link>,
    description: "录入所里的代理人（姓名、身份、技术领域，执业证号选填）。离职的停用即可，历史案件保留。",
  },
  {
    title: <Link to="/companies">建立企业（可选）</Link>,
    description: "可以先手动建客户企业；不建也行，录入官文时会按申请人自动创建。",
  },
  {
    title: <Link to="/upload">批量录入官文</Link>,
    description:
      "从专利业务办理系统下载通知书 PDF 放进一个文件夹，在「文书录入」点「选择文件夹」→「解析全部」→ 核对 →「确认保存全部」。受理通知书会自动建案；能按申请号匹配的归入已有案件；重复的通知书自动跳过。",
  },
  {
    title: <Link to="/cases">管理案件</Link>,
    description:
      "阶段由通知书自动推进，详情页可看流程进度、文书、期限，可设置承办人、更换企业、关联一案双申。交底阶段的新案可在「新建案件」手动录入。",
  },
  {
    title: <Link to="/">每天查看期限看板</Link>,
    description: "按到期日处理期限，完成后标记「已完成」。",
  },
  {
    title: <Link to="/deadline-rules">核对期限规则</Link>,
    description: "内置规则默认未核对，请逐条确认；通知书上写明的期限（如缴费截止日、答复期限）会优先采用。",
  },
];

export default function Guide() {
  return (
    <div style={{ maxWidth: 760 }}>
      <Title level={3}>使用指南</Title>
      <Paragraph type="secondary">第一次使用，建议按下面的顺序完成设置。点击标题可直接跳转。</Paragraph>
      <Button
        type="primary"
        style={{ marginBottom: 24 }}
        onClick={() => window.dispatchEvent(new Event(START_TOUR_EVENT))}
      >
        重新播放新手引导
      </Button>
      <Steps direction="vertical" current={-1} items={STEPS} />
      <Alert
        style={{ marginTop: 16 }}
        type="info"
        showIcon
        message="数据只保存在本机"
        description="案件和官文都存放在「设置」里显示的目录中，程序不会上传任何数据。请定期备份该目录。"
      />
    </div>
  );
}
