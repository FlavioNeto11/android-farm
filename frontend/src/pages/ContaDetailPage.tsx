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
import { ArrowLeft, Mail, Camera, LoaderCircle, Trash2, RefreshCw, Copy } from 'lucide-react';
import type { Account, CredentialResponse, Evidence } from '../types';

export function ContaDetailPage() {
  const { selectedAccountId, navigate } = useUIStore();
  const { accounts, deleteAccount } = useAccountsStore();
  const [account, setAccount] = useState<Account | null>(null);
  const [credentials, setCredentials] = useState<CredentialResponse | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
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

        const [credData, evData] = await Promise.allSettled([
          api.getCredentials(selectedAccountId),
          api.getEvidence(selectedAccountId),
        ]);

        if (credData.status === 'fulfilled') setCredentials(credData.value);
        if (evData.status === 'fulfilled') setEvidence(evData.value);
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
                      account.handle.includes('@') ? (
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
          {evidence.length > 0 && (
            <Card>
              <CardBody>
                <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
                  Evidências
                </h2>
                {evidence.map((ev) => (
                  <div key={ev.evidence_type} style={{ marginBottom: 'var(--sp-4)' }}>
                    {ev.screenshot_url ? (
                      <EvidenceViewer
                        email={credentials?.email ?? ''}
                        password={credentials?.password ?? ''}
                        platform={ev.platform}
                        screenshotUrl={ev.screenshot_url}
                        description={ev.description}
                      />
                    ) : (
                      <Banner tone="info">{ev.description}</Banner>
                    )}
                  </div>
                ))}
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
