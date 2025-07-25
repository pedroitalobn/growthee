import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CreateEndpointDialogProps {
  open?: boolean
  onClose?: () => void
  onOpenChange?: (open: boolean) => void
}

export function CreateEndpointDialog({ open, onClose, onOpenChange }: CreateEndpointDialogProps) {
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
          <CardTitle>Criar Novo Endpoint</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Nome</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Nome do endpoint"
            />
          </div>
          <div>
            <label className="text-sm font-medium">URL</label>
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://api.exemplo.com"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={handleClose}>
              Cancelar
            </Button>
            <Button onClick={handleClose}>
              Criar
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}