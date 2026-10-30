export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};
export type Employee = {
  id: string;
  employee_code: string;
  full_name: string;
  counts: Record<string, number>;
};
export type FieldDef = { label: string; type: string; required: boolean };
export type DocType = {
  code: string;
  name: string;
  fields: Record<string, FieldDef>;
};
export type Row = {
  id: string;
  title: string;
  employee_code: string;
  employee_name: string;
  type_code: string;
  type_name: string;
  review_status: string;
  page_count: number;
  created_at: string;
  verified_at: string | null;
  version: number;
};
export type Field = {
  field_name: string;
  label: string;
  field_type: string;
  required: boolean;
  value: string | null;
  value_state: string;
  source_page_id: string | null;
  review_status: string;
  predicted_value: string | null;
  confidence: number | null;
};
export type Doc = {
  id: string;
  session_id: string;
  employee_id: string;
  employee_code: string;
  employee_name: string;
  type_code: string;
  title: string;
  review_status: string;
  version: number;
  identity_match: boolean | null;
  identity_note: string | null;
  created_at: string;
  verified_at: string | null;
  pages: { id: string; page_order: number; image_url: string }[];
  fields: Field[];
};
export type Stats = {
  employee_count: number;
  page_count: number;
  documents: Record<string, number>;
  jobs: Record<string, number>;
  demo_mode: boolean;
};
export type Receipt = {
  id: string;
  client_page_id: string;
  sha256: string;
  page_order: number;
};
export type Job = {
  id: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  error_code: string | null;
};
export type CaptureSession = {
  id: string;
  version: number;
  status: string;
  pages: Receipt[];
  job: Job | null;
  document_ids: string[];
};
