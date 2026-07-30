/**
 * Reusable UI primitives — Button, Input, Select, Tooltip, Modal,
 * Alert, Disclaimer, SourceCitation, EmptyState, ErrorState.
 * All components are presentation-only; wire event handlers and data from above.
 */

import { useState, useRef, useEffect, type ReactNode } from 'react'

// ─── Button ──────────────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline-navy'
type ButtonSize = 'xs' | 'sm' | 'md' | 'lg'

const BTN_VARIANTS: Record<ButtonVariant, string> = {
  primary:       'bg-civic text-white hover:bg-civic-hover active:bg-civic-hover shadow-sm',
  secondary:     'bg-surface text-civic border border-civic hover:bg-civic-pale active:bg-civic-pale',
  ghost:         'text-muted hover:text-navy hover:bg-soft active:bg-soft-mid',
  danger:        'bg-red-600 text-white hover:bg-red-700 active:bg-red-700',
  'outline-navy':'border border-navy/20 text-navy hover:bg-navy/5 active:bg-navy/10',
}

const BTN_SIZES: Record<ButtonSize, string> = {
  xs: 'text-xs px-3 py-1.5 rounded-lg',
  sm: 'text-sm px-3.5 py-2 rounded-lg',
  md: 'text-sm px-4 py-2.5 rounded-xl',
  lg: 'text-base px-5 py-3 rounded-xl',
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
  iconRight?: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconRight,
  children,
  className = '',
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 font-semibold transition-all duration-150
        ${BTN_VARIANTS[variant]} ${BTN_SIZES[size]}
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}`}
    >
      {loading ? (
        <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      ) : icon}
      {children}
      {!loading && iconRight}
    </button>
  )
}

// ─── TextInput ───────────────────────────────────────────────────────────────

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  icon?: ReactNode
}

export function TextInput({ label, error, icon, className = '', ...rest }: InputProps) {
  return (
    <div className="space-y-1.5">
      {label && <label className="block text-sm font-medium text-navy">{label}</label>}
      <div className="relative">
        {icon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none">
            {icon}
          </span>
        )}
        <input
          {...rest}
          className={`w-full py-2.5 px-3.5 ${icon ? 'pl-9' : ''} rounded-xl border text-navy text-sm
            bg-surface placeholder:text-muted-light
            border-border hover:border-border-strong
            focus:outline-none focus:ring-2 focus:ring-civic focus:border-transparent
            transition-all duration-150
            ${error ? 'border-red-400 focus:ring-red-400' : ''}
            ${className}`}
        />
      </div>
      {error && <p className="text-xs text-red-600 flex items-center gap-1"><span>⚠</span>{error}</p>}
    </div>
  )
}

// ─── SelectInput ─────────────────────────────────────────────────────────────

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

export function SelectInput({ label, children, className = '', ...rest }: SelectProps) {
  return (
    <div className="space-y-1.5">
      {label && <label className="block text-sm font-medium text-navy">{label}</label>}
      <select
        {...rest}
        className={`py-2.5 px-3.5 pr-8 rounded-xl border border-border hover:border-border-strong
          bg-surface text-navy text-sm
          focus:outline-none focus:ring-2 focus:ring-civic focus:border-transparent
          transition-all duration-150 appearance-none
          ${className}`}
        style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%236b7a99'%3E%3Cpath fill-rule='evenodd' d='M4.22 6.22a.75.75 0 011.06 0L8 8.94l2.72-2.72a.75.75 0 111.06 1.06l-3.25 3.25a.75.75 0 01-1.06 0L4.22 7.28a.75.75 0 010-1.06z'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px' }}
      >
        {children}
      </select>
    </div>
  )
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

export function Tooltip({ children, content }: { children: ReactNode; content: string }) {
  const [open, setOpen] = useState(false)
  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 whitespace-nowrap
          bg-navy text-white text-xs rounded-lg px-3 py-1.5 shadow-lg pointer-events-none
          after:content-[''] after:absolute after:top-full after:left-1/2 after:-translate-x-1/2
          after:border-4 after:border-transparent after:border-t-navy">
          {content}
        </span>
      )}
    </span>
  )
}

// ─── Modal ───────────────────────────────────────────────────────────────────

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const MODAL_SIZES = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl', xl: 'max-w-6xl' }

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const previouslyFocused = useRef<HTMLElement | null>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    if (!open) return

    previouslyFocused.current = document.activeElement as HTMLElement | null
    const dialog = dialogRef.current
    const focusable = dialog?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    if (focusable && focusable.length > 0) focusable[0].focus()
    else dialog?.focus()

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCloseRef.current()
        return
      }
      if (e.key !== 'Tab' || !dialog) return
      const items = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      if (items.length === 0) return
      const first = items[0]
      const last = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('keydown', handleKey)
      previouslyFocused.current?.focus()
    }
  }, [open])

  if (!open) return null

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[100] bg-navy/40 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === overlayRef.current) onClose() }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
        className={`${MODAL_SIZES[size]} w-full bg-surface rounded-2xl shadow-2xl border border-border overflow-hidden`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 id="modal-title" className="font-semibold text-navy text-base" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
            {title}
          </h3>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-navy hover:bg-soft transition-colors"
            aria-label="Close"
          >
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
              <path d="M3.22 3.22a.75.75 0 011.06 0L8 6.94l3.72-3.72a.75.75 0 111.06 1.06L9.06 8l3.72 3.72a.75.75 0 11-1.06 1.06L8 9.06l-3.72 3.72a.75.75 0 01-1.06-1.06L6.94 8 3.22 4.28a.75.75 0 010-1.06z"/>
            </svg>
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

// ─── Alert ───────────────────────────────────────────────────────────────────

type AlertType = 'info' | 'success' | 'warning' | 'error'

const ALERT_STYLES: Record<AlertType, string> = {
  info:    'bg-civic-pale border-civic/20 text-civic',
  success: 'bg-teal-light border-teal/20 text-teal',
  warning: 'bg-amber-50 border-amber-200 text-amber-800',
  error:   'bg-red-50 border-red-200 text-red-800',
}

const ALERT_ICONS: Record<AlertType, ReactNode> = {
  info: <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 shrink-0"><path fillRule="evenodd" clipRule="evenodd" d="M8 1.5a6.5 6.5 0 100 13A6.5 6.5 0 008 1.5zm-.75 3.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zm.75 5.75a.75.75 0 100 1.5.75.75 0 000-1.5z"/></svg>,
  success: <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 shrink-0"><path fillRule="evenodd" clipRule="evenodd" d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>,
  warning: <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 shrink-0 text-amber-500"><path fillRule="evenodd" clipRule="evenodd" d="M8.485 1.495c.673-1.167 2.357-1.167 3.03 0l5.28 9.167c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625l5.28-9.167zM8 5.5a.75.75 0 01.75.75v2.5a.75.75 0 01-1.5 0v-2.5A.75.75 0 018 5.5zm0 6.5a.75.75 0 100-1.5.75.75 0 000 1.5z"/></svg>,
  error:   <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 shrink-0 text-red-500"><path fillRule="evenodd" clipRule="evenodd" d="M8 1.5a6.5 6.5 0 100 13A6.5 6.5 0 008 1.5zM6.28 5.22a.75.75 0 00-1.06 1.06L6.94 8 5.22 9.72a.75.75 0 101.06 1.06L8 9.06l1.72 1.72a.75.75 0 101.06-1.06L9.06 8l1.72-1.72a.75.75 0 00-1.06-1.06L8 6.94 6.28 5.22z"/></svg>,
}

export function Alert({ type = 'info', children }: { type?: AlertType; children: ReactNode }) {
  return (
    <div className={`flex items-start gap-2.5 px-4 py-3 rounded-xl border text-sm leading-relaxed ${ALERT_STYLES[type]}`}>
      <span className="mt-0.5">{ALERT_ICONS[type]}</span>
      <div>{children}</div>
    </div>
  )
}

// ─── Disclaimer ──────────────────────────────────────────────────────────────

export function Disclaimer({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 px-4 py-3.5 rounded-xl bg-navy/4 border border-navy/10 text-xs text-navy/60 leading-relaxed">
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 shrink-0 text-muted mt-0.5">
        <path fillRule="evenodd" clipRule="evenodd" d="M8 1.5a6.5 6.5 0 100 13A6.5 6.5 0 008 1.5zm-.75 3.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zm.75 5.75a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
      </svg>
      {children}
    </div>
  )
}

// ─── PlaceholderBadge ─────────────────────────────────────────────────────────

export function PlaceholderBadge({ text = 'Placeholder data — for design purposes only' }: { text?: string }) {
  return (
    <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium">
      <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5 text-amber-500">
        <path fillRule="evenodd" clipRule="evenodd" d="M8 1.5a6.5 6.5 0 100 13A6.5 6.5 0 008 1.5zm-.75 3.75a.75.75 0 011.5 0v3.5a.75.75 0 01-1.5 0v-3.5zm.75 5.75a.75.75 0 100 1.5.75.75 0 000-1.5z"/>
      </svg>
      {text}
    </div>
  )
}

// ─── SourceCitation ──────────────────────────────────────────────────────────

interface SourceCitationProps {
  title: string
  url: string
}

export function SourceCitation({ title, url }: SourceCitationProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5 border-b border-border last:border-0">
      <div className="min-w-0">
        <p className="text-xs font-medium text-navy truncate">{title}</p>
      </div>
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-xs text-civic hover:text-civic-light font-medium"
        >
          View ↗
        </a>
      )}
    </div>
  )
}

// ─── EmptyState ──────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center text-center py-16 px-6">
      {icon && (
        <div className="w-16 h-16 rounded-full bg-civic-pale border border-civic/20 flex items-center justify-center mb-4 text-civic-light">
          {icon}
        </div>
      )}
      <h3 className="font-semibold text-navy text-lg mb-2" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
        {title}
      </h3>
      {description && <p className="text-muted text-sm max-w-xs leading-relaxed mb-5">{description}</p>}
      {action}
    </div>
  )
}

// ─── ErrorState ──────────────────────────────────────────────────────────────

export function ErrorState({ title, description, onRetry }: { title: string; description?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center text-center py-16 px-6">
      <div className="w-16 h-16 rounded-full bg-red-50 border border-red-200 flex items-center justify-center mb-4">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-7 h-7 text-red-500">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
        </svg>
      </div>
      <h3 className="font-semibold text-navy text-lg mb-2" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>{title}</h3>
      {description && <p className="text-muted text-sm max-w-xs leading-relaxed mb-5">{description}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 rounded-xl bg-civic text-white text-sm font-semibold hover:bg-civic-hover transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  )
}

// ─── Skeleton ────────────────────────────────────────────────────────────────

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-lg ${className}`} />
}
