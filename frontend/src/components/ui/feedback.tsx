import * as React from "react";
import { AlertTriangle, Inbox, Loader2, CheckCircle2, XCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./button";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted", className)}
      {...props}
    />
  );
}

export function Spinner({ className, size = "default" }: { className?: string; size?: "sm" | "default" | "lg" }) {
  const sizeClasses = {
    sm: "h-4 w-4",
    default: "h-5 w-5",
    lg: "h-8 w-8",
  };
  return (
    <Loader2
      className={cn("animate-spin text-primary", sizeClasses[size], className)}
      aria-label="Loading"
    />
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/30 py-12 text-center">
      {icon ? (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted/50 text-muted-foreground/50">
          {icon}
        </div>
      ) : (
        <Inbox className="mb-3 h-10 w-10 text-muted-foreground/50" aria-hidden />
      )}
      <p className="text-lg font-semibold text-foreground">{title}</p>
      {description && <p className="mt-2 max-w-sm text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-xl border border-danger/30 bg-danger/5 p-8 text-center"
    >
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-danger/10">
        <AlertTriangle className="h-6 w-6 text-danger" aria-hidden />
      </div>
      <p className="text-lg font-semibold text-danger">Something went wrong</p>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        {message || "An unexpected error occurred. Please try again."}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-6" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  icon,
  trend,
  trendLabel,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone?: "default" | "danger" | "warning" | "success";
  icon?: React.ReactNode;
  trend?: { value: number; label?: string };
  trendLabel?: string;
}) {
  const toneClasses = {
    default: "text-foreground",
    danger: "text-danger",
    warning: "text-warning",
    success: "text-success",
  }[tone];

  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground truncate">{label}</p>
          <p className={cn("mt-1 text-3xl font-bold tabular-nums", toneClasses)}>{value}</p>
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
          {trend && (
            <div className="mt-2 flex items-center gap-1 text-xs">
              <span className={cn("font-medium", trend.value >= 0 ? "text-success" : "text-danger")}>
                {trend.value >= 0 ? "▲" : "▼"} {Math.abs(trend.value)}%
              </span>
              {trendLabel && <span className="text-muted-foreground">{trendLabel}</span>}
            </div>
          )}
        </div>
        {icon && (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-muted/50 text-muted-foreground/50">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  variant = "default",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  variant?: "default" | "danger" | "warning";
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-xl animate-scale-in">
        <div className="flex items-start gap-3">
          <div className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
            destructive && "bg-danger/10 text-danger",
            variant === "warning" && "bg-warning/10 text-warning",
            !destructive && variant === "default" && "bg-primary/10 text-primary"
          )}>
            {destructive ? <XCircle className="h-5 w-5" /> : variant === "warning" ? <AlertTriangle className="h-5 w-5" /> : <Info className="h-5 w-5" />}
          </div>
          <div className="flex-1">
            <h2 id="confirm-title" className="text-lg font-semibold">{title}</h2>
            {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? "danger" : variant === "warning" ? "danger" : "default"}
            onClick={() => {
              onConfirm();
              onCancel();
            }}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function Alert({
  title,
  description,
  variant = "info",
  onDismiss,
}: {
  title: string;
  description?: string;
  variant?: "info" | "success" | "warning" | "danger";
  onDismiss?: () => void;
}) {
  const variantStyles = {
    info: "border-primary/30 bg-primary/5 text-primary",
    success: "border-success/30 bg-success/5 text-success",
    warning: "border-warning/30 bg-warning/5 text-warning",
    danger: "border-danger/30 bg-danger/5 text-danger",
  };

  const Icons = {
    info: Info,
    success: CheckCircle2,
    warning: AlertTriangle,
    danger: XCircle,
  };

  const Icon = Icons[variant];

  return (
    <div
      className={cn(
        "relative flex items-start gap-3 rounded-lg border p-4",
        variantStyles[variant]
      )}
      role="alert"
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="flex-1 min-w-0">
        <p className="font-medium">{title}</p>
        {description && <p className="mt-1 text-sm opacity-90">{description}</p>}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="shrink-0 rounded-md p-1 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          aria-label="Dismiss"
        >
          <XCircle className="h-4 w-4 opacity-50 hover:opacity-100" />
        </button>
      )}
    </div>
  );
}