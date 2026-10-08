import { useEffect, useState } from 'react';
import { useAccountsStore } from '../stores/accounts';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { Select, TextInput } from '../components/Field';
import { Banner } from '../components/Banner';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { Search, Trash2, LoaderCircle, Mail, Camera, Eye, Copy, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { useUIStore } from '../stores/ui';
import type { AccountStatus, Platform } from '../types';

type SortBy = 'created_at' | 'handle' | 'platform';
type SortDir = 'asc' | 'desc';

export function ContasPage() {
  const { accounts, totalUnfiltered, initialLoad, loading, error, fetchAccounts, filterPlatform, filterStatus, searchQuery, setSearchQuery, setFilterPlatform, setFilterStatus, deleteAccount } = useAccountsStore();
  const { navigate } = useUIStore();
  const [sortBy, setSortBy] = useState<SortBy>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    fetchAccounts();
    const interval = setInterval(fetchAccounts, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSort = (column: SortBy) => {
    if (sortBy === column) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortBy(column);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ column }: { column: SortBy }) => {
    if (sortBy !== column) return <ArrowUpDown size={14} style={{ opacity: 0.5, marginLeft: 4 }} />;
    return sortDir === 'asc' ? <ArrowUp size={14} style={{ marginLeft: 4 }} /> : <ArrowDown size={14} style={{ marginLeft: 4 }} />;
  };

  const filtered = accounts.filter((a) => {
    if (searchQuery && !(a.handle?.toLowerCase().includes(searchQuery.toLowerCase()))) return false;
    if (filterPlatform && a.platform !== filterPlatform) return false;
    if (filterStatus && a.status !== filterStatus) return false;
    return true;
  }).sort((a, b) => {
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

  const getStatusTone = (status: AccountStatus) => {
    switch (status) {
      case 'ready': return 'success';
      case 'creating': return 'warning';
      case 'failed': return 'danger';
      case 'blocked': return 'neutral';
    }
  };

  const getPlatformIcon = (platform: Platform) => {
    return platform === 'outlook' ? <Mail size={14} /> : <Camera size={14} />;
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  };

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const deleteAccountData = accounts.find((a) => a.id === deleteId);

  if (initialLoad && !accounts.length) {
    return (
      <div className="page">
        <div className="pageHeader">
          <h1 className="t-titulo-pagina">Contas</h1>
        </div>
        <div className="filters" style={{ marginBottom: 'var(--sp-5)' }}>
          <div style={{ flex: '1 1 200px', height: '40px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)' }} />
          <div style={{ width: '180px', height: '40px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)' }} />
          <div style={{ width: '180px', height: '40px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)' }} />
        </div>
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} style={{ height: '40px', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--sp-2)' }} />
        ))}
      </div>
    );
  }

  if (error && !accounts.length) {
    return (
      <div className="page">
        <div className="pageHeader">
          <h1 className="t-titulo-pagina">Contas</h1>
        </div>
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          Erro ao carregar contas: {error}
          <Button variant="dangerGhost" size="sm" onClick={fetchAccounts} style={{ marginLeft: 'auto' }}>
            Tentar novamente
          </Button>
        </Banner>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="pageHeader">
        <div>
          <h1 className="t-titulo-pagina">Contas</h1>
          <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
            mostrando {filtered.length} de {totalUnfiltered} contas
          </p>
        </div>
        <Button variant="primary" onClick={() => navigate('criar')}>
          Nova Conta
        </Button>
      </div>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          {error}
          <Button variant="dangerGhost" size="sm" onClick={() => useAccountsStore.getState().clearError()} style={{ marginLeft: 'auto' }}>
            Fechar
          </Button>
        </Banner>
      )}

      {/* Filters */}
      <div className="filters" style={{ marginBottom: 'var(--sp-5)' }}>
        <div style={{ position: 'relative', flex: '1 1 200px' }}>
          <Search size={14} style={{ position: 'absolute', left: 'var(--sp-3)', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none' }} />
          <TextInput
            placeholder="Buscar por email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: 'var(--sp-8)' }}
            aria-label="Buscar por email"
          />
        </div>
        <Select
          value={filterPlatform ?? ''}
          onChange={(e) => setFilterPlatform((e.target.value as Platform) || null)}
          aria-label="Filtrar por plataforma"
        >
          <option value="">Todas plataformas</option>
          <option value="outlook">Outlook</option>
          <option value="instagram">Instagram</option>
        </Select>
        <Select
          value={filterStatus ?? ''}
          onChange={(e) => setFilterStatus((e.target.value as AccountStatus) || null)}
          aria-label="Filtrar por status"
        >
          <option value="">Todos status</option>
          <option value="ready">Prontas</option>
          <option value="creating">Criando</option>
          <option value="failed">Falhas</option>
          <option value="blocked">Bloqueadas</option>
        </Select>
        <Button variant="ghost" size="sm" onClick={fetchAccounts} loading={loading}>
          Atualizar
        </Button>
      </div>

      {/* Table */}
      {loading && accounts.length === 0 ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--sp-10)' }}>
          <LoaderCircle size={24} className="spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 'var(--sp-10) 0', color: 'var(--text-3)' }}>
          <p className="t-rotulo">Nenhuma conta encontrada</p>
          <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
            {accounts.length === 0 ? 'Crie sua primeira conta para começar.' : 'Tente ajustar os filtros.'}
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <caption className="sr-only">Lista de contas</caption>
            <thead>
              <tr>
                <th>Plataforma</th>
                <th onClick={() => handleSort('handle')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <span style={{ display: 'flex', alignItems: 'center' }}>Email / Handle <SortIcon column="handle" /></span>
                </th>
                <th>Status</th>
                <th>Persona</th>
                <th onClick={() => handleSort('created_at')} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  <span style={{ display: 'flex', alignItems: 'center' }}>Criada em <SortIcon column="created_at" /></span>
                </th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((account) => (
                <tr key={account.id}>
                  <td>
                    <Badge tone={account.platform === 'outlook' ? 'info' : 'warning'}>
                      {getPlatformIcon(account.platform)}
                      {account.platform}
                    </Badge>
                  </td>
                  <td>
                    {account.platform === 'instagram' ? (
                      <div>
                        {account.handle ? (
                          account.handle.includes('@') ? (
                            <span className="coin truncate" style={{ display: 'block', maxWidth: '280px' }}>
                              @{account.handle.split('@')[0]}
                            </span>
                          ) : (
                            <a
                              href={`https://www.instagram.com/${account.handle}/`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="coin truncate"
                              style={{ display: 'block', maxWidth: '280px', color: 'var(--accent-text)', textDecoration: 'none' }}
                              onMouseEnter={(e) => { e.currentTarget.style.textDecoration = 'underline'; }}
                              onMouseLeave={(e) => { e.currentTarget.style.textDecoration = 'none'; }}
                            >
                              @{account.handle}
                            </a>
                          )
                        ) : (
                          <span className="t-legenda" style={{ display: 'block', fontSize: 'var(--fs-2xs)', color: 'var(--text-3)' }}>
                            handle não capturado
                          </span>
                        )}
                        <span className="t-legenda" style={{ display: 'block', fontSize: 'var(--fs-2xs)', color: 'var(--text-3)' }}>
                          {account.email ? `vinculado a ${account.email}` : ''}
                        </span>
                      </div>
                    ) : (
                      <span className="coin truncate" style={{ display: 'block', maxWidth: '280px' }}>
                        {account.handle}
                      </span>
                    )}
                  </td>
                  <td>
                    <Badge tone={getStatusTone(account.status)}>
                      {account.status === 'creating' && <LoaderCircle size={12} className="spin" />}
                      {account.status}
                    </Badge>
                    {account.error_message && (
                      <span className="t-legenda" style={{ display: 'block', marginTop: 'var(--sp-1)', color: 'var(--danger-text)' }}>
                        {account.error_message.slice(0, 50)}...
                      </span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                      <span className="t-legenda coin" style={{ fontSize: 'var(--fs-xs)' }} title={account.profile_id}>
                        {account.profile_id.slice(0, 12)}...
                      </span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(account.profile_id, account.id)}
                        aria-label={`Copiar ID da persona ${account.profile_id}`}
                        style={{ background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', padding: 4, borderRadius: 'var(--radius-sm)' }}
                      >
                        <Copy size={14} />
                      </button>
                      {copiedId === account.id && <span style={{ fontSize: 'var(--fs-2xs)', color: 'var(--success-text)' }}>Copiado!</span>}
                    </div>
                  </td>
                  <td>
                    <span className="t-legenda" style={{ fontSize: 'var(--fs-xs)' }}>
                      {formatDateTime(account.created_at)}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Eye}
                        onClick={() => navigate('contas', account.id)}
                        label="Ver detalhes"
                      />
                      <Button
                        variant="dangerGhost"
                        size="sm"
                        icon={Trash2}
                        onClick={() => setDeleteId(account.id)}
                        label="Deletar"
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && accounts.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--sp-6)' }}>
          <LoaderCircle size={24} className="spin" style={{ color: 'var(--accent)' }} />
        </div>
      )}

      <ConfirmDialog
        open={deleteId !== null}
        title="Deletar conta"
        description={deleteAccountData ? `Deseja deletar a conta ${deleteAccountData.platform}: ${deleteAccountData.handle}? Esta ação não pode ser desfeita.` : ''}
        confirmLabel="Deletar"
        cancelLabel="Cancelar"
        destructive
        onConfirm={() => { if (deleteId) deleteAccount(deleteId); }}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
