import * as React from "react"

interface UsageChartProps {
  data?: any[]
}

export function UsageChart({ data = [] }: UsageChartProps) {
  return (
    <div className="h-64 flex items-center justify-center text-muted-foreground">
      <div className="text-center">
        <p>Gráfico de uso</p>
        <p className="text-sm mt-2">{data.length} transações</p>
      </div>
    </div>
  )
}