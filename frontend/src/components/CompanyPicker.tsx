import { useEffect, useState } from "react";
import { AutoComplete } from "antd";
import { api } from "../api/client";
import type { CompanyOut } from "../types";

interface Props {
  value?: string;
  onChange?: (name: string) => void;
  style?: React.CSSProperties;
  placeholder?: string;
}

/**
 * Pick an existing company by name, or type a new name — the backend finds
 * a company with that name or creates it, so both cases submit the same way.
 */
export default function CompanyPicker({ value, onChange, style, placeholder }: Props) {
  const [companies, setCompanies] = useState<CompanyOut[]>([]);

  useEffect(() => {
    api.get<CompanyOut[]>("/companies").then((res) => setCompanies(res.data));
  }, []);

  return (
    <AutoComplete
      style={style}
      value={value}
      onChange={onChange}
      placeholder={placeholder ?? "选择已有企业，或直接输入新企业名称"}
      allowClear
      options={companies.map((c) => ({ value: c.name, label: `${c.name}（${c.case_count} 件）` }))}
      filterOption={(input, option) => (option?.value ?? "").includes(input)}
    />
  );
}
