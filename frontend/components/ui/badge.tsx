import * as React from "react"
import { cn } from "@/lib/utils"

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "badge inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 transition-all duration-200 ease-out",
        {
          'border-transparent bg-primary text-primary-foreground hover:bg-primary/80 hover:scale-105': variant === 'default',
          'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80 hover:scale-105': variant === 'secondary',
          'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80 hover:scale-105': variant === 'destructive',
          'text-foreground hover:bg-accent/50': variant === 'outline'
        },
        className
      )}
      {...props}
    />
  )
}

export { Badge }