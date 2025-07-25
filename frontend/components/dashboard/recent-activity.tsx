import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface RecentActivityProps {
  transactions?: any[]
}

export function RecentActivity({ transactions = [] }: RecentActivityProps) {
  const mockActivities = [
    { id: 1, action: 'Enriquecimento de empresa', timestamp: '2 min atrás', status: 'success' },
    { id: 2, action: 'Enriquecimento de pessoa', timestamp: '5 min atrás', status: 'success' },
    { id: 3, action: 'Upgrade de plano', timestamp: '1 hora atrás', status: 'success' }
  ]

  const displayActivities = transactions.length > 0 ? transactions : mockActivities

  return (
    <Card>
      <CardHeader>
        <CardTitle>Atividade Recente</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {displayActivities.map((activity) => (
            <div key={activity.id} className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{activity.action}</p>
                <p className="text-xs text-muted-foreground">{activity.timestamp}</p>
              </div>
              <Badge variant={activity.status === 'success' ? 'default' : 'destructive'}>
                {activity.status}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}