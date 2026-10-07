import { useEffect, useState } from "react";
import { Button, Input, Modal, Select, Space, Table, Tag, Typography, message } from "antd";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { CASE_STAGES, type CaseOut } from "../types";

const { Title } = Typography;

export default function CaseList() {
  const [cases, setCases] = useState<CaseOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState<string | undefined>();
  const [clientName, setClientName] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const load = () => {
    setLoading(true);
    api
      .get<CaseOut[]>("/cases", {
        params: {
          stage: stage || undefined,
          client_name: clientName || undefined,
        },
      })
      .then((res) => {
        setCases(res.data);
        setSelectedIds([]);
      })
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [stage]);

  const deleteOne = (caseRow: CaseOut) => {
    Modal.confirm({
      title: `确认删除案件「${caseRow.internal_no} · ${caseRow.patent_name}」？`,
      content: "此操作不可撤销：会一并删除该案件的所有阶段记录、文书、期限、案件资料文件。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      onOk: () =>
        api
          .delete(`/cases/${caseRow.id}`)
          .then(() => {
            message.success("已删除");
            load();
          })
          .catch((err) => message.error(err.message)),
    });
  };

  const deleteSelected = () => {
    Modal.confirm({
      title: `确认删除选中的 ${selectedIds.length} 个案件？`,
      content: "此操作不可撤销：会一并删除这些案件的所有阶段记录、文书、期限、案件资料文件。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      onOk: async () => {
        for (const id of selectedIds) {
          try {
            // eslint-disable-next-line no-await-in-loop
            await api.delete(`/cases/${id}`);
          } catch (err) {
            message.error(`删除案件 ${id} 失败：${(err as Error).message}`);
          }
        }
        message.success("已删除选中的案件");
        load();
      },
    });
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, width: "100%", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>
          案件管理
        </Title>
        <Link to="/cases/new">
          <Button type="primary">新建案件（交底书录入）</Button>
        </Link>
      </Space>
      <Space style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="按阶段筛选"
          style={{ width: 160 }}
          value={stage}
          onChange={setStage}
          options={CASE_STAGES.map((s) => ({ label: s, value: s }))}
        />
        <Input.Search
          placeholder="按客户名称搜索"
          style={{ width: 220 }}
          value={clientName}
          onChange={(e) => setClientName(e.target.value)}
          onSearch={load}
        />
        {selectedIds.length > 0 && (
          <Button danger onClick={deleteSelected}>
            删除选中的 {selectedIds.length} 个案件
          </Button>
        )}
      </Space>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={cases}
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as number[]),
        }}
        columns={[
          {
            title: "内部编号",
            dataIndex: "internal_no",
            render: (v: string, row) => <Link to={`/cases/${row.id}`}>{v}</Link>,
          },
          { title: "客户名称", dataIndex: "client_name" },
          { title: "专利名称", dataIndex: "patent_name" },
          { title: "专利类型", dataIndex: "patent_type" },
          { title: "申请号", dataIndex: "application_no" },
          {
            title: "当前阶段",
            dataIndex: "current_stage",
            render: (s: string) => <Tag>{s}</Tag>,
          },
          { title: "承办人", dataIndex: "agent" },
          {
            title: "操作",
            render: (_: unknown, row) => <a onClick={() => deleteOne(row)}>删除</a>,
          },
        ]}
      />
    </div>
  );
}
