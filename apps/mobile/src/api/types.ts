export interface User {
  id: string;
  organization_id: string;
  role: string;
  name: string;
  phone_e164: string;
  email: string | null;
  language: string;
  last_seen_at: string | null;
}

export interface Organization {
  id: string;
  name: string;
  phone_e164: string;
  email: string | null;
  default_language: string;
  tier: string;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  user: User;
  organization: Organization;
}

export interface DashboardSummary {
  month: string;
  collected: string;
  target: string;
  paid_count: number;
  pending_count: number;
  overdue_count: number;
  needs_attention: NeedsAttentionItem[];
  recently_paid: RecentlyPaidItem[];
}

export interface NeedsAttentionItem {
  tenant_id: string;
  tenant_name: string;
  unit_identifier: string;
  amount_due: string;
  due_date: string;
  days_overdue: number;
}

export interface RecentlyPaidItem {
  payment_id: string;
  tenant_id: string;
  tenant_name: string;
  amount: string;
  paid_on: string;
}

export interface Tenant {
  id: string;
  organization_id: string;
  name: string;
  phone_e164: string;
  email: string | null;
  language: string;
  whatsapp_opt_in: boolean;
  email_opt_in: boolean;
  notes: string | null;
  archived_at: string | null;
  created_at: string;
}

export interface Property {
  id: string;
  organization_id: string;
  name: string;
  type: string;
  address_line: string | null;
  area: string | null;
  city: string;
  pincode: string | null;
  archived_at: string | null;
  created_at: string;
}

export interface Lease {
  id: string;
  organization_id: string;
  unit_id: string;
  tenant_id: string;
  start_date: string;
  end_date: string;
  monthly_rent: string;
  security_deposit: string;
  billing_day: number;
  status: string;
  renewal_status: string;
  notes: string | null;
}

export interface LeaseExpiringItem {
  lease_id: string;
  tenant_id: string;
  tenant_name: string;
  unit_identifier: string;
  end_date: string;
  days_until_expiry: number;
}

export interface Invoice {
  id: string;
  tenant_id: string;
  billing_month: string;
  due_date: string;
  amount_due: string;
  amount_paid: string;
  status: string;
}

export interface ReminderResult {
  sent: number;
  skipped: number;
  channels: string[];
  detail: string;
}

export interface Payment {
  id: string;
  tenant_id: string;
  invoice_id: string | null;
  amount: string;
  paid_on: string;
  method: string;
  reference: string | null;
  notes: string | null;
  match_confidence: string;
  matched_automatically: boolean;
  created_at: string;
}
