// Types mirror the backend Pydantic schemas (see backend/app/schemas).
export type Role = "LEARNER" | "SECURITY" | "ADMIN";

export type PackageStatus =
  | "RECEIVED" | "VERIFIED" | "STORED" | "READY_FOR_PICKUP" | "PICKUP_REQUESTED" | "COLLECTED"
  | "UNIDENTIFIED" | "DAMAGED" | "UNDER_INVESTIGATION" | "RETURN_REQUESTED" | "RETURNED" | "LOST";

export type PackageSize = "SMALL" | "MEDIUM" | "LARGE";
export type PackageCondition = "GOOD" | "DAMAGED";
export type IncidentType =
  | "DAMAGE" | "UNIDENTIFIED_RECIPIENT" | "LEARNER_REPORTED_ISSUE" | "MISSING_PACKAGE" | "OPERATIONAL";

export interface Page<T> { items: T[]; total: number; page: number; page_size: number }

export interface UserBrief { id: number; institutional_id: string; full_name: string }

export interface User extends UserBrief {
  email: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse { access_token: string; token_type: string; expires_in: number; user: User }

export interface SignupInput {
  institutional_id: string;
  full_name: string;
  email: string;
  phone?: string | null;
  password: string;
}

export interface PackageAction { action: string; label: string; target_status: PackageStatus; dedicated: boolean }

export interface Package {
  id: number;
  internal_code: string;
  courier_name: string;
  tracking_id: string | null;
  recipient: UserBrief | null;
  recipient_hint: string | null;
  size: PackageSize;
  condition: PackageCondition;
  condition_notes: string | null;
  status: PackageStatus;
  status_label: string;
  storage_location: { id: number; code: string } | null;
  arrived_at: string;
  ready_at: string | null;
  closed_at: string | null;
  received_by: UserBrief | null;
  is_overdue: boolean;
  notes: string | null;
  available_actions: PackageAction[];
  updated_at: string;
}

export interface HistoryEntry {
  from_status: PackageStatus | null;
  to_status: PackageStatus;
  to_label: string;
  reason: string | null;
  changed_by: UserBrief | null;
  created_at: string;
}

export interface RegisterPackageInput {
  courier_name: string;
  tracking_id?: string | null;
  recipient_institutional_id?: string | null;
  recipient_hint?: string | null;
  size: PackageSize;
  condition: PackageCondition;
  condition_notes?: string | null;
  arrived_at?: string | null;
  notes?: string | null;
}

export interface PickupCode { package_id: number; internal_code: string; code: string; expires_at: string }

export interface PickupInput { package_code: string; learner_institutional_id: string; code: string }

export interface PickupRecord {
  id: number;
  package_id: number;
  internal_code: string;
  courier_name: string;
  learner_id: number;
  handed_over_by: UserBrief | null;
  storage_location_code: string | null;
  collected_at: string;
}

export interface StorageLocation {
  id: number;
  code: string;
  description: string | null;
  capacity: number;
  occupied_count: number;
  max_package_size: PackageSize;
  is_active: boolean;
}

export interface Notification {
  id: number;
  package_id: number | null;
  channel: "IN_APP" | "EMAIL";
  title: string;
  message: string;
  delivery_status: "PENDING" | "SENT" | "FAILED";
  created_at: string;
  read_at: string | null;
}

export interface IncidentComment {
  id: string;
  author_id: number;
  author_name: string;
  author_role: Role;
  message: string;
  created_at: string;
}

export interface Incident {
  id: number;
  package_id: number | null;
  package_code: string | null;
  type: IncidentType;
  status: "OPEN" | "RESOLVED";
  description: string;
  reported_by: UserBrief;
  resolved_by: UserBrief | null;
  resolution_note: string | null;
  comments?: IncidentComment[];
  created_at: string;
  resolved_at: string | null;
}

export interface AuditEntry {
  id: number;
  actor: UserBrief | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface Dashboard {
  by_status: Record<PackageStatus, number>;
  received: number;
  in_custody: number;
  overdue: number;
  awaiting_storage?: number;
  damaged_condition: number;
  received_today: number;
  collected_today: number;
  open_incidents: number;
  failed_notifications: number;
  storage_capacity: number;
  storage_occupied: number;
  collection_deadline_days: number;
}

export interface DailyRow { date: string; received: number; collected: number }
