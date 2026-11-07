import { useEffect } from "react";
import { Button, Form, Input, Select, Typography, message } from "antd";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import AgentSelect from "../components/AgentSelect";
import CompanyPicker from "../components/CompanyPicker";
import type { CompanyOut } from "../types";

const { Title } = Typography;

export default function NewCase() {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [searchParams] = useSearchParams();
  const presetCompanyId = searchParams.get("company_id");

  useEffect(() => {
    if (!presetCompanyId) return;
    api
      .get<CompanyOut>(`/companies/${presetCompanyId}`)
      .then((res) => form.setFieldsValue({ client_name: res.data.name }));
  }, [presetCompanyId, form]);

  const onFinish = (values: Record<string, unknown>) => {
    api
      .post("/cases", values)
      .then((res) => {
        message.success("案件已创建，状态为「待确认」");
        navigate(`/cases/${res.data.id}`);
      })
      .catch((err) => message.error(err.message));
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <Title level={3}>新建案件（交底书录入）</Title>
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item
          name="client_name"
          label="所属企业"
          rules={[{ required: true, message: "请选择或输入所属企业" }]}
          extra="输入的企业不存在时会自动新建"
        >
          <CompanyPicker />
        </Form.Item>
        <Form.Item name="patent_name" label="专利名称" rules={[{ required: true }]}>
          <Input placeholder="发明创造名称" />
        </Form.Item>
        <Form.Item name="patent_type" label="专利类型" initialValue="未知">
          <Select
            options={[
              { label: "发明专利", value: "发明专利" },
              { label: "实用新型", value: "实用新型" },
              { label: "外观设计", value: "外观设计" },
              { label: "未知", value: "未知" },
            ]}
          />
        </Form.Item>
        <Form.Item name="agent_id" label="承办人（代理人）">
          <AgentSelect />
        </Form.Item>
        <Form.Item name="notes" label="交底备注">
          <Input.TextArea rows={4} placeholder="交底书内容摘要 / 技术方案要点等" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">
            创建案件
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
}
