import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useTranslations } from "next-intl"

interface RecentActivityProps {
  transactions?: any[]
}

export function RecentActivity({ transactions = [] }: RecentActivityProps) {
  const t = useTranslations('recentActivity');
  
  const mockActivities = [
    { id: 1, action: t('companyEnrichment'), timestamp: t('twoMinutesAgo'), status: 'success' },
    { id: 2, action: t('personEnrichment'), timestamp: t('fiveMinutesAgo'), status: 'success' },
    { id: 3, action: t('planUpgrade'), timestamp: t('oneHourAgo'), status: 'success' }
  ]

  const displayActivities = transactions.length > 0 ? transactions : mockActivities

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('recentActivity')}</CardTitle>
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