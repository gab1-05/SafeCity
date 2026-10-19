import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary-600 shadow-sm hover:shadow-md transition-all active:scale-[0.98]",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary-600 shadow-sm hover:shadow-md transition-all active:scale-[0.98]",
        danger: "bg-danger text-danger-foreground hover:bg-danger-600 shadow-sm hover:shadow-md transition-all active:scale-[0.98]",
        success: "bg-success text-success-foreground hover:bg-success-600 shadow-sm hover:shadow-md transition-all active:scale-[0.98]",
        warning: "bg-warning text-warning-foreground hover:bg-warning-600 shadow-sm hover:shadow-md transition-all active:scale-[0.98]",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-all active:scale-[0.98]",
        ghost: "hover:bg-accent hover:text-accent-foreground transition-all active:scale-[0.98]",
        link: "text-primary underline-offset-2 hover:underline transition-colors",
        brand:
          "bg-gradient-to-r from-primary via-secondary to-primary/80 text-primary-foreground hover:from-primary/90 hover:to-primary/70 shadow-brand-sm hover:shadow-brand-lg transition-all active:scale-[0.98]",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-lg px-8 text-base",
        xl: "h-12 rounded-lg px-10 text-lg",
        icon: "h-10 w-10",
        iconSm: "h-8 w-8",
        iconLg: "h-12 w-12",
      },
    },
    compoundVariants: [
      { variant: "default", size: "lg", class: "shadow-md" },
      { variant: "brand", size: "lg", class: "shadow-brand-md" },
      { variant: "danger", size: "lg", class: "shadow-md" },
    ],
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      loading,
      leftIcon,
      rightIcon,
      type = "button",
      disabled,
      children,
      ...props
    },
    ref,
  ) => (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size, className }), fullWidth && "w-full")}
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading}
      {...props}
    >
      {loading ? (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" aria-hidden>
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : leftIcon ? (
        <span aria-hidden>{leftIcon}</span>
      ) : null}
      {children}
      {!loading && rightIcon && <span aria-hidden>{rightIcon}</span>}
    </button>
  ),
);
Button.displayName = "Button";

export { Button, buttonVariants };
