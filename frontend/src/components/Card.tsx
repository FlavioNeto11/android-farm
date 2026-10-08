import type { CSSProperties, ReactNode } from 'react';
import ui from './ui.module.css';

export function Card({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return <div className={`${ui.card} ${className ?? ''}`} style={style}>{children}</div>;
}

export function CardHeader({ children }: { children: ReactNode }) {
  return <div className={ui.cardHeader}>{children}</div>;
}

export function CardBody({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return <div className={`${ui.cardBody} ${className ?? ''}`} style={style}>{children}</div>;
}
