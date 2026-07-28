import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium outline-none transition duration-150 focus-visible:ring-2 focus-visible:ring-[var(--focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--canvas)] disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)]",
        default: "bg-[var(--accent)] text-white hover:bg-[var(--accent-strong)]",
        secondary: "border border-[var(--line-strong)] bg-[var(--panel)] text-[var(--ink)] hover:border-[var(--ink-subtle)] hover:bg-[var(--panel-raised)]",
        outline: "border border-[var(--line-strong)] bg-transparent text-[var(--ink)] hover:bg-[var(--panel-raised)]",
        quiet: "text-[var(--ink-muted)] hover:bg-[var(--panel-raised)] hover:text-[var(--ink)]",
        danger: "border border-[var(--danger)] bg-[var(--danger-soft)] text-[var(--danger)] hover:brightness-95",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-3.5",
        lg: "h-11 px-4",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

function ButtonImpl(
  { className, variant, size, type = "button", asChild = false, ...props }: ButtonProps,
  ref: React.ForwardedRef<HTMLButtonElement>,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      {...(asChild ? {} : { type })}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export const Button = forwardRef(ButtonImpl);

Button.displayName = "Button";