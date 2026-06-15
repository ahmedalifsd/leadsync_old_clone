// Lead types
export interface Lead {
  id: number;
  owner: number;
  owner_name: string;
  created_by: number;
  created_by_name: string;
  category?: number;
  category_name?: string;
  category_other?: string;
  source?: number;
  source_name?: string;
  source_other?: string;
  client_name: string;
  contact_number?: string;
  email?: string;
  requirement?: string;
  status: LeadStatus;
  follow_up_date?: string;
  notes?: string;
  assigned_to?: number;
  assigned_to_name?: string;
  lead_score: number;
  budget?: number;
  timeline?: string;
  decision_maker: boolean;
  converted_to_customer: boolean;
  conversion_date?: string;
  contact_attempts: number;
  status_repeat_count: number;
  custom_fields?: Record<string, any>;
  created_at: string;
  updated_at: string;
  deleted_at?: string;
  deleted_by?: number;
  assignment_date?: string;
}

export type LeadStatus =
  | 'new'
  | 'not_contacted'
  | 'contacted'
  | 'no_response'
  | 'interested'
  | 'not_interested'
  | 'qualified'
  | 'proposal'
  | 'negotiation'
  | 'won'
  | 'lost';

export const LEAD_STATUS_LABELS: Record<LeadStatus, string> = {
  new: 'New',
  not_contacted: 'Not Contacted',
  contacted: 'Contacted',
  no_response: 'No Response',
  interested: 'Interested',
  not_interested: 'Not Interested',
  qualified: 'Qualified',
  proposal: 'Proposal Sent',
  negotiation: 'Negotiation',
  won: 'Won',
  lost: 'Lost',
};

export const LEAD_STATUS_COLORS: Record<LeadStatus, string> = {
  new: 'bg-blue-100 text-blue-800',
  not_contacted: 'bg-gray-100 text-gray-800',
  contacted: 'bg-purple-100 text-purple-800',
  no_response: 'bg-red-100 text-red-800',
  interested: 'bg-yellow-100 text-yellow-800',
  not_interested: 'bg-orange-100 text-orange-800',
  qualified: 'bg-green-100 text-green-800',
  proposal: 'bg-cyan-100 text-cyan-800',
  negotiation: 'bg-indigo-100 text-indigo-800',
  won: 'bg-emerald-100 text-emerald-800',
  lost: 'bg-slate-100 text-slate-800',
};

// Category types
export interface Category {
  id: number;
  name: string;
  created_at: string;
}

// Source types
export interface Source {
  id: number;
  name: string;
  created_at: string;
}

// User types
export interface UserProfile {
  id: number;
  role: 'owner' | 'staff' | 'super_admin';
  phone_number?: string;
  company_name?: string;
  is_approved: boolean;
  pending_boss_username?: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  date_joined: string;
  profile?: UserProfile;
}

// Activity Log types
export interface ActivityLog {
  id: number;
  user: number;
  user_name: string;
  action: 'create' | 'update' | 'delete' | 'view' | 'import' | 'export' | 'login' | 'logout';
  target_model: string;
  target_id?: number;
  target_name: string;
  details?: string;
  ip_address?: string;
  user_agent?: string;
  timestamp: string;
}

// API Response types
export interface PaginatedResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

// Dashboard types
export interface DashboardStats {
  total_leads: number;
  new_leads: number;
  contacted: number;
  interested: number;
  qualified: number;
  won: number;
  lost: number;
  conversion_rate: number;
}

export interface LeadStatusDistribution {
  [status: string]: {
    label: string;
    count: number;
  };
}

// Filter types
export interface LeadFilters {
  status?: LeadStatus;
  category?: number;
  source?: number;
  assigned_to?: number;
  search?: string;
  page?: number;
  page_size?: number;
}

// Form types
export interface LeadFormData {
  category?: number;
  category_other?: string;
  source?: number;
  source_other?: string;
  client_name: string;
  contact_number?: string;
  email?: string;
  requirement?: string;
  status: LeadStatus;
  follow_up_date?: string;
  notes?: string;
  assigned_to?: number;
  lead_score?: number;
  budget?: number;
  timeline?: string;
  decision_maker?: boolean;
  converted_to_customer?: boolean;
  custom_fields?: Record<string, any>;
}
