import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useTranslations } from 'next-intl'

interface CreateEndpointDialogProps {
  open?: boolean
  onClose?: () => void
  onOpenChange?: (open: boolean) => void
}

export function CreateEndpointDialog({ open, onClose, onOpenChange }: CreateEndpointDialogProps) {
  const t = useTranslations('admin')
  const [name, setName] = React.useState('')
  const [url, setUrl] = React.useState('')

  const handleClose = () => {
    if (onClose) {
      onClose()
    }
    if (onOpenChange) {
      onOpenChange(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{t('createNewEndpoint')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">{t('name')}</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('endpointNamePlaceholder')}
            />
          </div>
          <div>
            <label className="text-sm font-medium">{t('url')}</label>
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t('urlPlaceholder')}
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={handleClose}>
              {t('cancel')}
            </Button>
            <Button onClick={handleClose}>
              {t('create')}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}