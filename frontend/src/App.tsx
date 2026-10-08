import { useEffect } from 'react';
import { useUIStore } from './stores/ui';
import { Sidebar, Topbar } from './components/Layout';
import { PainelPage } from './pages/PainelPage';
import { ContasPage } from './pages/ContasPage';
import { ContaDetailPage } from './pages/ContaDetailPage';
import { CriarContaPage } from './pages/CriarContaPage';
import { ProxiesPage } from './pages/ProxiesPage';
import { AccountProgressPage } from './pages/AccountProgressPage';

const PAGE_TITLES: Record<string, string> = {
  painel: 'Painel · Android Farm',
  contas: 'Contas · Android Farm',
  criar: 'Criar Conta · Android Farm',
  proxies: 'Proxies · Android Farm',
  progress: 'Progresso · Android Farm',
  notfound: 'Não encontrado · Android Farm',
};

function NotFoundPage() {
  const { navigate } = useUIStore();
  return (
    <div className="page" style={{ textAlign: 'center', padding: 'var(--sp-10) 0' }}>
      <h1 className="t-titulo-pagina" style={{ marginBottom: 'var(--sp-2)' }}>Página não encontrada</h1>
      <p className="t-legenda" style={{ marginBottom: 'var(--sp-6)' }}>
        O endereço que você acessou não existe no Android Farm.
      </p>
      <button
        onClick={() => navigate('painel')}
        style={{
          padding: 'var(--sp-2) var(--sp-4)',
          borderRadius: 'var(--radius-md)',
          border: 'none',
          background: 'var(--accent)',
          color: 'var(--text-on-accent)',
          cursor: 'pointer',
          fontSize: 'var(--fs-sm)',
          fontWeight: 'var(--fw-medium)',
        }}
      >
        Ir para o Painel
      </button>
    </div>
  );
}

function PageRouter() {
  const { currentPage, selectedAccountId } = useUIStore();

  useEffect(() => {
    document.title = PAGE_TITLES[currentPage] || 'Android Farm';
  }, [currentPage]);

  if (currentPage === 'contas' && selectedAccountId) {
    return <ContaDetailPage />;
  }

  switch (currentPage) {
    case 'painel':
      return <PainelPage />;
    case 'contas':
      return <ContasPage />;
    case 'criar':
      return <CriarContaPage />;
    case 'proxies':
      return <ProxiesPage />;
    case 'progress':
      return <AccountProgressPage />;
    case 'notfound':
      return <NotFoundPage />;
    default:
      return <NotFoundPage />;
  }
}

export function App() {
  const { sidebarOpen } = useUIStore();

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
      <Sidebar />
      <div
        style={{
          flex: 1,
          marginLeft: sidebarOpen ? '240px' : '0',
          transition: 'margin-left var(--dur-med) var(--ease)',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Topbar />
        <main style={{ flex: 1 }}>
          <PageRouter />
        </main>
      </div>
    </div>
  );
}
