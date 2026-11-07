import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  FolderOpenOutlined,
  UploadOutlined,
  SettingOutlined,
  ToolOutlined,
  BankOutlined,
  TeamOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import CaseList from "./pages/CaseList";
import CompanyList from "./pages/CompanyList";
import CompanyDetail from "./pages/CompanyDetail";
import AgentList from "./pages/AgentList";
import CaseDetail from "./pages/CaseDetail";
import NewCase from "./pages/NewCase";
import UploadDocument from "./pages/UploadDocument";
import DeadlineRules from "./pages/DeadlineRules";
import Settings from "./pages/Settings";
import Guide from "./pages/Guide";
import OnboardingTour from "./components/OnboardingTour";

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: <Link id="nav-dashboard" to="/">期限看板</Link> },
  { key: "/companies", icon: <BankOutlined />, label: <Link id="nav-companies" to="/companies">企业管理</Link> },
  { key: "/cases", icon: <FolderOpenOutlined />, label: <Link id="nav-cases" to="/cases">案件管理</Link> },
  { key: "/upload", icon: <UploadOutlined />, label: <Link id="nav-upload" to="/upload">文书录入</Link> },
  {
    key: "/deadline-rules",
    icon: <SettingOutlined />,
    label: <Link id="nav-rules" to="/deadline-rules">期限规则管理</Link>,
  },
  { key: "/agents", icon: <TeamOutlined />, label: <Link id="nav-agents" to="/agents">代理人名单</Link> },
  { key: "/settings", icon: <ToolOutlined />, label: <Link id="nav-settings" to="/settings">设置</Link> },
  {
    key: "/guide",
    icon: <QuestionCircleOutlined />,
    label: <Link id="nav-guide" to="/guide">使用指南</Link>,
  },
];

function App() {
  const location = useLocation();
  const selectedKey =
    menuItems
      .map((i) => i.key)
      .filter((k) => k !== "/" && location.pathname.startsWith(k))
      .sort((a, b) => b.length - a.length)[0] ??
    (location.pathname === "/" ? "/" : "");

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <OnboardingTour />
      <Header style={{ display: "flex", alignItems: "center" }}>
        <div style={{ color: "#fff", fontSize: 18, fontWeight: 600, marginRight: 32 }}>
          专利管理系统
        </div>
      </Header>
      <Layout>
        <Sider width={200} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={menuItems}
            style={{ height: "100%", borderRight: 0 }}
          />
        </Sider>
        <Layout style={{ padding: 24 }}>
          <Content style={{ background: "#fff", padding: 24, margin: 0, minHeight: 280 }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/companies" element={<CompanyList />} />
              <Route path="/companies/:id" element={<CompanyDetail />} />
              <Route path="/cases" element={<CaseList />} />
              <Route path="/cases/new" element={<NewCase />} />
              <Route path="/cases/:id" element={<CaseDetail />} />
              <Route path="/upload" element={<UploadDocument />} />
              <Route path="/deadline-rules" element={<DeadlineRules />} />
              <Route path="/agents" element={<AgentList />} />
              <Route path="/guide" element={<Guide />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
}

export default App;
