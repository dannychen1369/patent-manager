import { useEffect, useState } from "react";
import { Button, Input, Modal, Space, Table, Tag, Typography, message } from "antd";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import CompanyFormModal from "../components/CompanyFormModal";
import type { CompanyOut } from "../types";

const { Title } = Typography;

export default function CompanyList() {
  const [companies, setCompanies] = useState<CompanyOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [keyword, setKeyword] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<CompanyOut | null>(null);

  const load = () => {
    setLoading(true);
    api
      .get<CompanyOut[]>("/companies", { params: { keyword: keyword || undefined } })
      .then((res) => setCompanies(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const deleteOne = (row: CompanyOut) => {
    Modal.confirm({
      title: `确认删除企业「${row.name}」？`,
      content: "只能删除名下没有案件的企业。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      onOk: () =>
        api
          .delete(`/companies/${row.id}`)
          .then(() => {
            message.success("已删除");
            load();
          })
          .catch((err) => message.error(err.message)),
    });
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, width: "100%", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>
          企业管理
        </Title>
        <Button
          type="primary"
          onClick={() => {
            setEditing(null);
            setModalOpen(true);
          }}
        >
          新建企业
        </Button>
      </Space>
      <Input.Search
        placeholder="按企业名称搜索"
        style={{ width: 260, marginBottom: 16 }}
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        onSearch={load}
        allowClear
      />
      <Table
        rowKey="id"
        loading={loading}
        dataSource={companies}
        columns={[
          {
            title: "企业名称",
            dataIndex: "name",
            render: (v: string, row) => <Link to={`/companies/${row.id}`}>{v}</Link>,
          },
          { title: "联系人", dataIndex: "contact_person" },
          { title: "联系电话", dataIndex: "contact_phone" },
          { title: "案件数", dataIndex: "case_count", sorter: (a, b) => a.case_count - b.case_count },
          {
            title: "待处理期限",
            dataIndex: "pending_deadline_count",
            render: (n: number) => (n > 0 ? <Tag color="orange">{n}</Tag> : 0),
          },
          {
            title: "操作",
            render: (_: unknown, row) => (
              <Space>
                <a
                  onClick={() => {
                    setEditing(row);
                    setModalOpen(true);
                  }}
                >
                  编辑
                </a>
                <a onClick={() => deleteOne(row)}>删除</a>
              </Space>
            ),
          },
        ]}
      />
      <CompanyFormModal
        open={modalOpen}
        company={editing}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          setModalOpen(false);
          load();
        }}
      />
    </div>
  );
}
