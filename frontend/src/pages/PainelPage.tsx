import { useEffect, useState, useMemo } from 'react';
import { useAccountsStore } from '../stores/accounts';
import { api } from '../services/api';
import { Badge } from '../components/Badge';
import { Card, CardBody } from '../components/Card';
import { Button } from '../components/Button';
import { Skeleton } from '../components/Skeleton';
import { Banner } from '../components/Banner';
import { PlusCircle, CheckCircle, XCircle, LoaderCircle, Mail } from 'lucide-react';
import { useUIStore } from '../stores/ui';
import type { ProxyStats } from '../types';

export function PainelPage() {
  const { accounts, totalUnfiltered, initialLoad, loading, error, fetchAccounts } = useAccountsStore();
  const { navigate } = useUIStore();
  const [proxyStats, setProxyStats] = useState<ProxyStats | null>(null);
  const [healthLoading, setHealthLoading] = useState(true);
  const [serverStatus, setServerStatus] = useState<{ status: string; platforms: string[] } | null>(null);

  useEffect(() => {
    fetchAccounts();
    api.getProxyStats().then(setProxyStats).catch(() => {});
    api.health().then((r) => {
      setServerStatus({ status: r.status, platforms: r.platforms });
      setHealthLoading(false);
    }).catch(() => setHealthLoading(false));
  }, []);

  const readyCount = useMemo(() => accounts.filter((a) => a.status === 'ready').length, [accounts]);
  const failedCount = useMemo(() => accounts.filter((a) => a.status === 'failed').length, [accounts]);
  const creatingCount = useMemo(() => accounts.filter((a) => a.status === 'creating').length, [accounts]);
  const outlookCount = useMemo(() => accounts.filter((a) => a.platform === 'outlook').length, [accounts]);
  const instagramCount = useMemo(() => accounts.filter((a) => a.platform === 'instagram').length, [accounts]);
  const recentAccounts = useMemo(() =>
    [...accounts].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 5),
    [accounts]
  );

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  };

  if (initialLoad && !accounts.length) {
    return (
      <div className="page">
        <div className="pageHeader">
          <div>
            <h1 className="t-titulo-pagina">Painel de Controle</h1>
            <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
              Gerenciamento de contas Outlook e Instagram
            </p>
          </div>
        </div>
        <div className="statsGrid" style={{ marginBottom: 'var(--sp-6)' }}>
          {Array.from({ length: 7 }).map((_, i) => (
            <Card key={i}>
              <CardBody>
                <Skeleton width="60px" height="32px" />
                <div className="statLabel"><Skeleton width="80px" height="16px" /></div>
              </CardBody>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error && !accounts.length) {
    return (
      <div className="page">
        <div className="pageHeader">
          <h1 className="t-titulo-pagina">Painel de Controle</h1>
        </div>
        <Banner tone="danger">
          Erro ao carregar dados: {error}
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
          <h1 className="t-titulo-pagina">Painel de Controle</h1>
          <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
            Gerenciamento de contas Outlook e Instagram
          </p>
        </div>
        <Button variant="primary" icon={PlusCircle} onClick={() => navigate('criar')}>
          Nova Conta
        </Button>
      </div>

      {error && (
        <Banner tone="danger">
          {error}
          <Button variant="dangerGhost" size="sm" onClick={() => useAccountsStore.getState().clearError()} style={{ marginLeft: 'auto' }}>
            Fechar
          </Button>
        </Banner>
      )}

      {proxyStats && proxyStats.active_proxies === 0 && (
        <Banner tone="warning">
          Nenhum proxy ativo. A criação de contas pode falhar.
          <Button variant="ghost" size="sm" onClick={() => navigate('proxies')} style={{ marginLeft: 'auto' }}>
            Configurar proxies
          </Button>
        </Banner>
      )}

      {/* Stats */}
      <div className="statsGrid" style={{ marginBottom: 'var(--sp-6)' }}>
        <Card>
          <CardBody>
            <div className="t-valor">{totalUnfiltered || '—'}</div>
            <div className="statLabel">Total de Contas</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor" style={{ color: 'var(--success-text)' }}>
              {readyCount}
            </div>
            <div className="statLabel">Prontas</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor" style={{ color: 'var(--warning-text)' }}>
              {creatingCount}
            </div>
            <div className="statLabel">Criando</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor" style={{ color: 'var(--danger-text)' }}>
              {failedCount}
            </div>
            <div className="statLabel">Falhas</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor">{outlookCount}</div>
            <div className="statLabel">Outlook</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor">{instagramCount}</div>
            <div className="statLabel">Instagram</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor">
              {proxyStats ? proxyStats.active_proxies : <Skeleton width="60px" />}
            </div>
            <div className="statLabel">Proxies Ativos</div>
          </CardBody>
        </Card>
      </div>

      {/* Server Status */}
      <Card style={{ marginBottom: 'var(--sp-6)' }}>
        <CardBody>
          <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-3)' }}>
            Status do Servidor
          </h2>
          {healthLoading ? (
            <Skeleton width="200px" height="24px" />
          ) : serverStatus ? (
            <div style={{ display: 'flex', gap: 'var(--sp-4)', alignItems: 'center', flexWrap: 'wrap' }}>
              <Badge tone={serverStatus.status === 'healthy' ? 'success' : 'danger'}>
                {serverStatus.status === 'healthy' ? <CheckCircle size={12} /> : <XCircle size={12} />}
                {serverStatus.status}
              </Badge>
              <span className="t-legenda">
                Plataformas: {serverStatus.platforms.join(', ')}
              </span>
            </div>
          ) : (
            <Banner tone="danger">Servidor indisponível</Banner>
          )}
        </CardBody>
      </Card>

      {/* Recent Accounts */}
      <Card>
        <CardBody>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-4)' }}>
            <h2 className="t-titulo-secao">Contas Recentes</h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('contas')}>
              Ver todas
            </Button>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center' }}>
                  <Skeleton width="120px" />
                  <Skeleton width="200px" />
                  <Skeleton width="60px" />
                </div>
              ))}
            </div>
          ) : accounts.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--sp-8) 0', color: 'var(--text-3)' }}>
              <Mail size={32} style={{ margin: '0 auto var(--sp-3)', display: 'block', opacity: 0.5 }} />
              <p className="t-rotulo">Nenhuma conta criada ainda</p>
              <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
                Clique em "Nova Conta" para começar
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
              {recentAccounts.map((account) => (
                <div
                  key={account.id}
                  onClick={() => navigate('contas', account.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--sp-3)',
                    padding: 'var(--sp-3) var(--sp-4)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--surface-2)',
                    cursor: 'pointer',
                    transition: 'background var(--dur-fast) var(--ease)',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-3)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--surface-2)'; }}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter') navigate('contas', account.id); }}
                >
                  <Badge
                    tone={account.platform === 'outlook' ? 'info' : 'warning'}
                  >
                    {account.platform === 'outlook' ? <Mail size={12} /> : null}
                    {account.platform}
                  </Badge>
                  <span className="coin truncate" style={{ flex: 1, fontSize: 'var(--fs-sm)' }}>
                    {account.platform === 'instagram'
                      ? (account.handle ? (account.handle.includes('@') ? `@${account.handle.split('@')[0]}` : `@${account.handle}`) : '(sem handle)')
                      : account.handle}
                  </span>
                  <Badge
                    tone={
                      account.status === 'ready' ? 'success' :
                      account.status === 'creating' ? 'warning' :
                      account.status === 'failed' ? 'danger' : 'neutral'
                    }
                  >
                    {account.status === 'creating' && <LoaderCircle size={12} className="spin" />}
                    {account.status}
                  </Badge>
                  <span className="t-legenda" style={{ fontSize: 'var(--fs-2xs)' }}>
                    {formatDateTime(account.created_at)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
