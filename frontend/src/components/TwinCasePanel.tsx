import { useEffect, useState } from "react";
import { Alert, Button, Modal, Space, Table, Tag, Typography, message } from "antd";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { CaseDetailOut, CaseOut } from "../types";

const { Text } = Typography;

interface Props {
  detail: CaseDetailOut;
  onChanged: () => void;
}

/** 一案双申: link this case with its same-day invention / utility-model counterpart. */
export default function TwinCasePanel({ detail, onChanged }: Props) {
  const [twin, setTwin] = useState<CaseOut | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [candidates, setCandidates] = useState<CaseOut[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);

  const canHaveTwin = detail.patent_type === "发明专利" || detail.patent_type === "实用新型";

  useEffect(() => {
    if (!detail.twin_case_id) {
      setTwin(null);
      return;
    }
    api
      .get<CaseOut>(`/cases/${detail.twin_case_id}`)
      .then((res) => setTwin(res.data))
      .catch(() => setTwin(null));
  }, [detail.twin_case_id]);

  if (!canHaveTwin) return null;

  const openPicker = () => {
    setPickerOpen(true);
    setLoadingCandidates(true);
    api
      .get<CaseOut[]>(`/cases/${detail.id}/twin-candidates`)
      .then((res) => setCandidates(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoadingCandidates(false));
  };

  const link = (twinId: number) =>
    api
      .post(`/cases/${detail.id}/twin`, { twin_case_id: twinId })
      .then(() => {
        message.success("已关联为双申");
        setPickerOpen(false);
        onChanged();
      })
      .catch((err) => message.error(err.message));

  const unlink = () =>
    Modal.confirm({
      title: "取消双申关联？",
      okText: "取消关联",
      onOk: () =>
        api
          .delete(`/cases/${detail.id}/twin`)
          .then(() => {
            message.success("已取消关联");
            onChanged();
          })
          .catch((err) => message.error(err.message)),
    });

  const isInvention = detail.patent_type === "发明专利";
  const invention = isInvention ? detail : twin;
  const utility = isInvention ? twin : detail;

  return (
    <div style={{ marginBottom: 24 }}>
      {twin ? (
        <Alert
          type="info"
          showIcon
          message={
            <Space wrap>
              <Tag color="purple">一案双申</Tag>
              <span>
                同日{isInvention ? "实用新型" : "发明"}：
                <Link to={`/cases/${twin.id}`}>{twin.internal_no}</Link>
              </span>
              <Text type="secondary">{twin.application_no ?? "（无申请号）"}</Text>
              <Tag>{twin.current_stage}</Tag>
              <a onClick={unlink}>取消关联</a>
            </Space>
          }
          description={
            <>
              发明（{invention?.current_stage}）授权前，审查员会通知声明放弃实用新型专利权；
              届时实用新型（{utility?.current_stage}）的专利权必须尚未终止，请注意按时缴纳实用新型年费、不要提前放弃。
            </>
          }
        />
      ) : (
        <Space>
          <Text type="secondary">一案双申：未关联</Text>
          <Button size="small" onClick={openPicker}>
            查找同日{isInvention ? "实用新型" : "发明"}并关联
          </Button>
        </Space>
      )}

      <Modal
        title="关联双申案件"
        open={pickerOpen}
        onCancel={() => setPickerOpen(false)}
        footer={null}
        width={720}
      >
        <Text type="secondary">
          候选条件：同一企业、同一申请日（{detail.application_date ?? "本案尚无申请日"}）、
          {isInvention ? "实用新型" : "发明专利"}、尚未与其他案件关联。
        </Text>
        <Table
          style={{ marginTop: 12 }}
          rowKey="id"
          size="small"
          loading={loadingCandidates}
          dataSource={candidates}
          locale={{ emptyText: "没有符合条件的候选案件" }}
          pagination={false}
          columns={[
            { title: "内部编号", dataIndex: "internal_no" },
            { title: "专利名称", dataIndex: "patent_name" },
            { title: "申请号", dataIndex: "application_no" },
            {
              title: "名称一致",
              render: (_: unknown, row) =>
                row.patent_name === detail.patent_name ? <Tag color="green">一致</Tag> : <Tag>不同</Tag>,
            },
            {
              title: "",
              render: (_: unknown, row) => (
                <Button size="small" type="primary" onClick={() => link(row.id)}>
                  关联
                </Button>
              ),
            },
          ]}
        />
      </Modal>
    </div>
  );
}
