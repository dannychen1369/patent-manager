import { useEffect, useState } from "react";
import {
  AutoComplete,
  Button,
  Checkbox,
  Descriptions,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Timeline,
  Typography,
  Upload,
  message,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import CaseFlowSteps from "../components/CaseFlowSteps";
import AgentSelect from "../components/AgentSelect";
import CompanyPicker from "../components/CompanyPicker";
import TwinCasePanel from "../components/TwinCasePanel";
import {
  CASE_FILE_CATEGORY_PRESETS,
  CASE_STAGES,
  type CaseDetailOut,
  type CaseStage,
} from "../types";

const { Title } = Typography;

export default function CaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<CaseDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [newStage, setNewStage] = useState<CaseStage | undefined>();
  const [companyModalOpen, setCompanyModalOpen] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [agentModalOpen, setAgentModalOpen] = useState(false);
  const [newAgentId, setNewAgentId] = useState<number | null>(null);

  const [fileCategory, setFileCategory] = useState("");
  const [fileRoundNo, setFileRoundNo] = useState("");
  const [fileNote, setFileNote] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get<CaseDetailOut>(`/cases/${id}`)
      .then((res) => setDetail(res.data))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [id]);

  const confirmCase = () => {
    api
      .post(`/cases/${id}/confirm`)
      .then(() => {
        message.success("已确认，进入待撰写阶段");
        load();
      })
      .catch((err) => message.error(err.message));
  };

  const changeCompany = () => {
    if (!newCompanyName.trim()) {
      message.warning("请选择或输入企业");
      return Promise.reject();
    }
    return api
      .patch(`/cases/${id}`, { client_name: newCompanyName.trim() })
      .then(() => {
        message.success("已转到新企业");
        setCompanyModalOpen(false);
        load();
      })
      .catch((err) => message.error(err.message));
  };

  const changeAgent = () =>
    api
      .patch(`/cases/${id}`, { agent_id: newAgentId })
      .then(() => {
        message.success("承办人已更新");
        setAgentModalOpen(false);
        load();
      })
      .catch((err) => message.error(err.message));

  const changeStage = () => {
    if (!newStage) return;
    api
      .post(`/cases/${id}/stage`, { stage: newStage })
      .then(() => {
        message.success("阶段已更新");
        setNewStage(undefined);
        load();
      })
      .catch((err) => message.error(err.message));
  };

  const uploadCaseFile = () => {
    if (!pendingFile || !fileCategory) {
      message.warning("请选择分类并选择文件");
      return;
    }
    const data = new FormData();
    data.append("file", pendingFile);
    data.append("category", fileCategory);
    if (fileRoundNo) data.append("round_no", fileRoundNo);
    if (fileNote) data.append("note", fileNote);
    setUploadingFile(true);
    api
      .post(`/cases/${id}/files`, data, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then(() => {
        message.success("已上传");
        setPendingFile(null);
        setFileCategory("");
        setFileRoundNo("");
        setFileNote("");
        load();
      })
      .catch((err) => message.error(err.message))
      .finally(() => setUploadingFile(false));
  };

  const deleteCaseFile = (fileId: number) => {
    api
      .delete(`/cases/${id}/files/${fileId}`)
      .then(() => {
        message.success("已删除");
        load();
      })
      .catch((err) => message.error(err.message));
  };

  const openCaseFolder = () => {
    api
      .post(`/cases/${id}/files/open-folder`)
      .catch((err) => message.error(err.message));
  };

  const toggleStageDone = (eventId: number, isDone: boolean) => {
    api
      .patch(`/cases/${id}/stage-events/${eventId}`, { is_done: isDone })
      .then(() => load())
      .catch((err) => message.error(err.message));
  };

  const deleteCase = () => {
    Modal.confirm({
      title: `确认删除案件「${detail?.internal_no} · ${detail?.patent_name}」？`,
      content: "此操作不可撤销：会一并删除该案件的所有阶段记录、文书、期限、案件资料文件。请谨慎操作。",
      okText: "确认删除",
      okButtonProps: { danger: true },
      onOk: () =>
        api
          .delete(`/cases/${id}`)
          .then(() => {
            message.success("案件已删除");
            navigate("/cases");
          })
          .catch((err) => message.error(err.message)),
    });
  };

  if (loading || !detail) return <div>加载中...</div>;

  return (
    <div>
      <Space style={{ width: "100%", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          {detail.internal_no} · {detail.patent_name}
        </Title>
        <Space>
          {detail.current_stage === "待确认" && (
            <Button type="primary" onClick={confirmCase}>
              客户已确认，进入待撰写
            </Button>
          )}
          <Link to={`/upload?case_id=${detail.id}`}>
            <Button>为此案件上传文书</Button>
          </Link>
          <Button danger onClick={deleteCase}>
            删除案件
          </Button>
        </Space>
      </Space>

      <CaseFlowSteps
        patentType={detail.patent_type}
        currentStage={detail.current_stage}
        events={detail.stage_events}
      />

      <TwinCasePanel detail={detail} onChanged={load} />

      <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
        <Descriptions.Item label="所属企业">
          {detail.company_id ? (
            <Link to={`/companies/${detail.company_id}`}>{detail.client_name}</Link>
          ) : (
            detail.client_name
          )}
          <a
            style={{ marginLeft: 12, fontSize: 12 }}
            onClick={() => {
              setNewCompanyName(detail.client_name);
              setCompanyModalOpen(true);
            }}
          >
            更换
          </a>
        </Descriptions.Item>
        <Descriptions.Item label="专利类型">{detail.patent_type}</Descriptions.Item>
        <Descriptions.Item label="申请号">
          {detail.application_no ?? "（尚未获得申请号）"}
        </Descriptions.Item>
        <Descriptions.Item label="申请日">{detail.application_date ?? "-"}</Descriptions.Item>
        <Descriptions.Item label="当前阶段">
          <Tag color="blue">{detail.current_stage}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="承办人">
          {detail.agent ?? "-"}
          <a
            style={{ marginLeft: 12, fontSize: 12 }}
            onClick={() => {
              setNewAgentId(detail.agent_id);
              setAgentModalOpen(true);
            }}
          >
            {detail.agent ? "更换" : "设置"}
          </a>
        </Descriptions.Item>
        <Descriptions.Item label="备注" span={2}>
          {detail.notes ?? "-"}
        </Descriptions.Item>
      </Descriptions>

      <Modal
        title="设置承办人"
        open={agentModalOpen}
        onCancel={() => setAgentModalOpen(false)}
        onOk={changeAgent}
        okText="确定"
      >
        <AgentSelect value={newAgentId} onChange={setNewAgentId} />
      </Modal>

      <Modal
        title="更换所属企业"
        open={companyModalOpen}
        onCancel={() => setCompanyModalOpen(false)}
        onOk={changeCompany}
        okText="确定"
      >
        <CompanyPicker
          style={{ width: "100%" }}
          value={newCompanyName}
          onChange={setNewCompanyName}
        />
      </Modal>

      <Space style={{ marginBottom: 24 }}>
        <Select
          placeholder="手动调整阶段"
          style={{ width: 200 }}
          value={newStage}
          onChange={setNewStage}
          options={CASE_STAGES.map((s) => ({ label: s, value: s }))}
        />
        <Button onClick={changeStage} disabled={!newStage}>
          更新阶段
        </Button>
        <Typography.Text type="secondary">
          阶段由上传的通知书自动决定（以发文日最晚的通知书为准），一般无需手动调整
        </Typography.Text>
      </Space>

      <Title level={4}>阶段时间线</Title>
      <Timeline
        style={{ marginBottom: 24 }}
        items={detail.stage_events.map((e) => ({
          color: e.is_done ? "green" : "blue",
          children: (
            <div>
              <Checkbox
                checked={e.is_done}
                onChange={(ev) => toggleStageDone(e.id, ev.target.checked)}
              >
                <b>{e.stage}</b>
              </Checkbox>
              {" — "}
              {new Date(e.changed_at).toLocaleString()}
              {e.note ? <div style={{ color: "#888" }}>{e.note}</div> : null}
            </div>
          ),
        }))}
      />

      <Space style={{ width: "100%", justifyContent: "space-between" }}>
        <Title level={4} style={{ margin: 0 }}>
          案件资料
        </Title>
        <Button onClick={openCaseFolder}>在文件夹中打开</Button>
      </Space>
      <Typography.Paragraph type="secondary">
        存放交底材料（如客户提供的CAD图纸）、撰写稿、补正答复等支撑文件。上传的文件保存在本案件专属的文件夹里，也可以点击上方按钮直接在文件资源管理器里打开该文件夹手动放入文件（手动放入的文件不会出现在下方列表中，但同样安全保存在文件夹内）。
      </Typography.Paragraph>
      <Space style={{ marginBottom: 12 }} wrap>
        <AutoComplete
          style={{ width: 160 }}
          placeholder="分类（如：实审答复）"
          value={fileCategory}
          onChange={setFileCategory}
          options={CASE_FILE_CATEGORY_PRESETS.map((c) => ({ value: c }))}
        />
        <Input
          style={{ width: 120 }}
          placeholder="第几次（可选）"
          value={fileRoundNo}
          onChange={(e) => setFileRoundNo(e.target.value)}
        />
        <Input
          style={{ width: 200 }}
          placeholder="备注（可选）"
          value={fileNote}
          onChange={(e) => setFileNote(e.target.value)}
        />
        <Upload
          beforeUpload={(f) => {
            setPendingFile(f);
            return false;
          }}
          maxCount={1}
          fileList={pendingFile ? [{ uid: "1", name: pendingFile.name } as never] : []}
          onRemove={() => setPendingFile(null)}
        >
          <Button icon={<UploadOutlined />}>选择文件</Button>
        </Upload>
        <Button type="primary" loading={uploadingFile} onClick={uploadCaseFile}>
          上传
        </Button>
      </Space>
      <Table
        rowKey="id"
        dataSource={detail.files}
        pagination={false}
        style={{ marginBottom: 24 }}
        columns={[
          { title: "分类", dataIndex: "category" },
          { title: "第几次", dataIndex: "round_no" },
          { title: "文件名", dataIndex: "original_filename" },
          { title: "备注", dataIndex: "note" },
          {
            title: "上传时间",
            dataIndex: "uploaded_at",
            render: (v) => new Date(v).toLocaleString(),
          },
          {
            title: "操作",
            render: (_: unknown, row) => (
              <Space>
                <a href={`${api.defaults.baseURL}/cases/${id}/files/${row.id}/download`} target="_blank" rel="noreferrer">
                  下载
                </a>
                <a onClick={() => deleteCaseFile(row.id)}>删除</a>
              </Space>
            ),
          },
        ]}
      />

      <Title level={4}>已上传文书</Title>
      <Table
        rowKey="id"
        dataSource={detail.documents}
        pagination={false}
        style={{ marginBottom: 24 }}
        columns={[
          { title: "文件名", dataIndex: "original_filename" },
          { title: "文书类型", dataIndex: "doc_type" },
          { title: "细分", dataIndex: "doc_variant" },
          { title: "发文日", dataIndex: "issue_date" },
          { title: "上传时间", dataIndex: "created_at", render: (v) => new Date(v).toLocaleString() },
        ]}
      />

      <Title level={4}>期限</Title>
      <Table
        rowKey="id"
        dataSource={detail.deadlines}
        pagination={false}
        columns={[
          { title: "期限类型", dataIndex: "deadline_type" },
          { title: "到期日", dataIndex: "due_date" },
          { title: "状态", dataIndex: "status" },
          { title: "备注", dataIndex: "note" },
        ]}
      />
    </div>
  );
}
