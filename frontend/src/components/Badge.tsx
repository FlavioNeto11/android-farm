import type { ReactNode } from 'react';
import ui from './ui.module.css';

type BadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

const TONE: Record<BadgeTone, string> = {
  success: ui.badgeSuccess,
  warning: ui.badgeWarning,
  danger: ui.badgeDanger,
  info: ui.badgeInfo,
  neutral: ui.badgeNeutral,
};

export function Badge({ tone = 'neutral', icon, children }: { tone?: BadgeTone; icon?: ReactNode; children: ReactNode }) {
  return (
    <span className={`${ui.badge} ${TONE[tone]}`}>
      {icon}
      {children}
    </span>
  );
}
