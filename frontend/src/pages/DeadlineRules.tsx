import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Typography,
  message,
} from "antd";
import { api } from "../api/client";
import { DOC_TYPES, type DeadlineRuleOut } from "../types";

const { Title } = Typography;

export default function DeadlineRules() {
  const [rules, setRules] = useState<DeadlineRuleOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<DeadlineRuleOut | null>(null);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    api
      .get<DeadlineRuleOut[]>("/deadline-rules")
      .then((res) => setRules(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggleField = (rule: DeadlineRuleOut, field: "is_active" | "is_verified", value: boolean) => {
    api
      .patch(`/deadline-rules/${rule.id}`, { [field]: value })
      .then(() => load())
      .catch((err) => message.error(err.message));
  };

  const openEdit = (rule: DeadlineRuleOut | null) => {
    setEditing(rule);
    form.resetFields();
    if (rule) form.setFieldsValue(rule);
    setModalOpen(true);
  };

  const remove = (rule: DeadlineRuleOut) => {
    Modal.confirm({
      title: `确认删除规则「${rule.deadline_type}」？`,
      onOk: () =>
        api
          .delete(`/deadline-rules/${rule.id}`)
          .then(() => load())
          .catch((err) => message.error(err.message)),
    });
  };

  const submit = (values: Record<string, unknown>) => {
    const req = editing
      ? api.patch(`/deadline-rules/${editing.id}`, values)
      : api.post("/deadline-rules", { ...values, is_verified: false, is_active: true });
    req
      .then(() => {
        message.success("已保存");
        setModalOpen(false);
        load();
      })
      .catch((err) => message.error(err.message));
  };

  return (
    <div>
      <Title level={3}>期限规则管理</Title>
      <Alert
        style={{ marginBottom: 16 }}
        type="error"
        showIcon
        message="使用前必读"
        description="以下期限规则由系统预置，仅供参考，未必符合现行专利法及实施细则的最新规定（不同文书细分类型、发明/实用新型/外观设计、形式审查/实质审查阶段的法定期限均可能不同）。请逐条核对后将「已核对」标记为是，否则请以官方文书载明的期限为准，不要仅依赖本系统的自动计算结果。"
      />
      <Button type="primary" style={{ marginBottom: 16 }} onClick={() => openEdit(null)}>
        新增规则
      </Button>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={rules}
        columns={[
          { title: "文书类型", dataIndex: "doc_type" },
          { title: "细分", dataIndex: "doc_variant", render: (v) => v ?? "（不限）" },
          { title: "专利类型", dataIndex: "patent_type", render: (v) => v ?? "（不限）" },
          { title: "期限类型", dataIndex: "deadline_type" },
          {
            title: "期限",
            render: (_: unknown, r) => `${r.period_value} ${r.period_unit}`,
          },
          { title: "说明", dataIndex: "description", ellipsis: true },
          {
            title: "已核对",
            dataIndex: "is_verified",
            render: (v: boolean, r) => (
              <Switch checked={v} onChange={(val) => toggleField(r, "is_verified", val)} />
            ),
          },
          {
            title: "启用",
            dataIndex: "is_active",
            render: (v: boolean, r) => (
              <Switch checked={v} onChange={(val) => toggleField(r, "is_active", val)} />
            ),
          },
          {
            title: "操作",
            render: (_: unknown, r) => (
              <Space>
                <a onClick={() => openEdit(r)}>编辑</a>
                <a onClick={() => remove(r)}>删除</a>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editing ? "编辑期限规则" : "新增期限规则"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={submit}>
          <Form.Item name="doc_type" label="文书类型" rules={[{ required: true }]}>
            <Select disabled={!!editing} options={DOC_TYPES.map((t) => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="doc_variant" label="细分（留空表示不限，如：第一次）">
            <Input />
          </Form.Item>
          <Form.Item name="patent_type" label="专利类型（留空表示不限）">
            <Select
              allowClear
              options={[
                { label: "发明专利", value: "发明专利" },
                { label: "实用新型", value: "实用新型" },
                { label: "外观设计", value: "外观设计" },
              ]}
            />
          </Form.Item>
          <Form.Item name="deadline_type" label="期限类型名称" rules={[{ required: true }]}>
            <Input placeholder="如：第一次审查意见通知书答复期限" />
          </Form.Item>
          <Space>
            <Form.Item name="period_value" label="期限数值" rules={[{ required: true }]}>
              <InputNumber min={1} />
            </Form.Item>
            <Form.Item name="period_unit" label="单位" rules={[{ required: true }]}>
              <Select options={[{ label: "天", value: "天" }, { label: "月", value: "月" }]} />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="说明">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
