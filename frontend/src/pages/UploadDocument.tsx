import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Collapse,
  DatePicker,
  Input,
  Progress,
  Radio,
  Select,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import { FolderOpenOutlined, UploadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import AgentSelect from "../components/AgentSelect";
import {
  DOC_TYPES,
  patentTypeFromApplicationNo,
  type CaseOut,
  type CompanyOut,
  type DocType,
  type DocumentParseResult,
  type PatentType,
  type SuggestedDeadline,
} from "../types";

const { Title, Paragraph, Text } = Typography;

// Must match what the backend can extract text from (services/ocr_extract.py).
const SUPPORTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"];

type ItemStatus =
  | "pending"
  | "parsing"
  | "parsed"
  | "duplicate"
  | "error"
  | "confirming"
  | "confirmed";

interface BatchItem {
  key: string;
  file: File;
  /** Path inside the picked folder (e.g. "客户A/受理通知书.pdf"), or the bare filename. */
  displayName: string;
  status: ItemStatus;
  error?: string;
  matchedCaseId?: number | null;
  matchedCaseInternalNo?: string | null;
  matchedCompanyName?: string | null;
  duplicateCaseId?: number | null;
  duplicateCaseInternalNo?: string | null;
  duplicateReason?: string | null;
  /** User chose 「仍然录入」 for a notice flagged as already recorded. */
  allowDuplicate?: boolean;
  dispatch_no?: string | null;
  suggestedDeadlines: SuggestedDeadline[];
  savedCaseId?: number;
  temp_file_path?: string;
  raw_text?: string;
  // editable fields
  doc_type?: DocType;
  doc_variant?: string;
  issue_date?: string | null;
  application_date?: string | null;
  application_no?: string;
  applicant_name?: string;
  patent_name?: string;
  patent_type?: PatentType;
  linkMode: "matched" | "existing" | "new";
  selectedCaseId?: number;
}

let keyCounter = 0;
const nextKey = () => `f${Date.now()}_${keyCounter++}`;

const isSupported = (name: string) =>
  SUPPORTED_EXTENSIONS.some((ext) => name.toLowerCase().endsWith(ext));

// Identity of a picked file, so picking the same folder twice doesn't queue
// everything twice. (Content-level duplicates of already-saved notices are
// caught separately by the backend's file hash check.)
// Same notice = same 发文序号, or failing that the same application number,
// notice type, round and issue date.
const noticeKey = (it: Pick<BatchItem, "dispatch_no" | "application_no" | "doc_type" | "doc_variant" | "issue_date">) =>
  it.dispatch_no
    ? `d:${it.dispatch_no}`
    : it.application_no && it.doc_type && it.issue_date
      ? `k:${it.application_no}|${it.doc_type}|${it.doc_variant ?? ""}|${it.issue_date}`
      : null;

const fileIdentity = (file: File) =>
  `${file.webkitRelativePath || file.name}|${file.size}|${file.lastModified}`;

export default function UploadDocument() {
  const [searchParams] = useSearchParams();
  const presetCaseId = searchParams.get("case_id");
  const presetCompanyId = searchParams.get("company_id");

  const [items, setItems] = useState<BatchItem[]>([]);
  // Latest items for async code (parseAll awaits each file, so earlier
  // results have rendered by the time the next one is checked).
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [parsingAll, setParsingAll] = useState(false);
  const [confirmingAll, setConfirmingAll] = useState(false);
  const [allCases, setAllCases] = useState<CaseOut[]>([]);
  const [presetCompany, setPresetCompany] = useState<CompanyOut | null>(null);
  // 承办人 given to every case this batch creates.
  const [defaultAgentId, setDefaultAgentId] = useState<number | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    api.get<CaseOut[]>("/cases").then((res) => setAllCases(res.data));
  }, []);

  useEffect(() => {
    if (!presetCompanyId) return;
    api
      .get<CompanyOut>(`/companies/${presetCompanyId}`)
      .then((res) => setPresetCompany(res.data))
      .catch((err) => message.error(err.message));
  }, [presetCompanyId]);

  const updateItem = (key: string, patch: Partial<BatchItem>) => {
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, ...patch } : it)));
  };

  const collapseItem = (key: string) => {
    setExpandedKeys((prev) => prev.filter((k) => k !== key));
  };

  // Identities of everything currently in the list, kept in a ref (not
  // derived from `items`) because antd's Upload calls beforeUpload once per
  // file in quick succession, before any state update has been rendered.
  const queuedRef = useRef(new Set<string>());

  const addFiles = (files: File[]) => {
    const supported = files.filter((f) => isSupported(f.name));
    const fresh = supported.filter((f) => !queuedRef.current.has(fileIdentity(f)));
    fresh.forEach((f) => queuedRef.current.add(fileIdentity(f)));
    const newItems: BatchItem[] = fresh.map((file) => ({
      key: nextKey(),
      file,
      displayName: file.webkitRelativePath || file.name,
      status: "pending",
      suggestedDeadlines: [],
      linkMode: presetCaseId ? "existing" : "new",
      selectedCaseId: presetCaseId ? Number(presetCaseId) : undefined,
    }));
    if (newItems.length > 0) {
      setItems((prev) =>
        [...prev, ...newItems].sort((a, b) => a.displayName.localeCompare(b.displayName, "zh-CN"))
      );
      setExpandedKeys((keys) => [...keys, ...newItems.map((it) => it.key)]);
    }
    return {
      added: newItems.length,
      unsupported: files.length - supported.length,
      alreadyQueued: supported.length - fresh.length,
    };
  };

  const onFolderPicked = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ""; // allow picking the same folder again later
    if (files.length === 0) return;
    const result = addFiles(files);
    const parts = [`已加入 ${result.added} 份文书`];
    if (result.unsupported > 0) parts.push(`跳过 ${result.unsupported} 个非 PDF/图片文件`);
    if (result.alreadyQueued > 0) parts.push(`${result.alreadyQueued} 份已在列表中`);
    message.info(parts.join("，"));
  };

  const dropItems = (shouldDrop: (it: BatchItem) => boolean) => {
    setItems((prev) => {
      prev.filter(shouldDrop).forEach((it) => queuedRef.current.delete(fileIdentity(it.file)));
      return prev.filter((it) => !shouldDrop(it));
    });
  };

  const removeItem = (key: string) => dropItems((it) => it.key === key);

  const clearFinished = () =>
    dropItems((it) => it.status === "confirmed" || it.status === "duplicate");

  const parseOne = async (item: BatchItem) => {
    updateItem(item.key, { status: "parsing" });
    const data = new FormData();
    data.append("file", item.file);
    try {
      const res = await api.post<DocumentParseResult>("/documents/parse", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const parsed = res.data;
      const isDuplicate = parsed.duplicate_document_id != null;
      const key = noticeKey({
        dispatch_no: parsed.dispatch_no,
        application_no: parsed.application_no ?? undefined,
        doc_type: parsed.doc_type,
        doc_variant: parsed.doc_variant ?? undefined,
        issue_date: parsed.issue_date,
      });
      // Also catch the same notice appearing twice in this batch (e.g. two
      // copies in different sub-folders): the later one is the duplicate.
      const batchTwin = itemsRef.current.find(
        (it) =>
          it.key !== item.key &&
          it.status !== "duplicate" &&
          it.status !== "pending" &&
          it.status !== "parsing" &&
          key !== null &&
          noticeKey(it) === key
      );
      const inBatchDuplicate = !isDuplicate && batchTwin !== undefined;
      updateItem(item.key, {
        status: isDuplicate || inBatchDuplicate ? "duplicate" : "parsed",
        dispatch_no: parsed.dispatch_no,
        duplicateReason: isDuplicate
          ? parsed.duplicate_reason
          : inBatchDuplicate
            ? `与本批次中「${batchTwin!.displayName}」是同一份通知书`
            : null,
        doc_type: parsed.doc_type,
        doc_variant: parsed.doc_variant ?? undefined,
        issue_date: parsed.issue_date,
        application_date: parsed.application_date,
        application_no: parsed.application_no ?? undefined,
        applicant_name: parsed.applicant_name ?? undefined,
        patent_name: parsed.patent_name ?? undefined,
        patent_type: parsed.patent_type ?? undefined,
        matchedCaseId: parsed.matched_case_id,
        matchedCaseInternalNo: parsed.matched_case_internal_no,
        matchedCompanyName: parsed.matched_company_name,
        duplicateCaseId: parsed.duplicate_case_id,
        duplicateCaseInternalNo: parsed.duplicate_case_internal_no,
        suggestedDeadlines: parsed.suggested_deadlines,
        linkMode: presetCaseId ? "existing" : parsed.matched_case_id ? "matched" : "new",
        temp_file_path: parsed.temp_file_path,
        raw_text: parsed.raw_text,
      });
      if (isDuplicate || inBatchDuplicate) collapseItem(item.key);
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
      application_date: item.application_date || null,
      application_no: item.application_no || null,
      applicant_name: item.applicant_name || null,
      patent_name: item.patent_name || null,
      patent_type: item.patent_type || null,
      dispatch_no: item.dispatch_no || null,
      allow_duplicate: item.allowDuplicate ?? false,
    };
    if (presetCaseId) {
      payload.case_id = Number(presetCaseId);
    } else if (item.linkMode === "matched") {
      payload.case_id = item.matchedCaseId;
    } else if (item.linkMode === "existing") {
      payload.case_id = item.selectedCaseId;
    } else {
      // The backend still matches by application_no first, so several
      // notices of the same new application in one batch (e.g. 受理通知书 +
      // 缴费通知) all land in the single case the first one creates.
      payload.create_new_case_if_unmatched = true;
      if (presetCompanyId) payload.company_id = Number(presetCompanyId);
      if (defaultAgentId) payload.agent_id = defaultAgentId;
    }

    try {
      const res = await api.post("/documents/confirm", payload);
      updateItem(item.key, { status: "confirmed", savedCaseId: res.data.case_id });
      collapseItem(item.key);
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
    // Save oldest notices first, so each case moves through its stages in
    // real order (受理 → 初审 → 一审 ...) and the timeline reads correctly.
    const ready = candidates
      .filter((it) => !needsCaseSelection.includes(it))
      .sort((a, b) => (a.issue_date ?? "9999").localeCompare(b.issue_date ?? "9999"));

    setConfirmingAll(true);
    for (const it of ready) {
      // eslint-disable-next-line no-await-in-loop
      await confirmOne(it);
    }
    setConfirmingAll(false);
    api.get<CaseOut[]>("/cases").then((res) => setAllCases(res.data));
  };

  // For "create new case" items: how many other unsaved items in this batch
  // share the application number (they'll be merged into the same new case).
  const sameAppNoCount = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const it of items) {
      if (it.application_no && (it.status === "parsed" || it.status === "confirming")) {
        counts[it.application_no] = (counts[it.application_no] ?? 0) + 1;
      }
    }
    return counts;
  }, [items]);

  const summary = useMemo(() => {
    const by = (s: ItemStatus[]) => items.filter((it) => s.includes(it.status)).length;
    return {
      total: items.length,
      pending: by(["pending", "parsing"]),
      parsed: by(["parsed", "confirming"]),
      duplicate: by(["duplicate"]),
      error: by(["error"]),
      confirmed: by(["confirmed"]),
    };
  }, [items]);

  const statusTag = (item: BatchItem) => {
    switch (item.status) {
      case "pending":
        return <Tag>待解析</Tag>;
      case "parsing":
        return <Tag color="processing">解析中...</Tag>;
      case "parsed":
        return <Tag color="orange">待核对确认</Tag>;
      case "duplicate":
        return <Tag color="default">已录入过，跳过</Tag>;
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

  const newCaseCompanyHint = (item: BatchItem) => {
    if (presetCompany) return `归入企业：${presetCompany.name}`;
    if (item.matchedCompanyName) return `归入已有企业：${item.matchedCompanyName}`;
    if (item.applicant_name) return `将新建企业：${item.applicant_name}`;
    return "未识别到申请人，案件暂不归属企业";
  };

  const doneCount = summary.confirmed + summary.duplicate + summary.error;

  return (
    <div style={{ maxWidth: 900 }}>
      <Title level={3}>文书录入</Title>
      <Paragraph type="secondary">
        可以选择多份文件，或直接选择一个文件夹（含子文件夹）批量录入。系统逐份提取文字并解析申请号、文书类型、发文日等信息：
        能按申请号匹配到的文书归入已有案件，匹配不到的（如新来的受理通知书）会自动新建案件，并按申请人归入对应企业。
        请核对无误后再确认保存，保存时按发文日从早到晚依次录入。
      </Paragraph>

      {presetCompany && (
        <Alert
          style={{ marginBottom: 16 }}
          type="info"
          showIcon
          message={
            <>
              正在为企业 <Link to={`/companies/${presetCompany.id}`}>{presetCompany.name}</Link>{" "}
              录入：匹配不到已有案件的文书，新建的案件都会归入该企业。
            </>
          }
        />
      )}

      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<FolderOpenOutlined />} onClick={() => folderInputRef.current?.click()}>
          选择文件夹
        </Button>
        <input
          ref={(el) => {
            folderInputRef.current = el;
            // Not in React's typings; supported by Chromium/WebView2.
            el?.setAttribute("webkitdirectory", "");
          }}
          type="file"
          multiple
          style={{ display: "none" }}
          onChange={onFolderPicked}
        />
        <Upload
          multiple
          accept={SUPPORTED_EXTENSIONS.join(",")}
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
        <Button
          type="primary"
          loading={parsingAll}
          disabled={summary.pending + summary.error === 0}
          onClick={parseAll}
        >
          解析全部
        </Button>
        <Button
          disabled={!items.some((it) => it.status === "parsed")}
          loading={confirmingAll}
          onClick={confirmAll}
        >
          确认保存全部
        </Button>
        {doneCount > 0 && <Button onClick={clearFinished}>清除已完成</Button>}
      </Space>

      {!presetCaseId && (
        <Space style={{ marginBottom: 16 }}>
          <Text>新建案件的承办人：</Text>
          <AgentSelect
            style={{ width: 280 }}
            placeholder="不设置（之后在案件页指定）"
            value={defaultAgentId}
            onChange={setDefaultAgentId}
          />
        </Space>
      )}

      {items.length === 0 ? (
        <Paragraph type="secondary">尚未选择文件。</Paragraph>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <Space wrap size="large">
            <Text>共 {summary.total} 份</Text>
            {summary.pending > 0 && <Text>待解析 {summary.pending}</Text>}
            {summary.parsed > 0 && <Text type="warning">待确认 {summary.parsed}</Text>}
            {summary.confirmed > 0 && <Text type="success">已保存 {summary.confirmed}</Text>}
            {summary.duplicate > 0 && <Text type="secondary">重复跳过 {summary.duplicate}</Text>}
            {summary.error > 0 && <Text type="danger">出错 {summary.error}</Text>}
          </Space>
          {(parsingAll || confirmingAll) && (
            <Progress
              percent={Math.round(
                ((parsingAll ? summary.total - summary.pending : summary.confirmed) /
                  summary.total) *
                  100
              )}
              size="small"
            />
          )}
        </div>
      )}

      {items.length > 0 && (
      <Collapse
        activeKey={expandedKeys}
        onChange={(keys) => setExpandedKeys(Array.isArray(keys) ? keys : [keys])}
        items={items.map((item) => ({
          key: item.key,
          label: (
            <Space wrap>
              <span>{item.displayName}</span>
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

              {item.status === "duplicate" ? (
                <Alert
                  type="info"
                  showIcon
                  message={
                    <>
                      {item.duplicateReason ?? "这份通知书之前已经录入过"}
                      {item.duplicateCaseId && (
                        <>
                          （案件 <Link to={`/cases/${item.duplicateCaseId}`}>{item.duplicateCaseInternalNo}</Link>）
                        </>
                      )}
                      ，判断为重复的通知书，默认跳过。
                    </>
                  }
                  action={
                    <Button
                      size="small"
                      onClick={() => {
                        updateItem(item.key, { status: "parsed", allowDuplicate: true });
                        setExpandedKeys((keys) => [...keys, item.key]);
                      }}
                    >
                      仍然录入
                    </Button>
                  }
                />
              ) : item.status === "confirmed" ? (
                <Alert
                  type="success"
                  showIcon
                  message={
                    <>
                      已保存 — <Link to={`/cases/${item.savedCaseId}`}>查看案件</Link>
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
                        onChange={(e) => {
                          const appNo = e.target.value;
                          const derived = patentTypeFromApplicationNo(appNo);
                          updateItem(item.key, {
                            application_no: appNo,
                            ...(derived ? { patent_type: derived } : {}),
                          });
                        }}
                      />
                    </div>
                    <div>
                      <div>申请日</div>
                      <DatePicker
                        value={item.application_date ? dayjs(item.application_date) : null}
                        onChange={(d) =>
                          updateItem(item.key, {
                            application_date: d ? d.format("YYYY-MM-DD") : null,
                          })
                        }
                      />
                    </div>
                    <div>
                      <div>申请人 / 专利权人</div>
                      <Input
                        style={{ width: 220 }}
                        value={item.applicant_name}
                        onChange={(e) => updateItem(item.key, { applicant_name: e.target.value })}
                      />
                    </div>
                    <div>
                      <div>专利名称</div>
                      <Input
                        style={{ width: 220 }}
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
                        <Radio value="new">根据此文书新建案件</Radio>
                      </Radio.Group>
                      {item.linkMode === "new" && (
                        <div style={{ marginTop: 6 }}>
                          <Text type="secondary">
                            {newCaseCompanyHint(item)}
                            {item.application_no &&
                              (sameAppNoCount[item.application_no] ?? 0) > 1 &&
                              `；本批次另有 ${sameAppNoCount[item.application_no] - 1} 份同申请号文书，将归入同一个案件`}
                          </Text>
                        </div>
                      )}
                      {item.linkMode === "existing" && (
                        <Select
                          showSearch
                          placeholder="搜索案件（内部编号 / 企业名称）"
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
      )}
    </div>
  );
}
