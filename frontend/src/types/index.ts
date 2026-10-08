export interface Account {
  id: string;
  platform: 'outlook' | 'instagram';
  handle: string;
  status: 'creating' | 'ready' | 'failed' | 'blocked';
  profile_id: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
  proxy_used?: string;
}

export interface AccountListResponse {
  accounts: Account[];
  total: number;
}

export interface AccountDetail extends Account {
  credential?: {
    login_identifier: string;
    secret_ref: string;
    status: string;
  };
}

export interface CredentialResponse {
  email: string;
  password: string;
  platform: string;
}

export interface Evidence {
  account_id: string;
  platform?: string;
  evidence_type: 'screenshot' | 'log' | 'metadata';
  timestamp: string;
  screenshot_url?: string;
  description: string;
  filename?: string;
  step?: string;
}

export interface Proxy {
  id: string;
  host: string;
  port: number;
  username?: string;
  country?: string;
  status: 'active' | 'exhausted' | 'blocked';
  used_count: number;
  failed_count: number;
  last_used_at?: string;
}

export interface ProxyStats {
  active_proxies: number;
  total_proxies: number;
}

export interface PersonaData {
  profile_id: string;
  display_name: string;
  first_name: string;
  last_name: string;
  email?: string;
  birth_date?: string;
  gender?: string;
  locale?: string;
  username?: string;
  summary?: string;
}

export type Platform = 'outlook' | 'instagram';
export type AccountStatus = Account['status'];
