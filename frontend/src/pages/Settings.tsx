import { useEffect, useState } from "react";
import { Alert, Button, Input, Space, Typography, message } from "antd";
import { api } from "../api/client";

const { Title, Paragraph, Text } = Typography;

export default function Settings() {
  const [currentDir, setCurrentDir] = useState("");
  const [newPath, setNewPath] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [migrated, setMigrated] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .get<{ data_dir: string }>("/settings")
      .then((res) => setCurrentDir(res.data.data_dir))
      .catch((err) => message.error(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const save = () => {
    if (!newPath.trim()) {
      message.warning("请填写新的存储目录路径");
      return;
    }
    setSaving(true);
    api
      .post("/settings/data-dir", { new_path: newPath.trim() })
      .then((res) => {
        message.success(res.data.message ?? "已迁移");
        setMigrated(true);
      })
      .catch((err) => message.error(err.message))
      .finally(() => setSaving(false));
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <Title level={3}>设置</Title>

      <Title level={4}>数据存储位置</Title>
      <Paragraph type="secondary">
        案件数据库、上传的文书、案件资料文件都保存在这个目录里。可以改到别的磁盘/文件夹（比如同步盘、备份盘）。
      </Paragraph>

      {migrated && (
        <Alert
          style={{ marginBottom: 16 }}
          type="success"
          showIcon
          message="数据已迁移，请关闭并重新打开程序以生效"
        />
      )}

      <Paragraph>
        <Text strong>当前位置：</Text> {loading ? "加载中..." : currentDir}
      </Paragraph>

      <Space.Compact style={{ width: "100%", marginBottom: 8 }}>
        <Input
          placeholder="粘贴新的目标目录完整路径，如 D:\PatentData"
          value={newPath}
          onChange={(e) => setNewPath(e.target.value)}
        />
        <Button type="primary" loading={saving} onClick={save}>
          保存并迁移
        </Button>
      </Space.Compact>
      <Paragraph type="secondary" style={{ fontSize: 12 }}>
        建议先在资源管理器里创建好目标空文件夹，把完整路径复制粘贴到上面。迁移会把现有数据整体移动过去，原位置不会留副本。
      </Paragraph>
    </div>
  );
}
