import { LayoutDashboard, Users, PlusCircle, Network, Menu, X, type LucideIcon } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useUIStore } from '../stores/ui';
import { VERSION } from '../version';

type Page = 'painel' | 'contas' | 'criar' | 'proxies';

interface NavItem {
  page: Page;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { page: 'painel', label: 'Painel', icon: LayoutDashboard },
  { page: 'contas', label: 'Contas', icon: Users },
  { page: 'criar', label: 'Criar Conta', icon: PlusCircle },
  { page: 'proxies', label: 'Proxies', icon: Network },
];

export function Sidebar() {
  const { currentPage, navigate, sidebarOpen, isMobile, setSidebarOpen } = useUIStore();
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobile && sidebarOpen) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isMobile, sidebarOpen, setSidebarOpen]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      setSidebarOpen(false);
    }
  };

  return (
    <>
      {isMobile && sidebarOpen && (
        <div
          ref={overlayRef}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'var(--overlay)',
            zIndex: 'calc(var(--z-panel) - 1)',
          }}
          onClick={handleOverlayClick}
          aria-hidden="true"
        />
      )}

      <aside
        id="sidebar-nav"
        aria-label="Navegação principal"
        aria-hidden={!sidebarOpen || undefined}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          bottom: 0,
          width: '240px',
          background: 'var(--surface-1)',
          borderRight: '1px solid var(--border-1)',
          zIndex: 'var(--z-panel)',
          display: 'flex',
          flexDirection: 'column',
          transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform var(--dur-med) var(--ease)',
        }}
      >
        <div
          style={{
            padding: 'var(--sp-4) var(--sp-5)',
            borderBottom: '1px solid var(--border-1)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--sp-3)',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-on-accent)',
              fontWeight: 'var(--fw-semibold)',
              fontSize: 'var(--fs-sm)',
            }}
          >
            AF
          </div>
          <div>
            <div style={{ fontSize: 'var(--fs-md)', fontWeight: 'var(--fw-semibold)', color: 'var(--text-1)' }}>
              Android Farm
            </div>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>Gerenciamento</div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: 'var(--sp-3)' }}>
          {NAV_ITEMS.map(({ page, label, icon: Icon }) => (
            <button
              key={page}
              onClick={() => {
                navigate(page);
                if (isMobile) setSidebarOpen(false);
              }}
              aria-current={currentPage === page ? 'page' : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--sp-3)',
                width: '100%',
                padding: 'var(--sp-3) var(--sp-4)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--fs-sm)',
                fontWeight: currentPage === page ? 'var(--fw-semibold)' : 'var(--fw-medium)',
                color: currentPage === page ? 'var(--accent-text)' : 'var(--text-2)',
                background: currentPage === page ? 'var(--accent-soft)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease)',
              }}
              onMouseEnter={(e) => {
                if (currentPage !== page) {
                  (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-3)';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-1)';
                }
              }}
              onMouseLeave={(e) => {
                if (currentPage !== page) {
                  (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-2)';
                }
              }}
            >
              <Icon size={16} aria-hidden />
              {label}
            </button>
          ))}
        </nav>

        <div
          style={{
            padding: 'var(--sp-4) var(--sp-5)',
            borderTop: '1px solid var(--border-1)',
            fontSize: 'var(--fs-xs)',
            color: 'var(--text-3)',
            textAlign: 'center',
          }}
        >
          v{VERSION}
        </div>
      </aside>
    </>
  );
}

export function Topbar() {
  const { toggleSidebar, isMobile, sidebarOpen } = useUIStore();

  return (
    <header
      style={{
        position: 'sticky',
        top: 0,
        height: 'var(--topbar-h)',
        background: 'var(--surface-1)',
        borderBottom: '1px solid var(--border-1)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 var(--sp-5)',
        zIndex: 'var(--z-sticky)',
        gap: 'var(--sp-4)',
      }}
    >
      {isMobile && (
        <button
          onClick={toggleSidebar}
          aria-expanded={sidebarOpen}
          aria-controls="sidebar-nav"
          aria-label={sidebarOpen ? 'Fechar menu' : 'Abrir menu'}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 'var(--hit-min)',
            height: 'var(--hit-min)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-2)',
            background: 'transparent',
            color: 'var(--text-2)',
            cursor: 'pointer',
          }}
        >
          {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
      )}
      <h1 style={{ fontSize: 'var(--fs-lg)', fontWeight: 'var(--fw-semibold)', color: 'var(--text-1)' }}>
        Android Farm
      </h1>
    </header>
  );
}
