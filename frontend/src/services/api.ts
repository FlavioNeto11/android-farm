import type {
  Account,
  AccountListResponse,
  AccountDetail,
  CredentialResponse,
  Evidence,
  Proxy,
  ProxyStats,
  PersonaData,
} from '../types';

const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

export const api = {
  // Accounts
  listAccounts: (params?: { platform?: string; status?: string; profile_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.platform) qs.set('platform', params.platform);
    if (params?.status) qs.set('status', params.status);
    if (params?.profile_id) qs.set('profile_id', params.profile_id);
    const query = qs.toString() ? `?${qs.toString()}` : '';
    return request<AccountListResponse>(`/accounts${query}`);
  },

  getAccount: (id: string) => request<AccountDetail>(`/accounts/${id}`),

  createAccount: (profile_id: string, platforms: string[], persona_data: Partial<PersonaData>) =>
    request<Account>(`/accounts/request`, {
      method: 'POST',
      body: JSON.stringify({ profile_id, platforms, persona_data }),
    }),

  createAccountAI: (data: {
    platform: string;
    use_proxy: boolean;
    proxy_session_id: string;
    first_name?: string;
    last_name?: string;
    birth_date?: string;
    gender?: string;
  }) =>
    request<{ account_id: string; platform: string; status: string; message: string }>(
      `/instagram/create-account-ai`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      },
    ),

  deleteAccount: (id: string) => request<{ message: string; account_id: string }>(`/accounts/${id}`, {
    method: 'DELETE',
  }),

  // Credentials
  getCredentials: (id: string) => request<CredentialResponse>(`/accounts/${id}/credentials`),

  // Evidence
  getEvidence: (id: string) => request<Evidence[]>(`/accounts/${id}/evidence`),

  // Proxies
  listProxies: () => request<Proxy[]>('/proxies'),

  getProxyStats: () => request<ProxyStats>('/proxies/active-count'),

  addProxy: (proxy: { host: string; port: number; username?: string; password?: string; country?: string }) =>
    request<Proxy>('/proxies', {
      method: 'POST',
      body: JSON.stringify(proxy),
    }),

  deleteProxy: (id: string) => request<{ message: string }>(`/proxies/${id}`, {
    method: 'DELETE',
  }),

  // Health
  health: () => request<{ status: string; version: string; platforms: string[] }>('/health'),

  // Personas
  listPersonas: () => fetch('/api/personas').then(r => r.json()),
  getPersona: (id: string) => fetch(`/api/personas/${id}`).then(r => r.json()),
  createAccountForPersona: (id: string) =>
    request<{ account_id: string; persona_id: string; email: string; status: string; message: string }>(
      `/personas/${id}/create-account`,
      { method: 'POST' },
    ),

  // Automation log
  getAutomationLog: (id: string) =>
    request<{ account_id: string; status: string; handle: string | null; error_message: string | null; log: Array<{timestamp: string; message: string}>; created_at: string; updated_at: string }>(
      `/accounts/${id}/automation-log`,
    ),

  // Cleanup stuck accounts
  cleanupStuckAccounts: (minutes?: number) =>
    request<{ cleaned_count: number; minutes_threshold: number; accounts: Array<{account_id: string; platform: string; profile_id: string; created_at: string}> }>(
      `/accounts/cleanup-stuck${minutes ? `?minutes_threshold=${minutes}` : ''}`,
      { method: 'POST' },
    ),
};
