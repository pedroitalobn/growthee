'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { ApiDocumentationSkeleton } from '@/components/ui/loading'
import { apiClient } from '@/lib/api/client'
import { useAuthStore } from '@/lib/store/auth-store'
import { 
  Book, 
  Play, 
  Copy, 
  ChevronDown, 
  ChevronRight, 
  Code, 
  Terminal, 
  FileText,
  Zap,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react'

const toast = {
  success: (message: string) => console.log('Success:', message),
  error: (message: string) => console.error('Error:', message)
}

interface ApiEndpoint {
  id: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  path: string
  name: string
  description: string
  category: string
  parameters: Array<{
    name: string
    type: string
    required: boolean
    description: string
    example?: any
  }>
  requestBody?: {
    type: string
    properties: Record<string, any>
    example: any
  }
  responses: Array<{
    status: number
    description: string
    example: any
  }>
  creditsRequired: number
  rateLimit?: {
    requests: number
    period: string
  }
}

interface TestResult {
  success: boolean
  status: number
  data: any
  error?: string
  executionTime: number
  creditsUsed: number
}

const docsApi = {
  getEndpoints: async (): Promise<ApiEndpoint[]> => {
    const response = await apiClient.get('/api/v1/docs/endpoints')
    return response.data
  },
  testEndpoint: async (endpointId: string, params: any, body?: any): Promise<TestResult> => {
    const response = await apiClient.post(`/api/v1/docs/test/${endpointId}`, {
      params,
      body
    })
    return response.data
  }
}

export function ApiDocumentation() {
  const t = useTranslations('apiDocs')
  const { user } = useAuthStore()
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null)
  const [testParams, setTestParams] = useState<Record<string, any>>({})
  const [testBody, setTestBody] = useState('')
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [activeTab, setActiveTab] = useState<'details' | 'test' | 'examples' | 'curl'>('details')

  const { data: endpoints = [], isLoading } = useQuery({
    queryKey: ['api-endpoints'],
    queryFn: docsApi.getEndpoints
  })

  const testMutation = useMutation({
    mutationFn: ({ endpointId, params, body }: { endpointId: string, params: any, body?: any }) =>
      docsApi.testEndpoint(endpointId, params, body),
    onSuccess: (result) => {
      setTestResult(result)
      if (result.success) {
        toast.success('Teste executado com sucesso!')
      } else {
        toast.error('Erro no teste da API')
      }
    },
    onError: () => {
      toast.error('Erro ao executar teste')
    }
  })

  const categories = Array.from(new Set(endpoints.map(e => e.category)))

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId)
    } else {
      newExpanded.add(sectionId)
    }
    setExpandedSections(newExpanded)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success(t('copiedToClipboard'))
  }

  const generateCurlCommand = (endpoint: ApiEndpoint) => {
    let curl = `curl -X ${endpoint.method} \\
`
    curl += `  "${process.env.NEXT_PUBLIC_API_URL}${endpoint.path}" \\
`
    curl += `  -H "Authorization: Bearer YOUR_API_KEY" \\
`
    curl += `  -H "Content-Type: application/json"`
    
    if (endpoint.requestBody && endpoint.method !== 'GET') {
      curl += ` \\
  -d '${JSON.stringify(endpoint.requestBody.example, null, 2)}'`
    }
    
    return curl
  }

  const handleTest = () => {
    // Prevent multiple simultaneous requests
    if (testMutation.isPending) {
      return
    }

    if (!selectedEndpoint) return
    
    let body
    if (testBody.trim()) {
      try {
        body = JSON.parse(testBody)
      } catch (error) {
        toast.error(t('invalidJson'))
        return
      }
    }

    testMutation.mutate({
      endpointId: selectedEndpoint.id,
      params: testParams,
      body
    })
  }

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-green-100 text-green-800 border-green-200'
      case 'POST': return 'bg-blue-100 text-blue-800 border-blue-200'
      case 'PUT': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'DELETE': return 'bg-red-100 text-red-800 border-red-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  if (isLoading) {
    return <ApiDocumentationSkeleton />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Book className="h-6 w-6" />
        <h2 className="text-2xl font-bold">{t('apiDocumentation')}</h2>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t('availableEndpoints')}</CardTitle>
              <CardDescription>
                Explore todos os endpoints disponíveis da API
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[600px] overflow-y-auto">
                <div className="space-y-4">
                  {categories.map(category => {
                    const categoryEndpoints = endpoints.filter(e => e.category === category)
                    const isExpanded = expandedSections.has(category)
                    
                    return (
                      <div key={category}>
                        <div>
                          <Button
                            variant="ghost"
                            className="w-full justify-between p-2 h-auto font-medium"
                            onClick={() => toggleSection(category)}
                          >
                            <span className="capitalize">{category}</span>
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                          </Button>
                        </div>
                        <div className={`overflow-hidden transition-all duration-300 ease-out ${isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}>
                          <div className="mt-2 space-y-2">
                            {categoryEndpoints.map(endpoint => (
                              <div
                                key={endpoint.id}
                                className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                                  selectedEndpoint?.id === endpoint.id
                                    ? 'border-primary bg-primary/5'
                                    : 'border-border hover:border-primary/50 hover:bg-accent/50'
                                }`}
                                onClick={() => setSelectedEndpoint(endpoint)}
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge className={`text-xs ${getMethodColor(endpoint.method)}`}>
                                    {endpoint.method}
                                  </Badge>
                                  <span className="font-medium text-sm">{endpoint.name}</span>
                                </div>
                                <p className="text-xs text-muted-foreground mb-1">
                                  {endpoint.path}
                                </p>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                  <div className="flex items-center gap-1">
                                    <Zap className="h-3 w-3" />
                                    <span>{endpoint.creditsRequired} créditos</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-2">
          {selectedEndpoint ? (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Badge className={getMethodColor(selectedEndpoint.method)}>
                    {selectedEndpoint.method}
                  </Badge>
                  <CardTitle className="text-xl">{selectedEndpoint.name}</CardTitle>
                </div>
                <CardDescription>{selectedEndpoint.description}</CardDescription>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Code className="h-4 w-4" />
                    <code className="bg-muted px-2 py-1 rounded text-xs">{selectedEndpoint.path}</code>
                  </div>
                  <div className="flex items-center gap-1">
                    <Zap className="h-4 w-4" />
                    <span>{selectedEndpoint.creditsRequired} créditos</span>
                  </div>
                  {selectedEndpoint.rateLimit && (
                    <div className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      <span>{selectedEndpoint.rateLimit.requests}/{selectedEndpoint.rateLimit.period}</span>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="w-full">
                  <div className="flex border-b">
                    <button
                      className={`px-4 py-2 border-b-2 transition-all duration-200 ease-out hover:bg-accent/20 ${
                        activeTab === 'details'
                          ? 'border-primary text-primary bg-primary/5'
                          : 'border-transparent text-muted-foreground'
                      }`}
                      onClick={() => setActiveTab('details')}
                    >
                      Detalhes
                    </button>
                    <button
                      className={`px-4 py-2 border-b-2 transition-all duration-200 ease-out hover:bg-accent/20 ${
                        activeTab === 'test'
                          ? 'border-primary text-primary bg-primary/5'
                          : 'border-transparent text-muted-foreground'
                      }`}
                      onClick={() => setActiveTab('test')}
                    >
                      Testar
                    </button>
                    <button
                      className={`px-4 py-2 border-b-2 transition-all duration-200 ease-out hover:bg-accent/20 ${
                        activeTab === 'examples'
                          ? 'border-primary text-primary bg-primary/5'
                          : 'border-transparent text-muted-foreground'
                      }`}
                      onClick={() => setActiveTab('examples')}
                    >
                      Exemplos
                    </button>
                    <button
                      className={`px-4 py-2 border-b-2 transition-all duration-200 ease-out hover:bg-accent/20 ${
                        activeTab === 'curl'
                          ? 'border-primary text-primary bg-primary/5'
                          : 'border-transparent text-muted-foreground'
                      }`}
                      onClick={() => setActiveTab('curl')}
                    >
                      cURL
                    </button>
                  </div>

                  <div className="mt-4 space-y-4">
                    {activeTab === 'details' && (
                      <>
                        {selectedEndpoint.parameters.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-3">{t('parameters')}</h4>
                            <div className="space-y-2">
                              {selectedEndpoint.parameters.map(param => (
                                <div key={param.name} className="border rounded p-3">
                                  <div className="flex items-center gap-2 mb-1">
                                    <code className="text-sm bg-muted px-2 py-1 rounded">
                                      {param.name}
                                    </code>
                                    <Badge variant={param.required ? 'destructive' : 'secondary'}>
                                      {param.required ? 'Obrigatório' : 'Opcional'}
                                    </Badge>
                                    <span className="text-xs text-muted-foreground">
                                      {param.type}
                                    </span>
                                  </div>
                                  <p className="text-sm text-muted-foreground mb-2">{param.description}</p>
                                  {param.example && (
                                    <div className="mt-2">
                                      <code className="text-xs bg-muted p-2 rounded block">
                                        {typeof param.example === 'string' 
                                          ? param.example 
                                          : JSON.stringify(param.example, null, 2)
                                        }
                                      </code>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedEndpoint.requestBody && (
                          <div>
                            <h4 className="font-medium mb-3">{t('requestBody')}</h4>
                            <div className="border rounded p-3">
                              <Badge variant="outline" className="mb-2">
                                {selectedEndpoint.requestBody.type}
                              </Badge>
                              <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                                {JSON.stringify(selectedEndpoint.requestBody.example, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}

                        <div>
                          <h4 className="font-medium mb-3">{t('responses')}</h4>
                          <div className="space-y-2">
                            {selectedEndpoint.responses.map(response => (
                              <div key={response.status} className="border rounded p-3">
                                <div className="flex items-center gap-2 mb-2">
                                  <Badge 
                                    variant={response.status < 300 ? 'default' : 'destructive'}
                                    className="font-mono"
                                  >
                                    {response.status}
                                  </Badge>
                                  <span className="text-sm font-medium">{response.description}</span>
                                </div>
                                <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                                  {JSON.stringify(response.example, null, 2)}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}

                    {activeTab === 'test' && (
                      <div className="space-y-4">
                        {selectedEndpoint.parameters.length > 0 && (
                          <div>
                            <h4 className="font-medium mb-3">{t('testParameters')}</h4>
                            <div className="space-y-3">
                              {selectedEndpoint.parameters.map(param => (
                                <div key={param.name}>
                                  <Label htmlFor={param.name}>
                                    {param.name}
                                    {param.required && <span className="text-red-500 ml-1">*</span>}
                                  </Label>
                                  <Input
                                    id={param.name}
                                    placeholder={param.example?.toString() || `Digite ${param.name}`}
                                    value={testParams[param.name] || ''}
                                    onChange={(e) => setTestParams(prev => ({
                                      ...prev,
                                      [param.name]: e.target.value
                                    }))}
                                  />
                                  <p className="text-xs text-muted-foreground mt-1">
                                    {param.description}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedEndpoint.requestBody && (
                          <div>
                            <Label htmlFor="testBody">Corpo da Requisição (JSON)</Label>
                            <Textarea
                              id="testBody"
                              placeholder={JSON.stringify(selectedEndpoint.requestBody.example, null, 2)}
                              value={testBody}
                              onChange={(e) => setTestBody(e.target.value)}
                              rows={8}
                              className="font-mono text-sm"
                            />
                          </div>
                        )}

                        <div className="flex items-center gap-2">
                          <Button 
                            onClick={handleTest}
                            disabled={testMutation.isPending}
                            className="flex items-center gap-2 min-h-[44px]"
                          >
                            {testMutation.isPending ? (
                              <div className="flex items-center gap-2">
                                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                                <span>Executando...</span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                <Play className="h-4 w-4" />
                                <span>{t('executeTest')}</span>
                              </div>
                            )}
                          </Button>
                        </div>

                        {testResult && (
                          <div className="border rounded p-4">
                            <div className="flex items-center gap-2 mb-3">
                              {testResult.success ? (
                                <CheckCircle className="h-5 w-5 text-green-500" />
                              ) : (
                                <XCircle className="h-5 w-5 text-red-500" />
                              )}
                              <span className="font-medium">
                                {testResult.success ? t('success') : t('error')}
                              </span>
                              <Badge variant={testResult.success ? 'default' : 'destructive'}>
                                {testResult.status}
                              </Badge>
                              <span className="text-sm text-muted-foreground">
                                {testResult.executionTime}ms
                              </span>
                            </div>

                            {testResult.error && (
                              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded">
                                <p className="text-sm text-red-700">{testResult.error}</p>
                              </div>
                            )}

                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <h5 className="font-medium">{t('response')}</h5>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => copyToClipboard(JSON.stringify(testResult.data, null, 2))}
                                >
                                  <Copy className="h-3 w-3" />
                                </Button>
                              </div>
                              <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-64">
                                {JSON.stringify(testResult.data, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {activeTab === 'examples' && (
                      <div className="space-y-4">
                        {selectedEndpoint.responses.map(response => (
                          <div key={response.status}>
                            <div className="flex items-center gap-2 mb-2">
                              <h4 className="font-medium">Resposta {response.status}</h4>
                              <Badge variant={response.status < 300 ? 'default' : 'destructive'}>
                                {response.description}
                              </Badge>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => copyToClipboard(JSON.stringify(response.example, null, 2))}
                              >
                                <Copy className="h-3 w-3" />
                              </Button>
                            </div>
                            <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                              {JSON.stringify(response.example, null, 2)}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )}

                    {activeTab === 'curl' && (
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <Terminal className="h-4 w-4" />
                          <h4 className="font-medium">{t('curlCommand')}</h4>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => copyToClipboard(generateCurlCommand(selectedEndpoint))}
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                        <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                          {generateCurlCommand(selectedEndpoint)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex items-center justify-center h-64">
                <div className="text-center">
                  <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">
                    Selecione um endpoint para ver a documentação
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}