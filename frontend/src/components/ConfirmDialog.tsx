import { useEffect, useRef } from 'react';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  destructive?: boolean;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirmar',
  cancelLabel = 'Cancelar',
  onConfirm,
  onCancel,
  destructive = false,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && cancelRef.current) {
      cancelRef.current.focus();
    }
  }, [open]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [open, onCancel]);

  if (!open) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onCancel();
    }
  };

  return (
    <div
      ref={overlayRef}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--overlay)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 'var(--z-popover)',
      }}
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-desc"
    >
      <div
        style={{
          background: 'var(--surface-1)',
          border: '1px solid var(--border-1)',
          borderRadius: 'var(--radius-lg)',
          padding: 'var(--sp-6)',
          maxWidth: '400px',
          width: '90%',
          boxShadow: '0 20px 60px var(--shadow-xl)',
        }}
      >
        <h3 id="confirm-dialog-title" style={{ fontSize: 'var(--fs-xl)', fontWeight: 'var(--fw-semibold)', margin: '0 0 var(--sp-2)' }}>
          {title}
        </h3>
        <p id="confirm-dialog-desc" style={{ fontSize: 'var(--fs-base)', color: 'var(--text-2)', margin: '0 0 var(--sp-6)' }}>
          {description}
        </p>
        <div style={{ display: 'flex', gap: 'var(--sp-3)', justifyContent: 'flex-end' }}>
          <button
            ref={cancelRef}
            type="button"
            style={{
              padding: 'var(--sp-2) var(--sp-4)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-2)',
              background: 'transparent',
              color: 'var(--text-1)',
              cursor: 'pointer',
              fontSize: 'var(--fs-sm)',
              fontWeight: 'var(--fw-medium)',
            }}
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            style={{
              padding: 'var(--sp-2) var(--sp-4)',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: destructive ? 'var(--danger)' : 'var(--accent)',
              color: destructive ? 'var(--text-on-danger)' : 'var(--text-on-accent)',
              cursor: 'pointer',
              fontSize: 'var(--fs-sm)',
              fontWeight: 'var(--fw-medium)',
            }}
            onClick={() => {
              onConfirm();
              onCancel();
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
