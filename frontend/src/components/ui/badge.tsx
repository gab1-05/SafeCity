import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-all",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground border border-primary/20 shadow-sm",
        secondary: "bg-secondary text-secondary-foreground border border-secondary/20 shadow-sm",
        success: "bg-success text-success-foreground border border-success/20 shadow-sm",
        warning: "bg-warning text-warning-foreground border border-warning/20 shadow-sm",
        danger: "bg-danger text-danger-foreground border border-danger/20 shadow-sm",
        outline: "border border-border text-foreground hover:bg-accent",
        ghost: "text-muted-foreground hover:bg-accent hover:text-foreground",
        brand:
          "bg-gradient-to-r from-primary to-secondary text-primary-foreground shadow-brand-sm",
      },
      size: {
        sm: "px-2 py-0.5 text-[10px]",
        default: "px-2.5 py-0.5 text-xs",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, size, ...props }, ref) => (
    <span ref={ref} className={cn(badgeVariants({ variant, size, className }))} {...props} />
  ),
);
Badge.displayName = "Badge";

export { Badge, badgeVariants };
