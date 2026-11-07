import { useEffect, useState } from "react";
import { Button, Descriptions, Space, Table, Tag, Typography, message } from "antd";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import CompanyFormModal from "../components/CompanyFormModal";
import type { CaseStage, CompanyDetailOut } from "../types";

const { Title } = Typography;

export default function CompanyDetail() {
  const { id } = useParams();
  const [detail, setDetail] = useState<CompanyDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get<CompanyDetailOut>(`/companies/${id}`)
      .then((res) => setDetail(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  if (loading || !detail) return <div>加载中...</div>;

  // Count by stage so the header gives a quick picture of where this
  // company's portfolio stands.
  const stageCounts = detail.cases.reduce<Record<string, number>>((acc, c) => {
    acc[c.current_stage] = (acc[c.current_stage] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          {detail.name}
        </Title>
        <Space>
          <Link to={`/cases/new?company_id=${detail.id}`}>
            <Button type="primary">新建案件</Button>
          </Link>
          <Link to={`/upload?company_id=${detail.id}`}>
            <Button>批量录入文书</Button>
          </Link>
          <Button onClick={() => setEditOpen(true)}>编辑企业信息</Button>
        </Space>
      </Space>

      <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
        <Descriptions.Item label="统一社会信用代码">{detail.credit_code ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="联系人">{detail.contact_person ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="联系电话">{detail.contact_phone ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="邮箱">{detail.contact_email ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="地址" span={2}>
          {detail.address ?? "-"}
        </Descriptions.Item>
        <Descriptions.Item label="案件概况" span={2}>
          共 {detail.case_count} 件，待处理期限 {detail.pending_deadline_count} 个
          <span style={{ marginLeft: 12 }}>
            {Object.entries(stageCounts).map(([stage, n]) => (
              <Tag key={stage}>
                {stage} {n}
              </Tag>
            ))}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="备注" span={2}>
          {detail.notes ?? "-"}
        </Descriptions.Item>
      </Descriptions>

      <Title level={4}>名下案件</Title>
      <Table
        rowKey="id"
        dataSource={detail.cases}
        columns={[
          {
            title: "内部编号",
            dataIndex: "internal_no",
            render: (v: string, row) => <Link to={`/cases/${row.id}`}>{v}</Link>,
          },
          { title: "专利名称", dataIndex: "patent_name" },
          { title: "专利类型", dataIndex: "patent_type" },
          { title: "申请号", dataIndex: "application_no" },
          { title: "申请日", dataIndex: "application_date" },
          {
            title: "当前阶段",
            dataIndex: "current_stage",
            render: (s: CaseStage) => <Tag>{s}</Tag>,
          },
          { title: "承办人", dataIndex: "agent" },
        ]}
      />

      <CompanyFormModal
        open={editOpen}
        company={detail}
        onClose={() => setEditOpen(false)}
        onSaved={() => {
          setEditOpen(false);
          load();
        }}
      />
    </div>
  );
}
