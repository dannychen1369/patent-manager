import { useEffect, useState } from "react";
import {
  AutoComplete,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { api } from "../api/client";
import { AGENT_FIELD_PRESETS, AGENT_ROLES, type AgentOut } from "../types";

const { Title, Paragraph } = Typography;

export default function AgentList() {
  const [agents, setAgents] = useState<AgentOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<AgentOut | null>(null);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    api
      .get<AgentOut[]>("/agents", { params: { include_inactive: true } })
      .then((res) => setAgents(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const openModal = (agent: AgentOut | null) => {
    setEditing(agent);
    form.resetFields();
    form.setFieldsValue(agent ?? { role: "执业代理人", is_active: true });
    setModalOpen(true);
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing) await api.patch(`/agents/${editing.id}`, values);
      else await api.post("/agents", values);
      message.success("已保存");
      setModalOpen(false);
      load();
    } catch (err) {
      message.error((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = (agent: AgentOut) =>
    api
      .patch(`/agents/${agent.id}`, { is_active: !agent.is_active })
      .then(load)
      .catch((err) => message.error(err.message));

  const remove = (agent: AgentOut) =>
    Modal.confirm({
      title: `删除代理人「${agent.name}」？`,
      content: "只能删除没有承办案件的代理人；已离职的请用「停用」。",
      okText: "删除",
      okButtonProps: { danger: true },
      onOk: () =>
        api
          .delete(`/agents/${agent.id}`)
          .then(() => {
            message.success("已删除");
            load();
          })
          .catch((err) => message.error(err.message)),
    });

  // Names that appear more than once: highlight what tells them apart.
  const nameCounts = agents.reduce<Record<string, number>>((acc, a) => {
    acc[a.name] = (acc[a.name] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <Space style={{ marginBottom: 8, width: "100%", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>
          代理人名单
        </Title>
        <Button type="primary" onClick={() => openModal(null)}>
          添加代理人
        </Button>
      </Space>
      <Paragraph type="secondary">
        案件的承办人从这里选择。同名同姓的用技术领域、身份或执业证号区分（实习代理人可不填执业证号）；已离职的请停用，历史案件仍保留其记录。
      </Paragraph>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={agents}
        rowClassName={(a) => (a.is_active ? "" : "ant-table-row-disabled")}
        columns={[
          {
            title: "姓名",
            dataIndex: "name",
            render: (v: string, a) => (
              <Space size={4}>
                <span style={{ opacity: a.is_active ? 1 : 0.5 }}>{v}</span>
                {nameCounts[v] > 1 && <Tag color="orange">同名</Tag>}
              </Space>
            ),
          },
          {
            title: "身份",
            dataIndex: "role",
            render: (r: string) => <Tag color={r === "执业代理人" ? "blue" : "default"}>{r}</Tag>,
          },
          { title: "技术领域", dataIndex: "field" },
          { title: "执业证号", dataIndex: "license_no" },
          { title: "电话", dataIndex: "phone" },
          { title: "承办案件", dataIndex: "case_count" },
          {
            title: "状态",
            render: (_: unknown, a) => (a.is_active ? <Tag color="green">在职</Tag> : <Tag>已停用</Tag>),
          },
          {
            title: "操作",
            render: (_: unknown, a) => (
              <Space>
                <a onClick={() => openModal(a)}>编辑</a>
                <a onClick={() => toggleActive(a)}>{a.is_active ? "停用" : "启用"}</a>
                <a onClick={() => remove(a)}>删除</a>
              </Space>
            ),
          },
        ]}
      />
      <Modal
        title={editing ? "编辑代理人" : "添加代理人"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={save}
        confirmLoading={saving}
        okText="保存"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: "请填写姓名" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="身份">
            <Select options={AGENT_ROLES.map((r) => ({ label: r, value: r }))} />
          </Form.Item>
          <Form.Item name="field" label="技术领域" extra="同名同姓时用于区分，可选列表或直接输入">
            <AutoComplete
              allowClear
              options={AGENT_FIELD_PRESETS.map((f) => ({ value: f }))}
              filterOption={(input, option) => (option?.value ?? "").includes(input)}
            />
          </Form.Item>
          <Form.Item name="license_no" label="执业证号" extra="选填，实习代理人可不填">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="电话">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_active" label="在职" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
