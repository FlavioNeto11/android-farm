import { useState, useEffect } from 'react';
import { useUIStore } from '../stores/ui';
import { api } from '../services/api';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { Contact, RefreshCw, Camera, LoaderCircle, AlertCircle, Eye } from 'lucide-react';

interface Persona {
  id: string;
  first_name: string;
  last_name: string;
  display_name: string;
  status: string;
  email?: string;
  birth_date?: string;
  gender?: string;
  summary?: string;
}

const ANDROID_API_URL = import.meta.env.VITE_ANDROID_API_URL || 'http://127.0.0.1:8000';

export function PersonasPage() {
  const { navigate } = useUIStore();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchPersonas = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${ANDROID_API_URL}/api/personas`);
      if (!response.ok) {
        throw new Error('Failed to fetch personas from android API');
      }
      const data = await response.json();
      setPersonas(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar personas');
      setPersonas([]);
    }
    setLoading(false);
  };

  const createInstagram = async (personaId: string) => {
    setCreating(personaId);
    try {
      const result = await api.createAccountForPersona(personaId);
      if (result.account_id) {
        navigate('progress', result.account_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao criar conta');
    }
    setCreating(null);
  };

  useEffect(() => {
    fetchPersonas();
  }, []);

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-5)' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate('painel')}>
          Voltar ao Painel
        </Button>
      </div>

      <h1 className="t-titulo-pagina" style={{ marginBottom: 'var(--sp-1)' }}>
        Personas do Android
      </h1>
      <p className="t-legenda" style={{ marginBottom: 'var(--sp-6)' }}>
        Personas importadas do repositório android
      </p>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          <AlertCircle size={16} />
          {error}
        </Banner>
      )}

      <div style={{ marginBottom: 'var(--sp-4)', display: 'flex', gap: 'var(--sp-3)' }}>
        <Button variant="primary" onClick={fetchPersonas} disabled={loading}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          {loading ? 'Carregando...' : 'Atualizar'}
        </Button>
      </div>

      {personas.length === 0 ? (
        <Card>
          <CardBody>
            <p className="t-legenda" style={{ textAlign: 'center', padding: 'var(--sp-6) 0' }}>
              {loading ? 'Carregando personas...' : 'Nenhuma persona encontrada. Verifique se o android está rodando em localhost:8000'}
            </p>
          </CardBody>
        </Card>
      ) : (
        <div style={{ display: 'grid', gap: 'var(--sp-3)' }}>
          {personas.map((persona) => (
            <Card key={persona.id}>
              <CardBody>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--sp-4)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
                    <div
                      style={{
                        width: '48px',
                        height: '48px',
                        borderRadius: '50%',
                        background: 'var(--surface-3)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Contact size={24} style={{ color: 'var(--text-3)' }} />
                    </div>
                    <div>
                      <h3 style={{ fontWeight: 'var(--fw-semibold)', color: 'var(--text-1)' }}>
                        {persona.display_name || `${persona.first_name} ${persona.last_name}`}
                      </h3>
                      <p className="t-legenda">
                        {persona.first_name} {persona.last_name}
                        {persona.birth_date && ` · ${persona.birth_date}`}
                      </p>
                      <span
                        style={{
                          fontSize: 'var(--fs-xs)',
                          padding: '2px var(--sp-2)',
                          borderRadius: 'var(--radius-sm)',
                          background: persona.status === 'active' ? 'var(--success-soft)' : 'var(--surface-3)',
                          color: persona.status === 'active' ? 'var(--success-text)' : 'var(--text-2)',
                        }}
                      >
                        {persona.status}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('persona-detail', persona.id)}
                    >
                      <Eye size={14} />
                      Detalhes
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => createInstagram(persona.id)}
                      disabled={creating === persona.id}
                    >
                      {creating === persona.id ? (
                        <>
                          <LoaderCircle size={14} className="spin" />
                          Criando...
                        </>
                      ) : (
                        <>
                          <Camera size={14} />
                          Criar Instagram
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
