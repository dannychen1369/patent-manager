import { useEffect, useState } from "react";
import { Select } from "antd";
import { api } from "../api/client";
import { agentLabel, type AgentOut } from "../types";

interface Props {
  value?: number | null;
  onChange?: (agentId: number | null) => void;
  style?: React.CSSProperties;
  placeholder?: string;
}

/** Pick the responsible attorney from the roster (searchable). */
export default function AgentSelect({ value, onChange, style, placeholder }: Props) {
  const [agents, setAgents] = useState<AgentOut[]>([]);

  useEffect(() => {
    api.get<AgentOut[]>("/agents", { params: { include_inactive: true } }).then((res) => setAgents(res.data));
  }, []);

  // Inactive (left) attorneys can't be newly picked, but a case that already
  // has one still shows the name.
  const options = agents
    .filter((a) => a.is_active || a.id === value)
    .map((a) => ({ value: a.id, label: agentLabel(a) }));

  return (
    <Select
      showSearch
      allowClear
      style={style ?? { width: "100%" }}
      placeholder={placeholder ?? "从代理人名单中选择"}
      optionFilterProp="label"
      value={value ?? undefined}
      onChange={(v) => onChange?.(v ?? null)}
      options={options}
      notFoundContent="名单中没有匹配的代理人，请先到「代理人名单」添加"
    />
  );
}
