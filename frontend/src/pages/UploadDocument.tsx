import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Collapse,
  DatePicker,
  Input,
  Radio,
  Select,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import {
  DOC_TYPES,
  type CaseOut,
  type DocType,
  type DocumentParseResult,
  type PatentType,
  type SuggestedDeadline,
} from "../types";

const { Title, Paragraph, Text } = Typography;

type ItemStatus = "pending" | "parsing" | "parsed" | "error" | "confirming" | "confirmed";

interface BatchItem {
  key: string;
  file: File;
  status: ItemStatus;
  error?: string;
  matchedCaseId?: number | null;
  matchedCaseInternalNo?: string | null;
  suggestedDeadlines: SuggestedDeadline[];
  savedCaseId?: number;
  temp_file_path?: string;
  raw_text?: string;
  // editable fields
  doc_type?: DocType;
  doc_variant?: string;
  issue_date?: string | null;
  application_no?: string;
  applicant_name?: string;
  patent_name?: string;
  patent_type?: PatentType;
  linkMode: "matched" | "existing" | "new";
  selectedCaseId?: number;
}

let keyCounter = 0;
const nextKey = () => `f${Date.now()}_${keyCounter++}`;

export default function UploadDocument() {
  const [searchParams] = useSearchParams();
  const presetCaseId = searchParams.get("case_id");

  const [items, setItems] = useState<BatchItem[]>([]);
  const [parsingAll, setParsingAll] = useState(false);
  const [confirmingAll, setConfirmingAll] = useState(false);
  const [allCases, setAllCases] = useState<CaseOut[]>([]);

  useEffect(() => {
    api.get<CaseOut[]>("/cases").then((res) => setAllCases(res.data));
  }, []);

  const updateItem = (key: string, patch: Partial<BatchItem>) => {
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)));
  };

  const addFiles = (files: File[]) => {
    setItems((prev) => [
      ...prev,
      ...files.map((file) => ({
        key: nextKey(),
        file,
        status: "pending" as ItemStatus,
        suggestedDeadlines: [],
        linkMode: presetCaseId ? ("existing" as const) : ("new" as const),
        selectedCaseId: presetCaseId ? Number(presetCaseId) : undefined,
      })),
    ]);
  };

  const removeItem = (key: string) => {
    setItems((prev) => prev.filter((it) => it.key !== key));
  };

  const parseOne = async (item: BatchItem) => {
    updateItem(item.key, { status: "parsing" });
    const data = new FormData();
    data.append("file", item.file);
    try {
      const res = await api.post<DocumentParseResult>("/documents/parse", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const parsed = res.data;
      updateItem(item.key, {
        status: "parsed",
        doc_type: parsed.doc_type,
        doc_variant: parsed.doc_variant ?? undefined,
        issue_date: parsed.issue_date,
        application_no: parsed.application_no ?? undefined,
        applicant_name: parsed.applicant_name ?? undefined,
        patent_name: parsed.patent_name ?? undefined,
        patent_type: parsed.patent_type ?? undefined,
        matchedCaseId: parsed.matched_case_id,
        matchedCaseInternalNo: parsed.matched_case_internal_no,
        suggestedDeadlines: parsed.suggested_deadlines,
        linkMode: presetCaseId ? "existing" : parsed.matched_case_id ? "matched" : "new",
        temp_file_path: parsed.temp_file_path,
        raw_text: parsed.raw_text,
      });
    } catch (err) {
      updateItem(item.key, { status: "error", error: (err as Error).message });
    }
  };

  const parseAll = async () => {
    setParsingAll(true);
    const pending = items.filter((it) => it.status === "pending" || it.status === "error");
    for (const it of pending) {
      // eslint-disable-next-line no-await-in-loop
      await parseOne(it);
    }
    setParsingAll(false);
  };

  const confirmOne = async (item: BatchItem) => {
    updateItem(item.key, { status: "confirming" });
    const payload: Record<string, unknown> = {
      temp_file_path: item.temp_file_path,
      original_filename: item.file.name,
      doc_type: item.doc_type,
      doc_variant: item.doc_variant || null,
      raw_text: item.raw_text,
      issue_date: item.issue_date || null,
      application_no: item.application_no || null,
      applicant_name: item.applicant_name || null,
      patent_name: item.patent_name || null,
      patent_type: item.patent_type || null,
    };
    if (presetCaseId) {
      payload.case_id = Number(presetCaseId);
    } else if (item.linkMode === "matched") {
      payload.case_id = item.matchedCaseId;
    } else if (item.linkMode === "existing") {
      payload.case_id = item.selectedCaseId;
    } else {
      payload.create_new_case_if_unmatched = true;
    }

    try {
      const res = await api.post("/documents/confirm", payload);
      updateItem(item.key, { status: "confirmed", savedCaseId: res.data.case_id });
    } catch (err) {
      updateItem(item.key, { status: "error", error: (err as Error).message });
    }
  };

  const confirmAll = async () => {
    const candidates = items.filter((it) => it.status === "parsed");
    if (candidates.length === 0) {
      message.warning("没有待确认保存的文件——请先选择文件并点击「解析全部」，且解析没有出错");
      return;
    }

    const needsCaseSelection = candidates.filter(
      (it) => !presetCaseId && it.linkMode === "existing" && !it.selectedCaseId
    );
    if (needsCaseSelection.length > 0) {
      message.warning(
        `有 ${needsCaseSelection.length} 个文件选择了"关联已有案件"但还没选具体案件，已跳过这些文件，请为它们选好案件后再确认保存（或点击每个文件自己的"确认保存"按钮）`
      );
    }
    const ready = candidates.filter((it) => !needsCaseSelection.includes(it));

    setConfirmingAll(true);
    for (const it of ready) {
      // eslint-disable-next-line no-await-in-loop
      await confirmOne(it);
    }
    setConfirmingAll(false);
  };

  const statusTag = (item: BatchItem) => {
    switch (item.status) {
      case "pending":
        return <Tag>待解析</Tag>;
      case "parsing":
        return <Tag color="processing">解析中...</Tag>;
      case "parsed":
        return <Tag color="orange">待核对确认</Tag>;
      case "confirming":
        return <Tag color="processing">保存中...</Tag>;
      case "confirmed":
        return <Tag color="green">已保存</Tag>;
      case "error":
        return <Tag color="red">出错</Tag>;
      default:
        return null;
    }
  };

  return (
    <div style={{ maxWidth: 860 }}>
      <Title level={3}>上传官方文书</Title>
      <Paragraph type="secondary">
        可一次选择多份文件批量上传。系统会逐份自动提取文字并解析字段，请核对无误后再确认保存——保存后文件会自动归档到对应案件的专属文件夹中。
      </Paragraph>

      <Space style={{ marginBottom: 16 }}>
        <Upload
          multiple
          beforeUpload={(file) => {
            // antd calls beforeUpload once PER FILE even for a multi-select
            // batch, and its second arg (fileList) is the *whole* batch on
            // every single call — using that instead of the single `file`
            // here would add every file N times (N = batch size).
            addFiles([file]);
            return false;
          }}
          showUploadList={false}
        >
          <Button icon={<UploadOutlined />}>选择文件（可多选，PDF / 图片）</Button>
        </Upload>
        <Button type="primary" loading={parsingAll} disabled={items.length === 0} onClick={parseAll}>
          解析全部
        </Button>
        <Button
          disabled={!items.some((it) => it.status === "parsed")}
          loading={confirmingAll}
          onClick={confirmAll}
        >
          确认保存全部
        </Button>
      </Space>

      {items.length === 0 && <Paragraph type="secondary">尚未选择文件。</Paragraph>}

      <Collapse
        activeKey={items.map((it) => it.key)}
        items={items.map((item) => ({
          key: item.key,
          label: (
            <Space>
              <span>{item.file.name}</span>
              {statusTag(item)}
              {item.doc_type && <Text type="secondary">{item.doc_type}</Text>}
              {item.application_no && <Text type="secondary">申请号：{item.application_no}</Text>}
            </Space>
          ),
          extra: (
            <a
              onClick={(e) => {
                e.stopPropagation();
                removeItem(item.key);
              }}
            >
              移除
            </a>
          ),
          children: (
            <div>
              {item.status === "error" && item.error && (
                <Alert style={{ marginBottom: 12 }} type="error" showIcon message={item.error} />
              )}

              {item.status === "confirmed" ? (
                <Alert
                  type="success"
                  showIcon
                  message={
                    <>
                      已保存 —{" "}
                      <Link to={`/cases/${item.savedCaseId}`}>查看案件</Link>
                    </>
                  }
                />
              ) : item.status === "parsed" || item.status === "confirming" ? (
                <Space direction="vertical" style={{ width: "100%" }} size="middle">
                  <Space wrap>
                    <div>
                      <div>文书类型</div>
                      <Select
                        style={{ width: 180 }}
                        value={item.doc_type}
                        onChange={(v) => updateItem(item.key, { doc_type: v })}
                        options={DOC_TYPES.map((t) => ({ label: t, value: t }))}
                      />
                    </div>
                    <div>
                      <div>细分（如：第一次）</div>
                      <Input
                        style={{ width: 140 }}
                        value={item.doc_variant}
                        onChange={(e) => updateItem(item.key, { doc_variant: e.target.value })}
                      />
                    </div>
                    <div>
                      <div>发文日</div>
                      <DatePicker
                        value={item.issue_date ? dayjs(item.issue_date) : null}
                        onChange={(d) =>
                          updateItem(item.key, { issue_date: d ? d.format("YYYY-MM-DD") : null })
                        }
                      />
                    </div>
                    <div>
                      <div>申请号</div>
                      <Input
                        style={{ width: 180 }}
                        value={item.application_no}
                        onChange={(e) => updateItem(item.key, { application_no: e.target.value })}
                      />
                    </div>
                    <div>
                      <div>申请人 / 专利权人</div>
                      <Input
                        style={{ width: 180 }}
                        value={item.applicant_name}
                        onChange={(e) => updateItem(item.key, { applicant_name: e.target.value })}
                      />
                    </div>
                    <div>
                      <div>专利名称</div>
                      <Input
                        style={{ width: 200 }}
                        value={item.patent_name}
                        onChange={(e) => updateItem(item.key, { patent_name: e.target.value })}
                      />
                    </div>
                    <div>
                      <div>专利类型</div>
                      <Select
                        allowClear
                        style={{ width: 140 }}
                        value={item.patent_type}
                        onChange={(v) => updateItem(item.key, { patent_type: v })}
                        options={[
                          { label: "发明专利", value: "发明专利" },
                          { label: "实用新型", value: "实用新型" },
                          { label: "外观设计", value: "外观设计" },
                        ]}
                      />
                    </div>
                  </Space>

                  {item.suggestedDeadlines.length > 0 && (
                    <Alert
                      type="warning"
                      showIcon
                      message="系统建议生成以下期限（保存后写入）"
                      description={
                        <ul style={{ margin: 0, paddingLeft: 20 }}>
                          {item.suggestedDeadlines.map((d, i) => (
                            <li key={i}>
                              {d.deadline_type}：{d.due_date ?? "（缺少发文日，无法计算）"}
                              {d.note ? <Text type="secondary">（{d.note}）</Text> : null}
                            </li>
                          ))}
                        </ul>
                      }
                    />
                  )}

                  {!presetCaseId && (
                    <div>
                      <div style={{ marginBottom: 4 }}>关联案件</div>
                      <Radio.Group
                        value={item.linkMode}
                        onChange={(e) => updateItem(item.key, { linkMode: e.target.value })}
                      >
                        {item.matchedCaseId && (
                          <Radio value="matched">
                            按申请号自动匹配到：{item.matchedCaseInternalNo}
                          </Radio>
                        )}
                        <Radio value="existing">选择已有案件</Radio>
                        <Radio value="new">创建新案件</Radio>
                      </Radio.Group>
                      {item.linkMode === "existing" && (
                        <Select
                          showSearch
                          placeholder="搜索案件（内部编号 / 客户名称）"
                          style={{ width: "100%", marginTop: 8 }}
                          optionFilterProp="label"
                          value={item.selectedCaseId}
                          onChange={(v) => updateItem(item.key, { selectedCaseId: v })}
                          options={allCases.map((c) => ({
                            label: `${c.internal_no} · ${c.client_name} · ${c.patent_name}`,
                            value: c.id,
                          }))}
                        />
                      )}
                    </div>
                  )}

                  <Button
                    type="primary"
                    loading={item.status === "confirming"}
                    onClick={() => confirmOne(item)}
                  >
                    确认保存
                  </Button>
                </Space>
              ) : (
                <Text type="secondary">
                  {item.status === "pending" ? "点击上方「解析全部」开始解析" : "解析中..."}
                </Text>
              )}
            </div>
          ),
        }))}
      />
    </div>
  );
}
