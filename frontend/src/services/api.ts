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
};
