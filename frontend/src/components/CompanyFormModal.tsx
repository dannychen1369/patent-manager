import { useEffect, useState } from "react";
import { Form, Input, Modal, message } from "antd";
import { api } from "../api/client";
import type { CompanyOut } from "../types";

interface Props {
  open: boolean;
  /** When given, the modal edits this company; otherwise it creates one. */
  company?: CompanyOut | null;
  onClose: () => void;
  onSaved: (company: CompanyOut) => void;
}

export default function CompanyFormModal({ open, company, onClose, onSaved }: Props) {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    form.resetFields();
    if (company) form.setFieldsValue(company);
  }, [open, company, form]);

  const submit = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const res = company
        ? await api.patch<CompanyOut>(`/companies/${company.id}`, values)
        : await api.post<CompanyOut>("/companies", values);
      message.success(company ? "企业信息已更新" : "企业已创建");
      onSaved(res.data);
    } catch (err) {
      message.error((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={company ? "编辑企业" : "新建企业"}
      open={open}
      onCancel={onClose}
      onOk={submit}
      confirmLoading={saving}
      okText="保存"
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="name" label="企业名称" rules={[{ required: true, message: "请填写企业名称" }]}>
          <Input placeholder="与官方文书上的申请人名称保持一致，便于自动归档" />
        </Form.Item>
        <Form.Item name="credit_code" label="统一社会信用代码">
          <Input />
        </Form.Item>
        <Form.Item name="contact_person" label="联系人">
          <Input />
        </Form.Item>
        <Form.Item name="contact_phone" label="联系电话">
          <Input />
        </Form.Item>
        <Form.Item name="contact_email" label="邮箱">
          <Input />
        </Form.Item>
        <Form.Item name="address" label="地址">
          <Input />
        </Form.Item>
        <Form.Item name="notes" label="备注">
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  );
}
