import { create } from 'zustand';
import { api } from '../services/api';

export interface FarmAccount {
  id: string;
  handle: string;
  platform: 'instagram' | 'outlook';
  status: 'ready' | 'creating' | 'failed' | 'blocked';
  profile_id: string;
  created_at: string;
  email?: string;
  error_message?: string;
  proxy_used?: string;
  updated_at: string;
}

export interface FarmProxy {
  id: string;
  host: string;
  port: number;
  country: string;
  status: 'active' | 'inactive';
  created_at: string;
}

type SortBy = 'created_at' | 'handle' | 'platform';
type SortDir = 'asc' | 'desc';

interface AccountsState {
  accounts: FarmAccount[];
  proxies: FarmProxy[];
  total: number;
  totalUnfiltered: number;
  initialLoad: boolean;
  loading: boolean;
  error: string | null;
  sortBy: SortBy;
  sortDir: SortDir;
  filterPlatform: string;
  filterStatus: string;
  searchTerm: string;
  searchQuery: string;

  fetchAccounts: () => Promise<void>;
  fetchProxies: () => Promise<void>;
  deleteAccount: (id: string) => Promise<void>;
  deleteProxy: (id: string) => Promise<void>;
  createAccount: (data: CreateAccountData) => Promise<void>;
  createProxy: (data: CreateProxyData) => Promise<void>;
  setSort: (sortBy: SortBy) => void;
  setFilterPlatform: (platform: string) => void;
  setFilterStatus: (status: string) => void;
  setSearchTerm: (term: string) => void;
  setSearchQuery: (term: string) => void;
  clearError: () => void;
  getFilteredAccounts: () => FarmAccount[];
  getProxyStats: () => { active: number; total: number };
}

export interface CreateAccountData {
  firstName: string;
  profileId?: string;
  birthDate: string;
  platforms: string[];
}

export interface CreateProxyData {
  host: string;
  port: number;
  country: string;
  username?: string;
  password?: string;
}

export const useFarmAccountsStore = create<AccountsState>((set, get) => ({
  accounts: [],
  proxies: [],
  total: 0,
  totalUnfiltered: 0,
  initialLoad: true,
  loading: false,
  error: null,
  sortBy: 'created_at',
  sortDir: 'desc',
  filterPlatform: '',
  filterStatus: '',
  searchTerm: '',
  searchQuery: '',

  fetchAccounts: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.listAccounts();
      const accounts: FarmAccount[] = (data as any).items || (data as any).accounts || [];
      set({
        accounts,
        total: accounts.length,
        totalUnfiltered: accounts.length,
        initialLoad: false,
        loading: false,
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erro desconhecido', initialLoad: false, loading: false });
    }
  },

  fetchProxies: async () => {
    set({ loading: true, error: null });
    try {
      const data = await api.listProxies();
      const proxies: FarmProxy[] = Array.isArray(data) ? data : (data as any).proxies || [];
      set({ proxies, loading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erro desconhecido', loading: false });
    }
  },

  deleteAccount: async (id: string) => {
    try {
      await api.deleteAccount(id);
      await get().fetchAccounts();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erro ao deletar conta' });
    }
  },

  deleteProxy: async (id: string) => {
    try {
      await api.deleteProxy(id);
      await get().fetchProxies();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Erro ao deletar proxy' });
    }
  },

  createAccount: async (data: CreateAccountData) => {
    await api.createAccount(
      data.profileId || `persona-${Date.now()}`,
      data.platforms,
      {
        first_name: data.firstName,
        birth_date: data.birthDate,
      }
    );
    await get().fetchAccounts();
  },

  createProxy: async (data: CreateProxyData) => {
    await api.addProxy({
      host: data.host,
      port: data.port,
      username: data.username,
      password: data.password,
      country: data.country,
    });
    await get().fetchProxies();
  },

  setSort: (sortBy: SortBy) => {
    const current = get().sortBy;
    const sortDir = current === sortBy && get().sortDir === 'desc' ? 'asc' : 'desc';
    set({ sortBy, sortDir });
  },

  setFilterPlatform: (platform: string) => set({ filterPlatform: platform }),
  setFilterStatus: (status: string) => set({ filterStatus: status }),
  setSearchTerm: (term: string) => set({ searchTerm: term, searchQuery: term }),
  setSearchQuery: (term: string) => set({ searchTerm: term, searchQuery: term }),
  clearError: () => set({ error: null }),

  getFilteredAccounts: () => {
    const { accounts, searchTerm, filterPlatform, filterStatus, sortBy, sortDir } = get();
    let filtered = [...accounts];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter((a) =>
        (a.handle?.toLowerCase().includes(term)) ||
        a.email?.toLowerCase().includes(term) ||
        a.profile_id.toLowerCase().includes(term)
      );
    }

    if (filterPlatform) {
      filtered = filtered.filter((a) => a.platform === filterPlatform);
    }

    if (filterStatus) {
      filtered = filtered.filter((a) => a.status === filterStatus);
    }

    filtered.sort((a, b) => {
      let cmp = 0;
      if (sortBy === 'created_at') {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortBy === 'handle') {
        cmp = a.handle.localeCompare(b.handle);
      } else if (sortBy === 'platform') {
        cmp = a.platform.localeCompare(b.platform);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return filtered;
  },

  getProxyStats: () => {
    const { proxies } = get();
    const active = proxies.filter((p) => p.status === 'active').length;
    return { active, total: proxies.length };
  },
}));

// Compatibility alias for existing pages
export const useAccountsStore = useFarmAccountsStore;
