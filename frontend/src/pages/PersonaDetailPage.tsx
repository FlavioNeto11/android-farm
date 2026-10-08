import { useState, useEffect } from 'react';
import { useUIStore } from '../stores/ui';
import { api } from '../services/api';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { Contact, Camera, LoaderCircle, AlertCircle, ArrowLeft, Mail, Calendar, User } from 'lucide-react';

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
  biography?: any;
  traits?: any;
}

const ANDROID_API_URL = import.meta.env.VITE_ANDROID_API_URL || 'http://127.0.0.1:8000';

export function PersonaDetailPage() {
  const { navigate, selectedAccountId } = useUIStore();
  const [persona, setPersona] = useState<Persona | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personaId = selectedAccountId || '';

  const fetchPersona = async () => {
    if (!personaId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${ANDROID_API_URL}/api/personas/${personaId}`);
      if (!response.ok) {
        throw new Error('Persona not found');
      }
      const data = await response.json();
      setPersona(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar persona');
    }
    setLoading(false);
  };

  const createInstagram = async () => {
    if (!personaId) return;
    setCreating(true);
    try {
      const result = await api.createAccountForPersona(personaId);
      if (result.account_id) {
        navigate('progress', result.account_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao criar conta');
    }
    setCreating(false);
  };

  useEffect(() => {
    fetchPersona();
  }, [personaId]);

  if (loading) {
    return (
      <div className="page">
        <p className="t-legenda">Carregando...</p>
      </div>
    );
  }

  if (error || !persona) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate('personas')}>
          <ArrowLeft size={14} />
          Voltar
        </Button>
        <Banner tone="danger" style={{ marginTop: 'var(--sp-4)' }}>
          <AlertCircle size={16} />
          {error || 'Persona não encontrada'}
        </Banner>
      </div>
    );
  }

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-5)' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate('personas')}>
          <ArrowLeft size={14} />
          Voltar para Personas
        </Button>
      </div>

      <h1 className="t-titulo-pagina" style={{ marginBottom: 'var(--sp-1)' }}>
        {persona.display_name || `${persona.first_name} ${persona.last_name}`}
      </h1>
      <p className="t-legenda" style={{ marginBottom: 'var(--sp-6)' }}>
        Detalhes da persona
      </p>

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          <AlertCircle size={16} />
          {error}
        </Banner>
      )}

      <div style={{ display: 'grid', gap: 'var(--sp-4)' }}>
        <Card>
          <CardBody>
            <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
              Informações Básicas
            </h2>
            <div style={{ display: 'grid', gap: 'var(--sp-3)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                <User size={16} style={{ color: 'var(--text-3)' }} />
                <span>
                  <strong>Nome:</strong> {persona.first_name} {persona.last_name}
                </span>
              </div>
              {persona.email && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                  <Mail size={16} style={{ color: 'var(--text-3)' }} />
                  <span>
                    <strong>Email:</strong> {persona.email}
                  </span>
                </div>
              )}
              {persona.birth_date && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                  <Calendar size={16} style={{ color: 'var(--text-3)' }} />
                  <span>
                    <strong>Nascimento:</strong> {persona.birth_date}
                  </span>
                </div>
              )}
              {persona.gender && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                  <Contact size={16} style={{ color: 'var(--text-3)' }} />
                  <span>
                    <strong>Gênero:</strong> {persona.gender}
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
                <span>
                  <strong>Status:</strong>{' '}
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
                </span>
              </div>
            </div>
          </CardBody>
        </Card>

        {persona.summary && (
          <Card>
            <CardBody>
              <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-3)' }}>
                Resumo
              </h2>
              <p className="t-legenda">{persona.summary}</p>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardBody>
            <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-3)' }}>
              Criar Conta Instagram
            </h2>
            <p className="t-legenda" style={{ marginBottom: 'var(--sp-4)' }}>
              Iniciar criação automática de conta Instagram para esta persona
            </p>
            <Button
              variant="primary"
              onClick={createInstagram}
              disabled={creating}
            >
              {creating ? (
                <>
                  <LoaderCircle size={15} className="spin" />
                  Criando conta...
                </>
              ) : (
                <>
                  <Camera size={15} />
                  Criar Instagram
                </>
              )}
            </Button>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
