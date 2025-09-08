'use client'

import { useMemo } from 'react'
import { useTranslations } from 'next-intl'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface UsageChartProps {
  data?: any[]
}

interface ChartDataPoint {
  date: string
  credits: number
  requests: number
}

export default function UsageChart({ data = [] }: UsageChartProps) {
  const t = useTranslations('dashboard');
  
  // Processar dados para o gráfico
  const processChartData = (): ChartDataPoint[] => {
    if (!data || data.length === 0) {
      // Return empty array when no real data is available
      return []
    }

    // Agrupar transações por data
    const groupedData = data.reduce((acc, transaction: any) => {
      if (!transaction) return acc
      
      const date = new Date(transaction.createdAt || transaction.timestamp).toISOString().split('T')[0]
      
      if (!acc[date]) {
        acc[date] = { date, credits: 0, requests: 0 }
      }
      
      acc[date].credits += transaction.credits || transaction.amount || 1
      acc[date].requests += 1
      
      return acc
    }, {} as Record<string, ChartDataPoint>)

    const values = Object.values(groupedData) as ChartDataPoint[]
    return values.sort((a, b) => a.date.localeCompare(b.date))
  }

  const chartData = processChartData()

  if (chartData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-muted-foreground fade-in">
        <div className="text-center">
          <p>{t('noDataAvailable')}</p>
              <p className="text-sm mt-2">{t('dataWillAppear')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="chart-container fade-in">
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" className="opacity-30 transition-opacity duration-300" />
        <XAxis 
          dataKey="date" 
          tickFormatter={(value) => {
            try {
              return format(new Date(value), 'dd/MM', { locale: ptBR })
            } catch {
              return value
            }
          }}
          className="text-xs"
        />
        <YAxis className="text-xs" />
        <Tooltip 
          labelFormatter={(value) => {
            try {
              return format(new Date(value), 'dd/MM/yyyy', { locale: ptBR })
            } catch {
              return value
            }
          }}
          formatter={(value: number, name: string) => [
            value,
            name === 'credits' ? t('credits') : t('requests')
          ]}
          contentStyle={{
            backgroundColor: 'hsl(var(--card))',
            border: '1px solid hsl(var(--border))',
            borderRadius: '6px'
          }}
        />
        <Line 
          type="monotone" 
          dataKey="credits" 
          stroke="hsl(var(--primary))" 
          strokeWidth={2}
          dot={{ fill: 'hsl(var(--primary))', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 8, stroke: 'hsl(var(--primary))', strokeWidth: 3, fill: 'hsl(var(--primary))', fillOpacity: 0.8 }}
          animationDuration={800}
          animationEasing="ease-out"
        />
        <Line 
          type="monotone" 
          dataKey="requests" 
          stroke="hsl(var(--secondary))" 
          strokeWidth={2}
          dot={{ fill: 'hsl(var(--secondary))', strokeWidth: 2, r: 4 }}
          activeDot={{ r: 8, stroke: 'hsl(var(--secondary))', strokeWidth: 3, fill: 'hsl(var(--secondary))', fillOpacity: 0.8 }}
          animationDuration={800}
          animationEasing="ease-out"
        />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}