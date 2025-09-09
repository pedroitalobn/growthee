import * as React from "react"
import { cn } from "@/lib/utils"

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          "btn inline-flex items-center justify-center rounded text-sm font-manrope font-light focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 transition-all duration-200 ease-out hover:scale-105 active:scale-95",
          {
            'btn-primary bg-[#1aff6e] text-black font-medium hover:bg-[#16e863] hover:shadow-lg': variant === 'default',
            'bg-destructive text-destructive-foreground hover:bg-destructive/90 hover:shadow-md': variant === 'destructive',
            'btn-secondary border border-border bg-background hover:bg-accent hover:text-accent-foreground hover:border-accent': variant === 'outline',
            'btn-secondary bg-secondary text-secondary-foreground hover:bg-secondary/80': variant === 'secondary',
            'hover:bg-accent hover:text-accent-foreground': variant === 'ghost',
            'text-primary underline-offset-4 hover:underline': variant === 'link'
          },
          {
            'h-8 px-3 py-1.5 text-sm': size === 'default', // Smaller default size
            'h-7 px-2.5 py-1 text-xs': size === 'sm', // Even smaller
            'h-9 px-4 py-2': size === 'lg', // Reduced from h-11
            'h-8 w-8': size === 'icon' // Smaller icon button
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }