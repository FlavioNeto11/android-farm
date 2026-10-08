import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { TextInput } from '../components/Field';
import { Badge } from '../components/Badge';
import { Skeleton } from '../components/Skeleton';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { Trash2, Plus, Network, LoaderCircle } from 'lucide-react';
import type { Proxy, ProxyStats } from '../types';

interface ProxyFormErrors {
  host?: string;
  port?: string;
  country?: string;
}

export function ProxiesPage() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [stats, setStats] = useState<ProxyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form
  const [host, setHost] = useState('');
  const [port, setPort] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [country, setCountry] = useState('');
  const [adding, setAdding] = useState(false);
  const [formErrors, setFormErrors] = useState<ProxyFormErrors>({});

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [proxyList, proxyStats] = await Promise.all([
        api.listProxies(),
        api.getProxyStats(),
      ]);
      setProxies(proxyList);
      setStats(proxyStats);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load proxies');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const validateProxy = (): boolean => {
    const errors: ProxyFormErrors = {};

    if (!host.trim()) {
      errors.host = 'Host é obrigatório';
    } else if (/\s/.test(host)) {
      errors.host = 'Host não pode conter espaços';
    }

    if (!port) {
      errors.port = 'Porta é obrigatória';
    } else {
      const portNum = parseInt(port, 10);
      if (isNaN(portNum) || portNum < 1 || portNum > 65535) {
        errors.port = 'Porta deve ser entre 1 e 65535';
      }
    }

    if (country.trim() && !/^[A-Z]{2}$/i.test(country)) {
      errors.country = 'País deve ter 2 letras (ISO)';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateProxy()) return;

    setAdding(true);
    try {
      await api.addProxy({
        host: host.trim(),
        port: parseInt(port, 10),
        username: username.trim() || undefined,
        password: password || undefined,
        country: country.trim().toUpperCase() || undefined,
      });
      setShowForm(false);
      setHost('');
      setPort('');
      setUsername('');
      setPassword('');
      setCountry('');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add proxy');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await api.deleteProxy(deleteId);
      setDeleteId(null);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete proxy');
    }
  };

  const getStatusTone = (status: string) => {
    switch (status) {
      case 'active': return 'success';
      case 'exhausted': return 'warning';
      case 'blocked': return 'danger';
      default: return 'neutral';
    }
  };

  const deleteProxyData = proxies.find((p) => p.id === deleteId);

  return (
    <div className="page">
      <div className="pageHeader">
        <div>
          <h1 className="t-titulo-pagina">Proxies</h1>
          <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
            {stats ? `${stats.active_proxies} ativos de ${stats.total_proxies}` : 'Carregando...'}
          </p>
        </div>
        <Button variant="primary" icon={Plus} onClick={() => setShowForm(!showForm)}>
          Adicionar Proxy
        </Button>
      </div>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          {error}
          <Button variant="dangerGhost" size="sm" onClick={() => setError(null)} style={{ marginLeft: 'auto' }}>
            Fechar
          </Button>
        </Banner>
      )}

      {success && (
        <Banner tone="success" style={{ marginBottom: 'var(--sp-4)' }}>
          Proxy adicionado com sucesso!
        </Banner>
      )}

      {/* Stats */}
      <div className="statsGrid" style={{ marginBottom: 'var(--sp-6)' }}>
        <Card>
          <CardBody>
            <div className="t-valor" style={{ color: 'var(--success-text)' }}>
              {loading ? <Skeleton width="40px" /> : stats?.active_proxies ?? 0}
            </div>
            <div className="statLabel">Ativos</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="t-valor">
              {loading ? <Skeleton width="40px" /> : stats?.total_proxies ?? 0}
            </div>
            <div className="statLabel">Total</div>
          </CardBody>
        </Card>
      </div>

      {/* Add Form */}
      {showForm && (
        <Card style={{ marginBottom: 'var(--sp-5)' }}>
          <CardBody>
            <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
              Novo Proxy
            </h2>
            <form onSubmit={handleAdd}>
              <div style={{ display: 'grid', gap: 'var(--sp-4)', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
                <div>
                  <TextInput
                    label="Host *"
                    placeholder="proxy.example.com"
                    value={host}
                    onChange={(e) => setHost(e.target.value)}
                    required
                  />
                  {formErrors.host && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 4 }}>{formErrors.host}</p>}
                </div>
                <div>
                  <TextInput
                    label="Port *"
                    type="number"
                    placeholder="8080"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    required
                    min="1"
                    max="65535"
                  />
                  {formErrors.port && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 4 }}>{formErrors.port}</p>}
                </div>
                <TextInput
                  label="Username"
                  placeholder="Opcional"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
                <TextInput
                  label="Password"
                  type="password"
                  placeholder="Opcional"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                />
                <div>
                  <TextInput
                    label="Country"
                    placeholder="BR, US, etc."
                    value={country}
                    onChange={(e) => setCountry(e.target.value.toUpperCase())}
                    maxLength={2}
                  />
                  {formErrors.country && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 4 }}>{formErrors.country}</p>}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 'var(--sp-3)', marginTop: 'var(--sp-4)', justifyContent: 'flex-end' }}>
                <Button variant="outline" onClick={() => setShowForm(false)}>
                  Cancelar
                </Button>
                <Button variant="primary" type="submit" loading={adding}>
                  Adicionar
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      {/* Proxy List */}
      {loading && proxies.length === 0 ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--sp-10)' }}>
          <LoaderCircle size={24} className="spin" style={{ color: 'var(--accent)' }} />
        </div>
      ) : proxies.length === 0 ? (
        <Card>
          <CardBody style={{ textAlign: 'center', padding: 'var(--sp-10) 0', color: 'var(--text-3)' }}>
            <Network size={32} style={{ margin: '0 auto var(--sp-3)', display: 'block', opacity: 0.5 }} />
            <p className="t-rotulo">Nenhum proxy configurado</p>
            <p className="t-legenda" style={{ marginTop: 'var(--sp-1)' }}>
              Proxies são necessários para a criação de contas. Adicione um proxy para começar.
            </p>
          </CardBody>
        </Card>
      ) : (
        <Card>
          <CardBody>
            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <caption className="sr-only">Lista de proxies</caption>
                <thead>
                  <tr>
                    <th>Host</th>
                    <th>Port</th>
                    <th>Status</th>
                    <th>Country</th>
                    <th>Usos</th>
                    <th>Falhas</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {proxies.map((proxy) => (
                    <tr key={proxy.id}>
                      <td className="coin">{proxy.host}</td>
                      <td className="coin">{proxy.port}</td>
                      <td>
                        <Badge tone={getStatusTone(proxy.status)}>
                          {proxy.status}
                        </Badge>
                      </td>
                      <td>{proxy.country || '-'}</td>
                      <td className="coin">{proxy.used_count}</td>
                      <td className="coin" style={{ color: proxy.failed_count > 0 ? 'var(--danger-text)' : undefined }}>
                        {proxy.failed_count}
                      </td>
                      <td>
                        <Button
                          variant="dangerGhost"
                          size="sm"
                          icon={Trash2}
                          onClick={() => setDeleteId(proxy.id)}
                          label="Remover"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}

      <ConfirmDialog
        open={deleteId !== null}
        title="Remover proxy"
        description={deleteProxyData ? `Deseja remover o proxy ${deleteProxyData.host}:${deleteProxyData.port}? Esta ação não pode ser desfeita.` : ''}
        confirmLabel="Remover"
        cancelLabel="Cancelar"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
