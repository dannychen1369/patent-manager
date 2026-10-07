import { Button, Form, Input, Select, Typography, message } from "antd";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

const { Title } = Typography;

export default function NewCase() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

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
        <Form.Item name="client_name" label="客户名称" rules={[{ required: true }]}>
          <Input placeholder="客户/申请人名称" />
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
        <Form.Item name="agent" label="承办人">
          <Input />
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
