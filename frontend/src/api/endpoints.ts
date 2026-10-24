/** One function per backend endpoint, grouped by feature. Pages never call fetch directly. */
import { request } from "./client";
import type {
  AuditEntry, DailyRow, Dashboard, HistoryEntry, Incident, IncidentType, Notification, Package, PackageCondition,
  PackageSize, PackageStatus, Page, PickupCode, PickupInput, PickupRecord, RegisterPackageInput, Role,
  SignupInput, StorageLocation, TokenResponse, User, UserBrief,
} from "./types";

export interface PackageQuery {
  q?: string;
  status?: PackageStatus[];
  condition?: PackageCondition;
  overdue?: boolean;
  arrived_from?: string;
  arrived_to?: string;
  page?: number;
  page_size?: number;
}

export const authApi = {
  login: (identifier: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: { identifier, password } }),
  signup: (input: SignupInput) =>
    request<TokenResponse>("/auth/signup", { method: "POST", body: input }),
  resetPassword: (identifier: string, new_password: string) =>
    request<TokenResponse>("/auth/reset-password", { method: "POST", body: { identifier, new_password } }),
  me: () => request<User>("/auth/me"),
};

export const packagesApi = {
  list: (query: PackageQuery = {}) => request<Page<Package>>("/packages", { query: { ...query } }),
  get: (id: number) => request<Package>(`/packages/${id}`),
  history: (id: number) => request<HistoryEntry[]>(`/packages/${id}/history`),
  register: (input: RegisterPackageInput, idempotencyKey: string) =>
    request<Package>("/packages", { method: "POST", body: input, idempotencyKey }),
  assignStorage: (id: number, locationId: number | null, markReady: boolean) =>
    request<Package>(`/packages/${id}/storage`, { method: "POST", body: { location_id: locationId, mark_ready: markReady } }),
  identifyRecipient: (id: number, learnerId: string) =>
    request<Package>(`/packages/${id}/recipient`, { method: "POST", body: { learner_institutional_id: learnerId } }),
  transition: (id: number, target: PackageStatus, reason?: string) =>
    request<Package>(`/packages/${id}/transitions`, { method: "POST", body: { target_status: target, reason } }),
  requestReturn: (id: number, reason: string) =>
    request<Package>(`/packages/${id}/return-request`, { method: "POST", body: { reason } }),
  initiateReturn: (body: { package_id?: number | null; courier_name?: string | null; tracking_id?: string | null; reason: string; size?: PackageSize; notes?: string | null }) =>
    request<Package>("/packages/return-initiate", { method: "POST", body }),
};

export const pickupApi = {
  requestCode: (packageId: number) => request<PickupCode>(`/packages/${packageId}/pickup-request`, { method: "POST" }),
  verify: (input: PickupInput) =>
    request<{ verified: boolean; package: Package }>("/pickups/verify", { method: "POST", body: input }),
  complete: (input: PickupInput, idempotencyKey: string) =>
    request<PickupRecord>("/pickups/complete", { method: "POST", body: input, idempotencyKey }),
  history: (page = 1) => request<Page<PickupRecord>>("/pickups", { query: { page } }),
};

export const storageApi = {
  list: (activeOnly = false) => request<StorageLocation[]>("/storage-locations", { query: { active_only: activeOnly } }),
  create: (body: { code: string; description?: string; capacity: number; max_package_size: PackageSize }) =>
    request<StorageLocation>("/storage-locations", { method: "POST", body }),
  update: (id: number, body: Partial<Pick<StorageLocation, "description" | "capacity" | "max_package_size" | "is_active">>) =>
    request<StorageLocation>(`/storage-locations/${id}`, { method: "PATCH", body }),
};

export const usersApi = {
  searchLearners: (q: string) => request<UserBrief[]>("/users/learners", { query: { q } }),
  list: (query: { q?: string; role?: Role; page?: number }) => request<Page<User>>("/users", { query }),
  create: (body: { institutional_id: string; full_name: string; email: string; phone?: string; role: Role; password: string }) =>
    request<User>("/users", { method: "POST", body }),
  update: (id: number, body: { full_name?: string; phone?: string; is_active?: boolean; password?: string }) =>
    request<User>(`/users/${id}`, { method: "PATCH", body }),
};

export const notificationsApi = {
  list: (page = 1) => request<Page<Notification>>("/notifications", { query: { page } }),
  unreadCount: () => request<{ unread: number }>("/notifications/unread-count"),
  markRead: (id: number) => request<Notification>(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => request<{ updated: number }>("/notifications/read-all", { method: "POST" }),
  retryFailed: () =>
    request<{ retried: number; sent: number; failed: number; skipped: number }>("/notifications/retry-failed", { method: "POST" }),
};

export const incidentsApi = {
  list: (query: { status?: "OPEN" | "RESOLVED"; type?: IncidentType; package_id?: number; page?: number } = {}) =>
    request<Page<Incident>>("/incidents", { query }),
  create: (body: { package_id?: number | null; type: IncidentType; description: string; escalate: boolean }) =>
    request<Incident>("/incidents", { method: "POST", body }),
  resolve: (id: number, note: string) =>
    request<Incident>(`/incidents/${id}/resolve`, { method: "POST", body: { resolution_note: note } }),
};

export const reportsApi = {
  dashboard: () => request<Dashboard>("/reports/dashboard"),
  daily: (dateFrom?: string, dateTo?: string) =>
    request<DailyRow[]>("/reports/daily", { query: { date_from: dateFrom, date_to: dateTo } }),
  audit: (query: { action?: string; entity_type?: string; entity_id?: string; date_from?: string; date_to?: string; page?: number }) =>
    request<Page<AuditEntry>>("/audit-logs", { query }),
};
