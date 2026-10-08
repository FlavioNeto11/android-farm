import { useEffect, useState, useRef } from 'react';
import { useUIStore } from '../stores/ui';
import { api } from '../services/api';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { Badge } from '../components/Badge';
import { ArrowLeft, LoaderCircle, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  message: string;
}

interface AutomationLogResponse {
  account_id: string;
  status: string;
  handle: string | null;
  error_message: string | null;
  log: LogEntry[];
  created_at: string;
  updated_at: string;
}

export function AccountProgressPage() {
  const { navigate, selectedAccountId } = useUIStore();
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [accountStatus, setAccountStatus] = useState<string>('creating');
  const [error, setError] = useState<string | null>(null);
  const [handle, setHandle] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [usePolling, setUsePolling] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollCountRef = useRef(0);

  const accountId = selectedAccountId;

  useEffect(() => {
    if (!accountId) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/progress`;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 3;

    const connectWs = () => {
      if (reconnectAttempts >= maxReconnectAttempts) {
        setUsePolling(true);
        return;
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setWsConnected(true);
        reconnectAttempts = 0;
        ws.send(JSON.stringify({ type: 'subscribe', account_id: accountId }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.account_id && data.account_id !== accountId) return;

        const entry: LogEntry = {
          timestamp: data.timestamp || new Date().toISOString(),
          message: data.detail || data.message || '',
        };
        setLogEntries(prev => [...prev, entry]);

        if (data.type === 'complete') {
          setAccountStatus('completed');
          setWsConnected(false);
          ws.close();
        } else if (data.type === 'error') {
          setError(data.detail);
          setAccountStatus('failed');
          setWsConnected(false);
          ws.close();
        } else if (data.type === 'success' && data.detail?.includes('Handle:')) {
          const match = data.detail.match(/@(\w+)/);
          if (match) setHandle(match[1]);
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        if (accountStatus === 'creating' && reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          setTimeout(connectWs, Math.min(1000 * Math.pow(2, reconnectAttempts), 5000));
        }
        if (reconnectAttempts >= maxReconnectAttempts) {
          setUsePolling(true);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [accountId]);

  useEffect(() => {
    if (!accountId) return;

    const pollLog = async () => {
      try {
        const data: AutomationLogResponse = await api.getAutomationLog(accountId);
        if (data.log && data.log.length > 0) {
          setLogEntries(data.log);
        }
        if (data.status === 'ready') {
          setAccountStatus('completed');
          if (data.handle) setHandle(data.handle);
        } else if (data.status === 'failed') {
          setAccountStatus('failed');
          setError(data.error_message || 'Falha desconhecida');
        }
        pollCountRef.current = 0;
      } catch {
        pollCountRef.current++;
        if (pollCountRef.current > 10) {
          setUsePolling(false);
        }
      }
    };

    if (usePolling) {
      const interval = setInterval(pollLog, 2000);
      pollLog();
      return () => clearInterval(interval);
    }

    const interval = setInterval(pollLog, 3000);
    return () => clearInterval(interval);
  }, [accountId, usePolling]);

  const formatTime = (ts: string) => {
    try {
      return new Date(ts).toLocaleTimeString('pt-BR');
    } catch {
      return '';
    }
  };

  const getEntryTone = (msg: string) => {
    if (msg.includes('sucesso') || msg.includes('completado com sucesso') || msg.startsWith('Sucesso')) return 'success';
    if (msg.includes('Falha') || msg.includes('error') || msg.includes('Erro') || msg.includes('not found')) return 'error';
    if (msg.includes('warning') || msg.includes('Aviso') || msg.includes('Fallback') || msg.includes('Checkpoint') || msg.includes('Blocking')) return 'warning';
    if (msg.includes('AI decision') || msg.startsWith('IA')) return 'ai';
    return 'info';
  };

  const getEntryIcon = (tone: string) => {
    switch (tone) {
      case 'success': return <CheckCircle size={14} color="var(--success-text)" />;
      case 'error': return <AlertCircle size={14} color="var(--danger-text)" />;
      case 'warning': return <LoaderCircle size={14} className="spin" color="var(--warning-text)" />;
      default: return <LoaderCircle size={12} style={{ color: 'var(--text-3)' }} />;
    }
  };

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-5)' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate('contas')}>
          <ArrowLeft size={14} />
          Voltar para Contas
        </Button>
      </div>

      <h1 className="t-titulo-pagina" style={{ marginBottom: 'var(--sp-1)' }}>
        Criando Conta
      </h1>
      <p className="t-legenda" style={{ marginBottom: 'var(--sp-6)' }}>
        Acompanhe o progresso da automação em tempo real
      </p>

      <div style={{ marginBottom: 'var(--sp-4)', display: 'flex', gap: 'var(--sp-3)', alignItems: 'center' }}>
        <Badge tone={accountStatus === 'completed' ? 'success' : accountStatus === 'failed' ? 'danger' : 'warning'}>
          {accountStatus === 'creating' && <LoaderCircle size={14} className="spin" />}
          {accountStatus === 'completed' && <CheckCircle size={14} />}
          {accountStatus === 'failed' && <AlertCircle size={14} />}
          {accountStatus === 'creating' ? 'Em progresso...' : accountStatus === 'completed' ? 'Concluído' : 'Falhou'}
        </Badge>
        {handle && (
          <Badge tone="success">@{handle}</Badge>
        )}
        {!wsConnected && accountStatus === 'creating' && (
          <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>
            {usePolling ? 'Polling...' : 'Conectando WS...'}
          </span>
        )}
      </div>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          <AlertCircle size={16} />
          {error}
        </Banner>
      )}

      <Card>
        <CardBody>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-3)' }}>
            <h2 className="t-titulo-secao" style={{ marginBottom: 0 }}>Log de Automação</h2>
            <Button variant="ghost" size="sm" onClick={() => { if (accountId) api.getAutomationLog(accountId).then(d => setLogEntries(d.log || [])); }}>
              <RefreshCw size={14} />
            </Button>
          </div>
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {logEntries.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 'var(--sp-8)', color: 'var(--text-3)' }}>
                <LoaderCircle size={24} className="spin" style={{ margin: '0 auto var(--sp-2)', display: 'block', color: 'var(--accent)' }} />
                <p className="t-legenda">Aguardando início da automação...</p>
              </div>
            ) : (
              logEntries.map((entry, index) => {
                const tone = getEntryTone(entry.message);
                return (
                  <div
                    key={index}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 'var(--sp-3)',
                      padding: 'var(--sp-2) 0',
                      borderBottom: index < logEntries.length - 1 ? '1px solid var(--border-2)' : 'none',
                    }}
                  >
                    <span style={{ fontSize: 'var(--fs-2xs)', color: 'var(--text-3)', minWidth: '60px', paddingTop: '2px' }}>
                      {formatTime(entry.timestamp)}
                    </span>
                    <span style={{ paddingTop: '2px', flexShrink: 0 }}>
                      {getEntryIcon(tone)}
                    </span>
                    <span style={{ fontSize: 'var(--fs-sm)', flex: 1, color: tone === 'error' ? 'var(--danger-text)' : tone === 'warning' ? 'var(--warning-text)' : 'var(--text-1)' }}>
                      {entry.message}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </CardBody>
      </Card>

      {accountStatus === 'completed' && (
        <div style={{ marginTop: 'var(--sp-4)', textAlign: 'center' }}>
          <Banner tone="success">
            <CheckCircle size={16} />
            Conta criada com sucesso! {handle ? `Handle: @${handle}` : ''}
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
            Falha na criação da conta. Verifique os logs acima.
          </Banner>
          <Button variant="outline" style={{ marginTop: 'var(--sp-3)' }} onClick={() => navigate('contas')}>
            Voltar para Contas
          </Button>
        </div>
      )}
    </div>
  );
}
