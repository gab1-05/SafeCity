import { toast as sonnerToast, Toaster } from "sonner";

export { sonnerToast as toast, Toaster };

export type ToastType = "default" | "success" | "error" | "warning" | "info" | "loading";

type ToastOptions = {
  description?: string;
  action?: { label: string; onClick: () => void };
  duration?: number;
};

type ToastMessage = string | { title: string; description?: string };

const normalizeToast = (message: ToastMessage, options?: ToastOptions) => {
  if (typeof message === "string") {
    return { message, options };
  }
  return { message: message.title, options: { ...options, description: message.description } };
};

export const useToast = () => {
  const callToast = (fn: typeof sonnerToast.success, message: ToastMessage, options?: ToastOptions) => {
    const { message: msg, options: opts } = normalizeToast(message, options);
    return fn(msg, opts);
  };

  const toastMethods = {
    success: (message: ToastMessage, options?: ToastOptions) =>
      callToast(sonnerToast.success, message, options),
    error: (message: ToastMessage, options?: ToastOptions) =>
      callToast(sonnerToast.error, message, options),
    warning: (message: ToastMessage, options?: ToastOptions) =>
      callToast(sonnerToast.warning, message, options),
    info: (message: ToastMessage, options?: ToastOptions) =>
      callToast(sonnerToast.info, message, options),
    loading: (message: ToastMessage, options?: ToastOptions) =>
      callToast(sonnerToast.loading, message, options),
    promise: <T,>(
      promise: Promise<T>,
      messages: {
        loading: string;
        success: string | ((data: T) => string);
        error: string | ((error: unknown) => string);
      }
    ) => sonnerToast.promise(promise, messages),
    dismiss: (id?: string | number) => sonnerToast.dismiss(id),
    custom: (component: React.ReactNode, options?: { duration?: number }) =>
      sonnerToast.custom(component as any, options),
  };

  return {
    ...toastMethods,
    toast: sonnerToast,
  };
};

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