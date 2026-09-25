import { toast as sonnerToast, Toaster, type ExternalToast } from "sonner";

export { Toaster };
export { sonnerToast as sonner };

export type ToastVariant =
  | "default"
  | "success"
  | "error"
  | "warning"
  | "info"
  | "loading";

/** Structured payload used across the app: `toast({ title, description, variant })`. */
export type ToastInput =
  | string
  | {
      title: string;
      description?: string;
      variant?: ToastVariant;
      id?: string | number;
      duration?: number;
      action?: { label: string; onClick: () => void };
    };

type ToastOptions = Omit<Extract<ToastInput, object>, "title" | "variant">;

type ResolvedToast = {
  title: string;
  description?: string;
  variant: ToastVariant;
  options: ExternalToast;
};

function resolve(input: ToastInput, extra?: ToastOptions): ResolvedToast {
  if (typeof input === "string") {
    return { title: input, variant: "default", options: { ...extra } };
  }
  const { title, description, variant = "default", ...options } = input;
  return { title, description, variant, options: { ...options, ...extra } };
}

function show(input: ToastInput, extra?: ToastOptions): string | number {
  const { title, description, variant, options } = resolve(input, extra);
  const payload: ExternalToast = description ? { ...options, description } : options;
  switch (variant) {
    case "success":
      return sonnerToast.success(title, payload);
    case "error":
      return sonnerToast.error(title, payload);
    case "warning":
      return sonnerToast.warning(title, payload);
    case "info":
      return sonnerToast.info(title, payload);
    case "loading":
      return sonnerToast.loading(title, payload);
    default:
      return sonnerToast(title, payload);
  }
}

/** `toast` keeps sonner's method surface so `toast.success(...)` also works. */
export const toast = Object.assign(show, {
  success: sonnerToast.success,
  error: sonnerToast.error,
  warning: sonnerToast.warning,
  info: sonnerToast.info,
  loading: sonnerToast.loading,
  message: sonnerToast.message,
  promise: sonnerToast.promise,
  dismiss: sonnerToast.dismiss,
  custom: sonnerToast.custom,
});

const toastApi = {
  toast: show,
  success: (message: ToastInput, options?: ToastOptions) =>
    show(typeof message === "string" ? message : { ...message, variant: "success" }, options),
  error: (message: ToastInput, options?: ToastOptions) =>
    show(typeof message === "string" ? message : { ...message, variant: "error" }, options),
  warning: (message: ToastInput, options?: ToastOptions) =>
    show(typeof message === "string" ? message : { ...message, variant: "warning" }, options),
  info: (message: ToastInput, options?: ToastOptions) =>
    show(typeof message === "string" ? message : { ...message, variant: "info" }, options),
  loading: (message: ToastInput, options?: ToastOptions) =>
    show(typeof message === "string" ? message : { ...message, variant: "loading" }, options),
  promise: sonnerToast.promise,
  dismiss: sonnerToast.dismiss,
  custom: sonnerToast.custom,
};

/**
 * Stable singleton — the object identity never changes, so components can put
 * it in `useEffect` dependency arrays without re-subscribing on every render.
 */
export const useToast = () => toastApi;

export const ToasterComponent = () => (
  <Toaster
    position="bottom-right"
    theme="system"
    className="toaster-group"
    toastOptions={{
      classNames: {
        toast: "rounded-xl border bg-card text-card-foreground shadow-xl",
        description: "text-sm text-muted-foreground",
        actionButton: "rounded-md bg-primary text-primary-foreground hover:bg-primary/90",
        cancelButton: "rounded-md border border-border bg-background hover:bg-accent",
        closeButton: "text-muted-foreground hover:text-foreground",
      },
    }}
  />
);
