import { useEffect, useState } from "react";
import { Alert, Table, Tag, Typography, message } from "antd";
import { Link } from "react-router-dom";
import dayjs from "dayjs";
import { api } from "../api/client";
import type { DeadlineWithCaseOut } from "../types";

const { Title } = Typography;

function statusColor(status: string, dueDate: string) {
  if (status === "已完成") return "default";
  const days = dayjs(dueDate).diff(dayjs().startOf("day"), "day");
  if (days < 0) return "red";
  if (days <= 7) return "orange";
  return "green";
}

export default function Dashboard() {
  const [deadlines, setDeadlines] = useState<DeadlineWithCaseOut[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .get<DeadlineWithCaseOut[]>("/deadlines")
      .then((res) => setDeadlines(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const markCompleted = (id: number) => {
    api
      .patch(`/deadlines/${id}`, { status: "已完成" })
      .then(() => {
        message.success("已标记为完成");
        load();
      })
      .catch((err) => message.error(err.message));
  };

  return (
    <div>
      <Title level={3}>期限看板</Title>
      <Alert
        style={{ marginBottom: 16 }}
        type="warning"
        showIcon
        message="法定期限提示"
        description="系统自动计算的期限依赖「期限规则管理」页面中的规则，规则默认标记为未核对。请在正式依赖本系统前逐条核对法定期限是否准确。"
      />
      <Table
        rowKey="id"
        loading={loading}
        dataSource={deadlines}
        columns={[
          {
            title: "案件",
            dataIndex: "case_internal_no",
            render: (_: string, row) => (
              <Link to={`/cases/${row.case_id}`}>
                {row.case_internal_no} · {row.case_client_name}
              </Link>
            ),
          },
          { title: "专利名称", dataIndex: "case_patent_name" },
          { title: "期限类型", dataIndex: "deadline_type" },
          {
            title: "到期日",
            dataIndex: "due_date",
            sorter: (a, b) => a.due_date.localeCompare(b.due_date),
            defaultSortOrder: "ascend",
            render: (due_date: string, row) => (
              <Tag color={statusColor(row.status, due_date)}>{due_date}</Tag>
            ),
          },
          { title: "状态", dataIndex: "status" },
          {
            title: "操作",
            render: (_: unknown, row) =>
              row.status !== "已完成" ? (
                <a onClick={() => markCompleted(row.id)}>标记完成</a>
              ) : null,
          },
        ]}
      />
    </div>
  );
}
