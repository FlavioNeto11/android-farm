import { create } from 'zustand';

export type FarmPage = 'painel' | 'contas' | 'criar' | 'proxies' | 'notfound';

interface FarmUiState {
  currentPage: FarmPage;
  selectedAccountId: string | null;
  sidebarOpen: boolean;
  isMobile: boolean;

  navigate: (page: FarmPage, id?: string) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setIsMobile: (mobile: boolean) => void;
  parseHash: (hash: string) => void;
  selectAccount: (id: string | null) => void;
}

function extractIdFromHash(hash: string): { page: FarmPage; id: string | null } {
  const clean = hash.replace(/^#\/?/, '');
  if (clean.startsWith('contas/')) {
    const id = clean.slice(7);
    return { page: 'contas', id: id || null };
  }
  const page = clean.split('/')[0] as FarmPage;
  if (['painel', 'contas', 'criar', 'proxies'].includes(page)) {
    return { page, id: null };
  }
  return { page: 'notfound', id: null };
}

export const useUIStore = create<FarmUiState>((set) => ({
  currentPage: 'painel',
  selectedAccountId: null,
  sidebarOpen: window.innerWidth >= 1024,
  isMobile: window.innerWidth < 1024,

  navigate: (page, id) => {
    const hash = id ? `#/contas/${id}` : `#/${page}`;
    window.location.hash = hash;
    set({ currentPage: page, selectedAccountId: id || null });
  },

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setIsMobile: (mobile) => set({ isMobile: mobile, sidebarOpen: !mobile }),

  parseHash: (hash: string) => {
    const { page, id } = extractIdFromHash(hash);
    set({ currentPage: page, selectedAccountId: id });
  },

  selectAccount: (id) => set({ selectedAccountId: id }),
}));

// Initialize from current hash
const initialHash = window.location.hash;
if (initialHash) {
  useUIStore.getState().parseHash(initialHash);
}

// Listen for hash changes
window.addEventListener('hashchange', () => {
  useUIStore.getState().parseHash(window.location.hash);
});

// Listen for resize
window.addEventListener('resize', () => {
  const isMobile = window.innerWidth < 1024;
  useUIStore.getState().setIsMobile(isMobile);
});
