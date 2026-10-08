import type { CSSProperties, ReactNode } from 'react';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';
import ui from './ui.module.css';

type BannerTone = 'success' | 'warning' | 'danger' | 'info';

const ICONS: Record<BannerTone, typeof AlertCircle> = {
  success: CheckCircle,
  warning: AlertTriangle,
  danger: AlertCircle,
  info: Info,
};

const TONE: Record<BannerTone, string> = {
  success: ui.bannerSuccess,
  warning: ui.bannerWarning,
  danger: ui.bannerDanger,
  info: ui.bannerInfo,
};

export function Banner({ tone = 'info', style, children }: { tone?: BannerTone; style?: CSSProperties; children: ReactNode }) {
  const Icon = ICONS[tone];
  return (
    <div className={`${ui.banner} ${TONE[tone]}`} style={style}>
      <Icon size={16} aria-hidden />
      <span>{children}</span>
    </div>
  );
}
