import { useEffect, useState } from 'react';
import { useUIStore } from '../stores/ui';
import { useAccountsStore } from '../stores/accounts';
import { api } from '../services/api';
import { Badge } from '../components/Badge';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { EvidenceViewer } from '../components/EvidenceViewer';
import { Skeleton } from '../components/Skeleton';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ArrowLeft, Mail, Camera, LoaderCircle, Trash2, RefreshCw, Copy, Clock } from 'lucide-react';
import type { Account, CredentialResponse, Evidence } from '../types';

export function ContaDetailPage() {
  const { selectedAccountId, navigate } = useUIStore();
  const { accounts, deleteAccount } = useAccountsStore();
  const [account, setAccount] = useState<Account | null>(null);
  const [credentials, setCredentials] = useState<CredentialResponse | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [automationLog, setAutomationLog] = useState<Array<{timestamp: string; message: string}>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => {
    if (!selectedAccountId) {
      navigate('contas');
      return;
    }

    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const acc = accounts.find((a) => a.id === selectedAccountId);
        if (acc) setAccount(acc);

        const [credData, evData, logData] = await Promise.allSettled([
          api.getCredentials(selectedAccountId),
          api.getEvidence(selectedAccountId),
          api.getAutomationLog(selectedAccountId),
        ]);

        if (credData.status === 'fulfilled') setCredentials(credData.value);
        if (evData.status === 'fulfilled') setEvidence(evData.value);
        if (logData.status === 'fulfilled' && logData.value.log) setAutomationLog(logData.value.log);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load details');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [selectedAccountId]);

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' });
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!selectedAccountId) return null;

  const getStatusTone = (status: string) => {
    switch (status) {
      case 'ready': return 'success';
      case 'creating': return 'warning';
      case 'failed': return 'danger';
      case 'blocked': return 'neutral';
    }
    return 'neutral';
  };

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-5)' }}>
        <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={() => navigate('contas')} aria-label="Voltar para lista de contas">
          Voltar para Contas
        </Button>
      </div>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          {error}
        </Banner>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          <Skeleton width="300px" height="32px" />
          <Skeleton width="100%" height="200px" />
        </div>
      ) : account ? (
        <>
          {/* Account Header */}
          <Card style={{ marginBottom: 'var(--sp-5)' }}>
            <CardBody>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--sp-4)' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-2)' }}>
                    <Badge tone={account.platform === 'outlook' ? 'info' : 'warning'}>
                      {account.platform === 'outlook' ? <Mail size={14} /> : <Camera size={14} />}
                      {account.platform}
                    </Badge>
                    <Badge tone={getStatusTone(account.status)}>
                      {account.status === 'creating' && <LoaderCircle size={12} className="spin" />}
                      {account.status}
                    </Badge>
                  </div>
                  <h1 className="t-titulo-pagina" style={{ fontSize: 'var(--fs-xl)' }}>
                    {account.platform === 'instagram' ? (
                      account.handle ? (account.handle.includes('@') ? (
                        <span>@{account.handle.split('@')[0]} <span style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', fontWeight: 'normal' }}>(handle não capturado)</span></span>
                      ) : (
                        <a
                          href={`https://www.instagram.com/${account.handle}/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'var(--accent-text)', textDecoration: 'none' }}
                          onMouseEnter={(e) => { e.currentTarget.style.textDecoration = 'underline'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.textDecoration = 'none'; }}
                        >
                          @{account.handle}
                        </a>
                      )) : (
                        <span>(handle não capturado)</span>
                      )
                    ) : (
                      account.handle
                    )}
                  </h1>
                  <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
                    Criada em {formatDateTime(account.created_at)}
                  </p>
                  {account.profile_id && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginTop: 'var(--sp-2)' }}>
                      <span className="t-legenda" title={account.profile_id}>
                        Profile ID: {account.profile_id.slice(0, 12)}...
                      </span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(account.profile_id)}
                        aria-label="Copiar Profile ID"
                        style={{ background: 'none', border: 'none', color: 'var(--text-3)', cursor: 'pointer', padding: 4, borderRadius: 'var(--radius-sm)' }}
                      >
                        <Copy size={14} />
                      </button>
                      {copied && <span style={{ fontSize: 'var(--fs-2xs)', color: 'var(--success-text)' }}>Copiado!</span>}
                    </div>
                  )}
                  {account.proxy_used && (
                    <p className="t-legenda">
                      Proxy: {account.proxy_used}
                    </p>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                  <Button variant="outline" size="sm" icon={RefreshCw} onClick={() => window.location.reload()}>
                    Atualizar
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    icon={Trash2}
                    onClick={() => setShowDelete(true)}
                  >
                    Deletar
                  </Button>
                </div>
              </div>

              {account.error_message && (
                <Banner tone="danger" style={{ marginTop: 'var(--sp-4)' }}>
                  Erro: {account.error_message}
                </Banner>
              )}
            </CardBody>
          </Card>

          {/* Credentials */}
          {credentials && (
            <Card style={{ marginBottom: 'var(--sp-5)' }}>
              <CardBody>
                <EvidenceViewer
                  email={credentials.email}
                  password={credentials.password}
                  platform={credentials.platform}
                />
              </CardBody>
            </Card>
          )}

          {/* Evidence Screenshots */}
          <Card>
            <CardBody>
              <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
                Evidências
              </h2>
              {evidence.length === 0 ? (
                <p className="t-legenda">Nenhuma evidência disponível.</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--sp-3)' }}>
                  {evidence.filter(e => e.evidence_type === 'screenshot').map((ev) => (
                    <div key={ev.filename} style={{ position: 'relative' }}>
                      <img
                        src={ev.screenshot_url}
                        alt={ev.description}
                        style={{ width: '100%', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-2)' }}
                      />
                      <p className="t-legenda" style={{ marginTop: 'var(--sp-1)', fontSize: 'var(--fs-2xs)' }}>
                        {ev.description}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          {/* Automation Log */}
          {automationLog.length > 0 && (
            <Card>
              <CardBody>
                <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
                  <Clock size={16} style={{ marginRight: 'var(--sp-2)' }} />
                  Log de Automação
                </h2>
                <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
                  {automationLog.map((entry, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        gap: 'var(--sp-3)',
                        padding: 'var(--sp-2) 0',
                        borderBottom: i < automationLog.length - 1 ? '1px solid var(--border-2)' : 'none',
                        fontSize: 'var(--fs-sm)',
                      }}
                    >
                      <span style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-3)', minWidth: '60px' }}>
                        {new Date(entry.timestamp).toLocaleTimeString('pt-BR')}
                      </span>
                      <span style={{ color: entry.message.includes('Erro') || entry.message.includes('Falha') ? 'var(--danger-text)' : entry.message.includes('warning') || entry.message.includes('Aviso') ? 'var(--warning-text)' : 'var(--text-1)' }}>
                        {entry.message}
                      </span>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}

          {!credentials && account.status === 'ready' && (
            <Banner tone="warning">
              Credenciais não disponíveis. O endpoint de credenciais pode não estar implementado no backend.
            </Banner>
          )}
        </>
      ) : (
        <div style={{ textAlign: 'center', padding: 'var(--sp-10) 0' }}>
          <p className="t-rotulo">Conta não encontrada</p>
          <Button variant="primary" onClick={() => navigate('contas')} style={{ marginTop: 'var(--sp-4)' }}>
            Voltar para Contas
          </Button>
        </div>
      )}

      <ConfirmDialog
        open={showDelete}
        title="Deletar conta"
        description={account ? `Deseja deletar a conta ${account.platform}: ${account.handle}? Esta ação não pode ser desfeita.` : ''}
        confirmLabel="Deletar"
        cancelLabel="Cancelar"
        destructive
        onConfirm={() => { deleteAccount(account!.id); navigate('contas'); }}
        onCancel={() => setShowDelete(false)}
      />
    </div>
  );
}
