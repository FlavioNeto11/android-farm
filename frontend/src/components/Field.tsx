import { type InputHTMLAttributes, type SelectHTMLAttributes, type TextareaHTMLAttributes, forwardRef } from 'react';
import ui from './ui.module.css';

export const TextInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label?: string }>(
  function TextInput({ label, className, ...rest }, ref) {
    return (
      <label className={ui.field}>
        {label && <span className={ui.fieldLabel}>{label}</span>}
        <input ref={ref} className={`${ui.fieldInput} ${className ?? ''}`} {...rest} />
      </label>
    );
  },
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & { label?: string }>(
  function Select({ label, className, children, ...rest }, ref) {
    return (
      <label className={ui.field}>
        {label && <span className={ui.fieldLabel}>{label}</span>}
        <select ref={ref} className={`${ui.fieldInput} ${className ?? ''}`} {...rest}>
          {children}
        </select>
      </label>
    );
  },
);

export const TextArea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }>(
  function TextArea({ label, className, ...rest }, ref) {
    return (
      <label className={ui.field}>
        {label && <span className={ui.fieldLabel}>{label}</span>}
        <textarea ref={ref} className={`${ui.fieldInput} ${className ?? ''}`} {...rest} />
      </label>
    );
  },
);
