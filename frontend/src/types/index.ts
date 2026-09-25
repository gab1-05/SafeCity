/**
 * SafeCity domain types — mirror backend serializers.
 * Keep in sync with the Django serializers (see docs/api-schema.yaml).
 */

export type UserRole =
  | "citizen"
  | "department_staff"
  | "emergency_responder"
  | "volunteer"
  | "city_admin"
  | "superuser";

export type IncidentStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "verified"
  | "rejected"
  | "duplicate"
  | "assigned"
  | "in_progress"
  | "awaiting_info"
  | "escalated"
  | "resolved"
  | "closed"
  | "reopened";

export type Severity = "low" | "medium" | "high" | "critical";
export type Urgency = "low" | "normal" | "urgent" | "immediate";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  phone?: string;
  role: UserRole;
  department?: { id: string; name: string; code?: string } | null;
  is_active?: boolean;
  is_locked?: boolean;
  locked_until?: string | null;
  prefers_anonymous_reporting?: boolean;
  language?: string;
}

export interface IncidentCategory {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon: string;
  is_emergency_category: boolean;
  requires_media: boolean;
  display_order: number;
}

export interface Ward {
  id: string;
  name: string;
  code: string;
  latitude: number | null;
  longitude: number | null;
  zone?: { id: string; name: string; code: string } | null;
}

export interface Incident {
  id: string;
  reference_number: string;
  title: string;
  description: string;
  category: IncidentCategory | null;
  subcategory: string;
  severity: Severity;
  urgency: Urgency;
  status: IncidentStatus;
  reporter_display: string;
  is_reporter?: boolean;
  is_anonymous: boolean;
  department: { id: string; name: string } | null;
  department_name: string | null;
  assigned_staff_name: string | null;
  assigned_responder_name: string | null;
  latitude: number;
  longitude: number;
  address_public: string;
  address_private: string;
  ward_name: string | null;
  landmark: string;
  is_emergency: boolean;
  sla_deadline: string | null;
  sla_breached: boolean;
  is_overdue: boolean;
  duplicate_of: string | null;
  citizen_confirmed_resolution: boolean;
  satisfaction_rating: number | null;
  resolution_summary: string;
  submitted_at: string | null;
  verified_at: string | null;
  assigned_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  id: string;
  from_status: string | null;
  to_status: string;
  actor: string;
  note: string;
  is_internal: boolean;
  created_at: string;
}

export interface IncidentComment {
  id: string;
  author_name: string;
  body: string;
  is_internal: boolean;
  created_at: string;
}

export interface IncidentMediaItem {
  id: string;
  url: string | null;
  media_type: "image" | "video" | "document";
  mime_type: string;
  size_bytes: number;
  caption: string;
  thumbnail: string | null;
  created_at: string;
}

export interface Notification {
  id: string;
  verb: string;
  title: string;
  body: string;
  incident_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface Announcement {
  id: string;
  title: string;
  body: string;
  audience: string;
  is_pinned: boolean;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AnalyticsSummary {
  total: number;
  in_window: number;
  open: number;
  new_in_window: number;
  awaiting_verification: number;
  high_priority: number;
  overdue: number;
  emergency: number;
  resolved_in_window: number;
  reopened_in_window: number;
  duplicates_in_window: number;
  avg_response_minutes: number | null;
  avg_resolution_minutes: number | null;
  sla_compliance_pct: number | null;
  resolution_rate_pct: number | null;
  avg_satisfaction: number | null;
}

export interface ApiError {
  detail: string;
  code: string;
  errors: Record<string, string[]>;
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const URGENCY_LABELS: Record<Urgency, string> = {
  low: "Not urgent",
  normal: "Normal",
  urgent: "Urgent",
  immediate: "Immediate danger",
};

export const STATUS_LABELS: Record<IncidentStatus, string> = {
  draft: "Draft",
  submitted: "Submitted",
  under_review: "Under Review",
  verified: "Verified",
  rejected: "Rejected",
  duplicate: "Duplicate",
  assigned: "Assigned",
  in_progress: "In Progress",
  awaiting_info: "Awaiting Info",
  escalated: "Escalated",
  resolved: "Resolved",
  closed: "Closed",
  reopened: "Reopened",
};
