import { useState } from 'react';
import { useUIStore } from '../stores/ui';
import { useAccountsStore } from '../stores/accounts';
import { api } from '../services/api';
import { Button } from '../components/Button';
import { Card, CardBody } from '../components/Card';
import { Banner } from '../components/Banner';
import { TextInput, Select } from '../components/Field';
import { AutomationProgress } from '../components/AutomationProgress';
import { ArrowLeft, CheckCircle, LoaderCircle, AlertCircle } from 'lucide-react';

interface FormErrors {
  firstName?: string;
  profileId?: string;
  birthDate?: string;
  platforms?: string;
}

export function CriarContaPage() {
  const { navigate } = useUIStore();
  const { getProxyStats } = useAccountsStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ account_id: string; platform: string } | null>(null);
  const [errors, setErrors] = useState<FormErrors>({});

  // Form state
  const [profileId, setProfileId] = useState('');
  const [platforms, setPlatforms] = useState<string[]>(['outlook', 'instagram']);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [birthDate, setBirthDate] = useState('');
  const [gender, setGender] = useState('other');

  const proxyStats = getProxyStats();

  const validate = (): boolean => {
    const newErrors: FormErrors = {};

    if (!firstName.trim()) {
      newErrors.firstName = 'Nome é obrigatório';
    } else if (firstName.trim().length < 2) {
      newErrors.firstName = 'Nome deve ter pelo menos 2 caracteres';
    } else if (/\d/.test(firstName)) {
      newErrors.firstName = 'Nome não pode conter números';
    }

    if (profileId.trim()) {
      if (/\s/.test(profileId)) {
        newErrors.profileId = 'Profile ID não pode conter espaços';
      } else if (!/^[a-zA-Z0-9-]+$/.test(profileId)) {
        newErrors.profileId = 'Profile ID deve conter apenas letras, números e hífen';
      }
    }

    if (!birthDate) {
      newErrors.birthDate = 'Data de nascimento é obrigatória';
    } else {
      const date = new Date(birthDate);
      const today = new Date();
      if (date > today) {
        newErrors.birthDate = 'Data de nascimento não pode ser no futuro';
      }
    }

    if (platforms.length === 0) {
      newErrors.platforms = 'Selecione pelo menos uma plataforma';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const togglePlatform = (platform: string) => {
    setPlatforms((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (platforms.includes('instagram')) {
        const result = await api.createAccountAI({
          platform: 'instagram',
          use_proxy: proxyStats.active > 0,
          proxy_session_id: `session_${Date.now()}`,
          first_name: firstName,
          last_name: lastName,
          birth_date: birthDate,
          gender,
        });
        setSuccess({ account_id: result.account_id, platform: result.platform });
        setTimeout(() => navigate('progress', result.account_id), 1500);
      } else {
        const result = await api.createAccount(
          profileId || `persona-${Date.now()}`,
          platforms,
          {
            display_name: `${firstName} ${lastName}`.trim(),
            first_name: firstName,
            last_name: lastName,
            birth_date: birthDate,
            gender,
            locale: 'pt_BR',
          }
        );
        setSuccess({ account_id: result.id, platform: result.platform });
        setTimeout(() => navigate('contas'), 2000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha ao criar conta');
    } finally {
      setLoading(false);
    }
  };

  const platformWarning = platforms.length === 0
    ? 'Selecione as plataformas para criar a conta.'
    : platforms.includes('outlook') && platforms.includes('instagram')
    ? 'Serão criadas contas no Outlook e Instagram vinculadas.'
    : platforms.includes('outlook')
    ? 'Será criada uma conta no Outlook.'
    : 'Será criada uma conta no Instagram.';

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--sp-5)' }}>
        <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={() => navigate('painel')}>
          Voltar ao Painel
        </Button>
      </div>

      <h1 className="t-titulo-pagina" style={{ marginBottom: 'var(--sp-1)' }}>
        Criar Nova Conta
      </h1>
      <p className="t-legenda" style={{ marginBottom: 'var(--sp-6)' }}>
        Preencha os dados para criar contas Outlook e/ou Instagram
      </p>

      {proxyStats.active === 0 && (
        <Banner tone="warning" style={{ marginBottom: 'var(--sp-4)' }}>
          Nenhum proxy ativo. A criação de contas pode falhar.
          <Button variant="ghost" size="sm" onClick={() => navigate('proxies')} style={{ marginLeft: 'auto' }}>
            Configurar proxies
          </Button>
        </Banner>
      )}

      {error && (
        <Banner tone="danger" style={{ marginBottom: 'var(--sp-4)' }}>
          <AlertCircle size={16} />
          {error}
        </Banner>
      )}

      {success && (
        <Banner tone="success" style={{ marginBottom: 'var(--sp-4)' }}>
          <CheckCircle size={16} />
          Conta criada com sucesso! Redirecionando...
        </Banner>
      )}

      {loading && success && platforms.includes('instagram') && (
        <AutomationProgress accountId={success.account_id} />
      )}

      <form onSubmit={handleSubmit}>
        <Card style={{ marginBottom: 'var(--sp-5)' }}>
          <CardBody>
            <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
              Dados da Persona
            </h2>

            <div style={{ display: 'grid', gap: 'var(--sp-4)', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
              <div>
                <TextInput
                  label="Profile ID (opcional)"
                  placeholder="Gerado automaticamente"
                  value={profileId}
                  onChange={(e) => setProfileId(e.target.value)}
                />
                {errors.profileId && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 4 }}>{errors.profileId}</p>}
              </div>
              <div>
                <TextInput
                  label="Primeiro Nome *"
                  placeholder="Ex: João"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                />
                {errors.firstName && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 4 }}>{errors.firstName}</p>}
              </div>
              <TextInput
                label="Sobrenome"
                placeholder="Ex: Silva"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
              <div>
                <TextInput
                  label="Data de Nascimento *"
                  type="date"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                />
                {errors.birthDate && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 4 }}>{errors.birthDate}</p>}
              </div>
              <Select
                label="Gênero"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
              >
                <option value="male">Masculino</option>
                <option value="female">Feminino</option>
                <option value="other">Outro</option>
              </Select>
            </div>
          </CardBody>
        </Card>

        <Card style={{ marginBottom: 'var(--sp-5)' }}>
          <CardBody>
            <h2 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-4)' }}>
              Plataformas
            </h2>
            <p className="t-legenda" style={{ marginBottom: 'var(--sp-4)' }}>
              {platformWarning}
            </p>

            <div style={{ display: 'flex', gap: 'var(--sp-3)', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={() => togglePlatform('outlook')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--sp-2)',
                  padding: 'var(--sp-3) var(--sp-4)',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${platforms.includes('outlook') ? 'var(--accent-border)' : 'var(--border-2)'}`,
                  background: platforms.includes('outlook') ? 'var(--accent-soft)' : 'var(--surface-3)',
                  color: platforms.includes('outlook') ? 'var(--accent-text)' : 'var(--text-2)',
                  cursor: 'pointer',
                  fontSize: 'var(--fs-sm)',
                  fontWeight: 'var(--fw-medium)',
                }}
              >
                <input
                  type="checkbox"
                  checked={platforms.includes('outlook')}
                  onChange={() => {}}
                  style={{ accentColor: 'var(--accent)' }}
                />
                Outlook
              </button>

              <button
                type="button"
                onClick={() => togglePlatform('instagram')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--sp-2)',
                  padding: 'var(--sp-3) var(--sp-4)',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${platforms.includes('instagram') ? 'var(--warning-border)' : 'var(--border-2)'}`,
                  background: platforms.includes('instagram') ? 'var(--warning-soft)' : 'var(--surface-3)',
                  color: platforms.includes('instagram') ? 'var(--warning-text)' : 'var(--text-2)',
                  cursor: 'pointer',
                  fontSize: 'var(--fs-sm)',
                  fontWeight: 'var(--fw-medium)',
                }}
              >
                <input
                  type="checkbox"
                  checked={platforms.includes('instagram')}
                  onChange={() => {}}
                  style={{ accentColor: 'var(--warning-solid)' }}
                />
                Instagram
              </button>
            </div>
            {errors.platforms && <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger-text)', marginTop: 8 }}>{errors.platforms}</p>}

            {platforms.includes('outlook') && platforms.includes('instagram') && (
              <Banner tone="info" style={{ marginTop: 'var(--sp-4)' }}>
                Modo completo: será criada uma conta Outlook real e depois uma conta Instagram vinculada ao mesmo email.
              </Banner>
            )}
          </CardBody>
        </Card>

        <div style={{ display: 'flex', gap: 'var(--sp-3)', justifyContent: 'flex-end' }}>
          <Button variant="outline" onClick={() => navigate('painel')}>
            Cancelar
          </Button>
          <Button variant="primary" type="submit" loading={loading} disabled={success !== null}>
            {loading ? (
              <>
                <LoaderCircle size={15} className="spin" />
                Criando...
              </>
            ) : (
              'Criar Conta'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
