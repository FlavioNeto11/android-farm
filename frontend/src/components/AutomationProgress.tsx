import { useState, useEffect, useRef } from 'react';
import { LoaderCircle, CheckCircle, AlertCircle, DollarSign } from 'lucide-react';
import { Banner } from './Banner';
import { api } from '../services/api';

interface Step {
  type: string;
  detail: string;
  timestamp: string;
  status: 'pending' | 'running' | 'done' | 'error';
}

interface Metrics {
  stepsCount: number;
  estimatedCost: number;
  successRate: number;
}

interface LogEntry {
  timestamp: string;
  message: string;
}

export function AutomationProgress({ accountId }: { accountId: string }) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [usePolling, setUsePolling] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/progress`;
    let reconnectAttempts = 0;

    const connectWs = () => {
      if (reconnectAttempts >= 3) {
        setUsePolling(true);
        return;
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttempts = 0;
        ws.send(JSON.stringify({ type: 'subscribe', account_id: accountId }));
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.account_id && data.account_id !== accountId) return;

        if (data.type === 'step_executed' || data.type === 'step_started') {
          setSteps(prev => [...prev, {
            type: data.type,
            detail: data.detail,
            timestamp: data.timestamp,
            status: 'running',
          }]);
          setMetrics(prev => ({
            stepsCount: (prev?.stepsCount || 0) + 1,
            estimatedCost: ((prev?.estimatedCost || 0) + 0.19),
            successRate: prev?.successRate || 100,
          }));
        } else if (data.type === 'step_completed') {
          setSteps(prev => {
            const updated = [...prev];
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].status === 'running') {
                updated[i].status = 'done';
                break;
              }
            }
            return updated;
          });
        } else if (data.type === 'step_failed') {
          setSteps(prev => [...prev, {
            type: data.type,
            detail: data.detail,
            timestamp: data.timestamp,
            status: 'error',
          }]);
        } else if (data.type === 'complete') {
          setIsComplete(true);
          ws.close();
        } else if (data.type === 'error') {
          setError(data.detail);
          setIsComplete(true);
          ws.close();
        }
      };

      ws.onclose = () => {
        if (!isComplete && reconnectAttempts < 3) {
          reconnectAttempts++;
          setTimeout(connectWs, 2000 * reconnectAttempts);
        } else if (!isComplete) {
          setUsePolling(true);
        }
      };

      ws.onerror = () => ws.close();
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
    if (!usePolling || !accountId) return;

    const pollLog = async () => {
      try {
        const data = await api.getAutomationLog(accountId);
        if (data.log && data.log.length > 0) {
          const newSteps: Step[] = data.log.map((entry: LogEntry) => ({
            type: 'log',
            detail: entry.message,
            timestamp: entry.timestamp,
            status: 'done',
          }));
          setSteps(newSteps);
        }
        if (data.status === 'ready') {
          setIsComplete(true);
        } else if (data.status === 'failed') {
          setError(data.error_message || 'Falha desconhecida');
          setIsComplete(true);
        }
      } catch {
        // ignore
      }
    };

    const interval = setInterval(pollLog, 2000);
    pollLog();
    return () => clearInterval(interval);
  }, [accountId, usePolling]);

  return (
    <div style={{ marginTop: 'var(--sp-4)', padding: 'var(--sp-3)', background: 'var(--surface-2)', borderRadius: 'var(--radius-md)' }}>
      <h3 style={{ marginBottom: 'var(--sp-2)' }}>Progresso da Automação IA</h3>

      {metrics && (
        <div style={{ marginBottom: 'var(--sp-3)', padding: 'var(--sp-2)', background: 'var(--surface-3)', borderRadius: 'var(--radius-sm)', display: 'flex', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-1)' }}>
            <DollarSign size={14} />
            <span style={{ fontSize: 'var(--fs-sm)' }}>Custo estimado: ${metrics.estimatedCost.toFixed(4)}</span>
          </div>
          <div style={{ fontSize: 'var(--fs-sm)' }}>
            Passos: {metrics.stepsCount}
          </div>
        </div>
      )}

      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {steps.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--sp-4)', color: 'var(--text-3)' }}>
            <LoaderCircle size={16} className="spin" />
            <p style={{ fontSize: 'var(--fs-xs)', marginTop: 'var(--sp-1)' }}>
              {usePolling ? 'Buscando log via polling...' : 'Conectando...'}
            </p>
          </div>
        ) : (
          steps.map((step, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', padding: 'var(--sp-2)', marginBottom: 'var(--sp-1)', background: 'var(--surface-3)', borderRadius: 'var(--radius-sm)' }}>
              {step.status === 'done' ? <CheckCircle size={14} color="var(--success-text)" /> :
               step.status === 'running' ? <LoaderCircle size={14} className="spin" /> :
               <AlertCircle size={14} color="var(--warning-text)" />}
              <span style={{ fontSize: 'var(--fs-sm)' }}>{step.detail}</span>
            </div>
          ))
        )}
      </div>

      {isComplete && !error && (
        <Banner tone="success">Conta criada com sucesso!</Banner>
      )}

      {error && (
        <Banner tone="danger">Erro: {error}</Banner>
      )}
    </div>
  );
}
