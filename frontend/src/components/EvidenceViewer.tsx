import { Eye, EyeOff, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { Button } from './Button';
import ui from './ui.module.css';

interface EvidenceViewerProps {
  email: string;
  password: string;
  platform: string;
  screenshotUrl?: string;
  description?: string;
}

export function EvidenceViewer({ email, password, platform, screenshotUrl, description }: EvidenceViewerProps) {
  const [showPassword, setShowPassword] = useState(false);
  const [copied, setCopied] = useState<'email' | 'password' | null>(null);

  const copyToClipboard = async (text: string, field: 'email' | 'password') => {
    await navigator.clipboard.writeText(text);
    setCopied(field);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className={ui.evidenceContainer}>
      {/* Credentials */}
      <div>
        <h3 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-3)' }}>
          Credenciais
        </h3>

        <div className={ui.credentialRow}>
          <span className={ui.credentialLabel}>Email</span>
          <span className={ui.credentialValue}>{email}</span>
          <div className={ui.credentialActions}>
            <Button
              variant="ghost"
              size="sm"
              icon={copied === 'email' ? Check : Copy}
              onClick={() => copyToClipboard(email, 'email')}
              label="Copiar email"
            />
          </div>
        </div>

        <div className={ui.credentialRow}>
          <span className={ui.credentialLabel}>Senha</span>
          <span className={ui.credentialValue}>
            {showPassword ? password : '••••••••••••'}
          </span>
          <div className={ui.credentialActions}>
            <Button
              variant="ghost"
              size="sm"
              icon={showPassword ? EyeOff : Eye}
              onClick={() => setShowPassword(!showPassword)}
              label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
            />
            <Button
              variant="ghost"
              size="sm"
              icon={copied === 'password' ? Check : Copy}
              onClick={() => copyToClipboard(password, 'password')}
              label="Copiar senha"
            />
          </div>
        </div>
      </div>

      {/* Screenshot Evidence */}
      {screenshotUrl && (
        <div>
          <h3 className="t-titulo-secao" style={{ marginBottom: 'var(--sp-3)' }}>
            Evidência - {platform === 'outlook' ? 'Outlook' : 'Instagram'}
          </h3>
          <div className={ui.evidenceImage}>
            <img src={screenshotUrl} alt={`Evidência de login no ${platform}`} />
            {description && (
              <div className={ui.evidenceCaption}>{description}</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
