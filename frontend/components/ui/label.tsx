import * as React from "react"
import * as LabelPrimitive from "@radix-ui/react-label"
import { cn } from "@/lib/utils"

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>
>(({ className, ...props }, ref) => (
  <LabelPrimitive.Root
    ref={ref}
    className={cn(
      "text-sm font-manrope font-light leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 transition-colors duration-200 ease-out",
      className
    )}
    {...props}
  />
))
Label.displayName = "Label"

export { Label }