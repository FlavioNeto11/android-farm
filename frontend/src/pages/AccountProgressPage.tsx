import { useEffect, useState } from 'react';
import { useUIStore } from '../stores/ui';
import { api } from '../services/api';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { Badge } from '../components/Badge';
import { ArrowLeft, LoaderCircle, CheckCircle, AlertCircle } from 'lucide-react';

interface ProgressEvent {
  type: string;
  detail: string;
  timestamp: string;
  status: 'pending' | 'running' | 'done' | 'error';
  screenshot?: string;
}

export function AccountProgressPage() {
  const { navigate, selectedAccountId } = useUIStore();
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [accountStatus, setAccountStatus] = useState<string>('creating');
  const [error, setError] = useState<string | null>(null);

  const accountId = selectedAccountId;

  useEffect(() => {
    if (!accountId) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/progress`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'subscribe', account_id: accountId }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.account_id && data.account_id !== accountId) return;

      if (data.type === 'step_executed' || data.type === 'step_completed') {
        setEvents(prev => [...prev, {
          type: data.type,
          detail: data.detail,
          timestamp: data.timestamp || new Date().toISOString(),
          status: 'done',
          screenshot: data.screenshot,
        }]);
      } else if (data.type === 'captcha_detected') {
        setEvents(prev => [...prev, {
          type: 'captcha',
          detail: data.detail,
          timestamp: data.timestamp || new Date().toISOString(),
          status: 'running',
        }]);
      } else if (data.type === 'step_failed') {
        setEvents(prev => [...prev, {
          type: data.type,
          detail: data.detail,
          timestamp: data.timestamp || new Date().toISOString(),
          status: 'error',
        }]);
      } else if (data.type === 'complete') {
        setAccountStatus('completed');
        ws.close();
      } else if (data.type === 'error') {
        setError(data.detail);
        setAccountStatus('failed');
        ws.close();
      }
    };

    ws.onclose = () => {
      if (accountStatus === 'creating') {
        setAccountStatus('completed');
      }
    };

    return () => ws.close();
  }, [accountId]);

  useEffect(() => {
    if (!accountId) return;

    const pollStatus = async () => {
      try {
        const account = await api.getAccount(accountId);
        if (account.status === 'ready') {
          setAccountStatus('completed');
        } else if (account.status === 'failed') {
          setAccountStatus('failed');
          setError(account.error_message || 'Falha desconhecida');
        }
      } catch {
        // ignore
      }
    };

    const interval = setInterval(pollStatus, 3000);
    return () => clearInterval(interval);
  }, [accountId]);

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString('pt-BR');
    } catch {
      return '';
    }
  };

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-5)' }}>
        <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={() => navigate('contas')}>
          Voltar para Contas
        </Button>
      </div>

      <h1 className="t-titulo-pagina" style={{ marginBottom: 'var(--sp-1)' }}>
        Criando Conta
      </h1>
      <p className="t-legenda" style={{ marginBottom: 'var(--sp-6)' }}>
        Acompanhe o progresso da automa&ccedil;&atilde;o IA em tempo real
      </p>

      <div style={{ marginBottom: 'var(--sp-4)' }}>
        <Badge tone={accountStatus === 'completed' ? 'success' : accountStatus === 'failed' ? 'danger' : 'warning'}>
          {accountStatus === 'creating' && <LoaderCircle size={14} className="spin" />}
          {accountStatus === 'completed' && <CheckCircle size={14} />}
          {accountStatus === 'failed' && <AlertCircle size={14} />}
          {accountStatus === 'creating' ? 'Em progresso...' : accountStatus === 'completed' ? 'Conclu&iacute;do' : 'Falhou'}
        </Badge>
      </div>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          <AlertCircle size={16} />
          {error}
        </Banner>
      )}

      <Card>
        <CardBody>
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {events.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 'var(--sp-8)', color: 'var(--text-3)' }}>
                <LoaderCircle size={24} className="spin" style={{ margin: '0 auto var(--sp-2)', display: 'block', color: 'var(--accent)' }} />
                <p className="t-legenda">Aguardando in&iacute;cio da automa&ccedil;&atilde;o...</p>
              </div>
            ) : (
              events.map((event, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 'var(--sp-3)',
                    padding: 'var(--sp-2) 0',
                    borderBottom: index < events.length - 1 ? '1px solid var(--border-2)' : 'none',
                  }}
                >
                  <span style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-3)', minWidth: '60px', paddingTop: '2px' }}>
                    {formatTime(event.timestamp)}
                  </span>
                  <span style={{ paddingTop: '2px' }}>
                    {event.status === 'done' ? (
                      <CheckCircle size={14} color="var(--success-text)" />
                    ) : event.status === 'running' ? (
                      <LoaderCircle size={14} className="spin" color="var(--accent)" />
                    ) : event.status === 'error' ? (
                      <AlertCircle size={14} color="var(--danger-text)" />
                    ) : null}
                  </span>
                  <span style={{ fontSize: 'var(--fs-sm)', flex: 1 }}>{event.detail}</span>
                  {event.screenshot && (
                    <img
                      src={event.screenshot}
                      alt="Screenshot"
                      style={{ maxWidth: '120px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-2)' }}
                    />
                  )}
                </div>
              ))
            )}
          </div>
        </CardBody>
      </Card>

      {accountStatus === 'completed' && (
        <div style={{ marginTop: 'var(--sp-4)', textAlign: 'center' }}>
          <Banner tone="success">
            <CheckCircle size={16} />
            Conta criada com sucesso!
          </Banner>
          <Button variant="primary" style={{ marginTop: 'var(--sp-3)' }} onClick={() => navigate('contas')}>
            Ver Contas
          </Button>
        </div>
      )}

      {accountStatus === 'failed' && (
        <div style={{ marginTop: 'var(--sp-4)', textAlign: 'center' }}>
          <Banner tone="danger">
            <AlertCircle size={16} />
            Falha na cria&ccedil;&atilde;o da conta. Verifique os logs acima.
          </Banner>
          <Button variant="outline" style={{ marginTop: 'var(--sp-3)' }} onClick={() => navigate('contas')}>
            Voltar para Contas
          </Button>
        </div>
      )}
    </div>
  );
}
