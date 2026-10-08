import { LoaderCircle, type LucideIcon } from 'lucide-react';
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import ui from './ui.module.css';

export type ButtonVariant = 'secondary' | 'primary' | 'ghost' | 'outline' | 'danger' | 'dangerGhost';

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: ButtonVariant;
  size?: 'sm' | 'md' | 'lg';
  icon?: LucideIcon;
  loading?: boolean;
  label?: string;
  block?: boolean;
  children?: ReactNode;
}

const VARIANT: Record<ButtonVariant, string | undefined> = {
  secondary: undefined,
  primary: ui.btnPrimary,
  ghost: ui.btnGhost,
  outline: ui.btnOutline,
  danger: ui.btnDanger,
  dangerGhost: ui.btnDangerGhost,
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', icon: Icon, loading, block, children, label, className, type, ...rest },
  ref,
) {
  const iconSize = size === 'sm' ? 13 : size === 'lg' ? 17 : 15;
  return (
    <button
      ref={ref}
      type={type ?? 'button'}
      className={`${ui.btn} ${VARIANT[variant] ?? ''} ${size === 'sm' ? ui.btnSm : ''} ${size === 'lg' ? ui.btnLg : ''} ${block ? ui.btnBlock : ''} ${className ?? ''}`}
      disabled={loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <LoaderCircle size={iconSize} className="spin" aria-hidden /> : Icon ? <Icon size={iconSize} aria-hidden /> : null}
      {children ?? label}
    </button>
  );
});
