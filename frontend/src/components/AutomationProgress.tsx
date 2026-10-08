import { useState, useEffect } from 'react';
import { LoaderCircle, CheckCircle, AlertCircle, DollarSign } from 'lucide-react';
import { Banner } from './Banner';

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

export function AutomationProgress({ accountId }: { accountId: string }) {
  const [steps, setSteps] = useState<Step[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/progress`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'step_executed') {
        setSteps(prev => [...prev, {
          type: data.type,
          detail: data.detail,
          timestamp: data.timestamp,
          status: 'done'
        }]);
        
        setMetrics(prev => ({
          stepsCount: (prev?.stepsCount || 0) + 1,
          estimatedCost: ((prev?.estimatedCost || 0) + 0.19),
          successRate: prev?.successRate || 100
        }));
      } else if (data.type === 'captcha_detected') {
        setSteps(prev => [...prev, {
          type: 'captcha',
          detail: data.detail,
          timestamp: data.timestamp,
          status: 'running'
        }]);
      } else if (data.type === 'step_completed') {
        setSteps(prev => [...prev, {
          type: data.type,
          detail: data.detail,
          timestamp: data.timestamp,
          status: 'done'
        }]);
      } else if (data.type === 'step_failed') {
        setSteps(prev => [...prev, {
          type: data.type,
          detail: data.detail,
          timestamp: data.timestamp,
          status: 'error'
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
    
    return () => ws.close();
  }, [accountId]);

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
        {steps.map((step, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', padding: 'var(--sp-2)', marginBottom: 'var(--sp-1)', background: 'var(--surface-3)', borderRadius: 'var(--radius-sm)' }}>
            {step.status === 'done' ? <CheckCircle size={14} color="var(--success-text)" /> : 
             step.status === 'running' ? <LoaderCircle size={14} className="spin" /> : 
             <AlertCircle size={14} color="var(--warning-text)" />}
            <span style={{ fontSize: 'var(--fs-sm)' }}>{step.detail}</span>
          </div>
        ))}
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
