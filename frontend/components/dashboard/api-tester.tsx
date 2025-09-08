'use client'

import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/lib/store/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Play, Copy, Download, History, Settings, Coins } from 'lucide-react'
import { useTranslations } from 'next-intl'

interface TestRequest {
  id: string
  method: string
  url: string
  headers: Record<string, string>
  body?: string
  timestamp: Date
  response?: {
    status: number
    statusText: string
    headers: Record<string, string>
    data: any
    executionTime: number
    creditsUsed?: number
  }
  error?: string
  creditsUsed?: number
}

interface ApiEndpoint {
  id: string
  name: string
  method: string
  path: string
  description: string
  parameters?: Array<{
    name: string
    type: string
    required: boolean
    description: string
    example?: any
  }>
  headers?: Record<string, string>
  body?: any
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']



export function ApiTester() {
  const t = useTranslations('apiTester')
  const { user, token } = useAuthStore()
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null)
  const [customRequest, setCustomRequest] = useState({
    method: 'GET',
    url: '',
    headers: '{}',
    body: ''
  })
  const [testHistory, setTestHistory] = useState<TestRequest[]>([])
  const [activeTab, setActiveTab] = useState<'quick' | 'custom' | 'history'>('quick')

  const COMMON_ENDPOINTS: ApiEndpoint[] = [
    {
      id: 'health-check',
      name: 'Health Check',
      method: 'GET',
      path: '/health',
      description: 'Check API health status',
      parameters: []
    },
    {
      id: 'enrich-company',
      name: t('enrichCompany'),
      method: 'POST',
      path: '/api/v1/enrich/company',
      description: t('enrichCompanyDescription'),
      parameters: [
        { name: 'domain', type: 'string', required: true, description: t('companyDomain'), example: 'example.com' },
        { name: 'include_contacts', type: 'boolean', required: false, description: t('includeContacts'), example: true }
      ],
      body: {
        domain: 'example.com',
        include_contacts: true
      }
    },
    {
      id: 'enrich-person',
      name: t('enrichPerson'),
      method: 'POST',
      path: '/api/v1/enrich/person',
      description: t('enrichPersonDescription'),
      parameters: [
        { name: 'email', type: 'string', required: true, description: t('personEmail'), example: 'john@example.com' },
        { name: 'linkedin_url', type: 'string', required: false, description: t('linkedinUrl'), example: 'https://linkedin.com/in/john' }
      ],
      body: {
        email: 'john@example.com',
        linkedin_url: 'https://linkedin.com/in/john'
      }
    },
    {
      id: 'search-companies',
      name: t('searchCompanies'),
      method: 'GET',
      path: '/api/v1/search/companies',
      description: t('searchCompaniesDescription'),
      parameters: [
        { name: 'query', type: 'string', required: true, description: t('searchTerm'), example: 'technology startup' },
        { name: 'location', type: 'string', required: false, description: t('location'), example: 'São Paulo, Brazil' },
        { name: 'size', type: 'string', required: false, description: t('companySize'), example: '1-50' },
        { name: 'limit', type: 'number', required: false, description: t('resultsLimit'), example: 10 }
      ]
    },
    {
      id: 'google-maps-scrape',
      name: t('googleMapsScraping'),
      method: 'POST',
      path: '/api/v1/scrapp/google-maps',
      description: t('googleMapsScrapingDescription'),
      parameters: [
        { name: 'url', type: 'string', required: true, description: t('googleMapsUrl'), example: 'https://maps.google.com/maps/place/McDonald\'s' },
        { name: 'use_hyperbrowser', type: 'boolean', required: false, description: t('useHyperbrowser'), example: true }
      ],
      body: {
        url: 'https://maps.google.com/maps/place/McDonald\'s',
        use_hyperbrowser: true
      }
    },
    {
      id: 'google-maps-search',
      name: t('googleMapsSearch'),
      method: 'POST',
      path: '/api/v1/scrapp/google-maps/search',
      description: t('googleMapsSearchDescription'),
      parameters: [
        { name: 'business_name', type: 'string', required: true, description: t('businessNameToSearch'), example: 'Starbucks' },
        { name: 'location', type: 'string', required: true, description: t('locationToSearch'), example: 'New York' },
        { name: 'use_hyperbrowser', type: 'boolean', required: false, description: t('useHyperbrowser'), example: true }
      ],
      body: {
        business_name: 'Starbucks',
        location: 'New York',
        use_hyperbrowser: true
      }
    },
    {
      id: 'whatsapp-scrape',
      name: t('whatsappScraping'),
      method: 'POST',
      path: '/api/v1/scrapp/whatsapp',
      description: t('whatsappScrapingDescription'),
      parameters: [
        { name: 'url', type: 'string', required: true, description: t('whatsappUrl'), example: 'https://wa.me/5511999999999' },
        { name: 'use_hyperbrowser', type: 'boolean', required: false, description: t('useHyperbrowser'), example: true }
      ],
      body: {
        url: 'https://wa.me/5511999999999',
        use_hyperbrowser: true
      }
    },
    {
      id: 'whatsapp-search',
      name: t('whatsappSearch'),
      method: 'POST',
      path: '/api/v1/scrapp/whatsapp/search',
      description: t('whatsappSearchDescription'),
      parameters: [
        { name: 'business_name', type: 'string', required: true, description: t('businessNameToSearch'), example: 'McDonald\'s' },
        { name: 'location', type: 'string', required: true, description: t('locationToSearch'), example: 'São Paulo' },
        { name: 'use_hyperbrowser', type: 'boolean', required: false, description: t('useHyperbrowser'), example: true }
      ],
      body: {
        business_name: 'McDonald\'s',
        location: 'São Paulo',
        use_hyperbrowser: true
      }
    }
  ]

  const addHeader = (key: string, value: string) => {
    const headers = JSON.parse(customRequest.headers) as Record<string, string>
    headers[key] = value
    setCustomRequest({ ...customRequest, headers: JSON.stringify(headers, null, 2) })
  }

  const addBodyField = (key: string, value: any) => {
    const body = JSON.parse(customRequest.body || '{}') as Record<string, any>
    body[key] = value
    setCustomRequest({ ...customRequest, body: JSON.stringify(body, null, 2) })
  }

  const testMutation = useMutation({
    mutationFn: async (request: Omit<TestRequest, 'id' | 'timestamp'>) => {
      const startTime = Date.now()
      console.log('Starting API test:', request)
      
      try {
        const parsedHeaders = typeof request.headers === 'string' ? 
          JSON.parse(request.headers) as Record<string, string> : request.headers
        
        const headers = {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
          ...parsedHeaders
        }

        // Ensure URL starts with /api if it doesn't have a full URL
        let url = request.url
        if (!url.startsWith('http') && !url.startsWith('/api')) {
          url = `/api${url.startsWith('/') ? '' : '/'}${url}`
        }
        
        const fullUrl = url.startsWith('http') ? url : `${process.env.NEXT_PUBLIC_API_URL}${url}`
        console.log('Request URL:', fullUrl)
        console.log('Request headers:', headers)
        console.log('Request body:', request.body)
        
        const fetchOptions: RequestInit = {
          method: request.method,
          headers
        }
        
        // Only add body for non-GET requests and if body exists
        if (request.method !== 'GET' && request.body && request.body.trim()) {
          fetchOptions.body = request.body
        }
        
        const response = await fetch(fullUrl, fetchOptions)
        
        console.log('Response status:', response.status)
        console.log('Response headers:', Object.fromEntries(response.headers.entries()))

        let data
        const contentType = response.headers.get('content-type')
        try {
          if (contentType && contentType.includes('application/json')) {
            data = await response.json()
          } else {
            data = await response.text()
          }
        } catch (e) {
          console.warn('Failed to parse response:', e)
          data = 'Failed to parse response'
        }
        
        const executionTime = Date.now() - startTime
        
        // Extract credits information from response headers
        const creditsUsed = response.headers.get('x-credits-used') ? 
          parseInt(response.headers.get('x-credits-used') || '0') : undefined

        return {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries()),
          data,
          executionTime,
          ...(creditsUsed !== undefined && { creditsUsed })
        }
      } catch (error) {
        console.error('API Test Error:', error)
        const errorMessage = error instanceof Error ? error.message : t('unknownError')
        throw new Error(`${t('requestFailed')}: ${errorMessage}`)
      }
    },
    onSuccess: (response, variables) => {
      console.log('API Test Success:', { response, variables })
      const testRequest: TestRequest = {
        id: Date.now().toString(),
        ...variables,
        timestamp: new Date(),
        response
      }
      setTestHistory(prev => [testRequest, ...prev.slice(0, 49)]) // Keep only last 50
      console.log(t('testExecutedSuccessfully'))
    },
    onError: (error, variables) => {
      const testRequest: TestRequest = {
        id: Date.now().toString(),
        ...variables,
        timestamp: new Date(),
        error: error.message
      }
      setTestHistory(prev => [testRequest, ...prev.slice(0, 49)])
      console.error(t('errorExecutingTest'))
    }
  })

  const handleQuickTest = (endpoint: ApiEndpoint) => {
    // Prevent multiple simultaneous requests
    if (testMutation.isPending) {
      return
    }

    const params = endpoint.parameters?.reduce((acc, param) => {
      if (param.example !== undefined) {
        acc[param.name] = param.example
      }
      return acc
    }, {} as Record<string, any>) || {}

    let url = endpoint.path
    if (endpoint.method === 'GET' && Object.keys(params).length > 0) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        searchParams.append(key, String(value))
      })
      url += `?${searchParams.toString()}`
    }

    testMutation.mutate({
      method: endpoint.method,
      url,
      headers: endpoint.headers || {},
      body: endpoint.method !== 'GET' ? JSON.stringify(endpoint.body || params) : ''
    })
  }

  const handleCustomTest = () => {
    // Prevent multiple simultaneous requests
    if (testMutation.isPending) {
      return
    }

    if (!customRequest.url.trim()) {
      alert(t('urlRequired'))
      return
    }

    // Validate JSON headers
    let parsedHeaders = {}
    try {
      const headersText = customRequest.headers.trim() || '{}'
      parsedHeaders = JSON.parse(headersText)
    } catch (error) {
      alert('Headers devem estar em formato JSON válido')
      return
    }

    // Validate JSON body for non-GET requests
    if (customRequest.method !== 'GET' && customRequest.body && customRequest.body.trim()) {
      try {
        JSON.parse(customRequest.body)
      } catch (error) {
        alert('Corpo da requisição deve estar em formato JSON válido')
        return
      }
    }

    testMutation.mutate({
      method: customRequest.method,
      url: customRequest.url.trim(),
      headers: parsedHeaders,
      body: customRequest.body?.trim() || ''
    })
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    console.log(t('copiedToClipboard'))
  }

  const exportHistory = () => {
    const dataStr = JSON.stringify(testHistory, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `api-test-history-${new Date().toISOString().split('T')[0]}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{t('apiTester')}</h2>
          <p className="text-muted-foreground">
            {t('apiTesterDescription')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {t('credits')}: {user?.creditsRemaining || 0}
          </Badge>
          <Button variant="outline" size="sm" onClick={exportHistory}>
            <Download className="h-4 w-4 mr-2" />
            {t('exportHistory')}
          </Button>
        </div>
      </div>

      <div>
        <div className="flex border-b">
          <button
            className={`px-4 py-2 font-medium transition-all duration-200 ease-out hover:bg-accent/20 ${activeTab === 'quick' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-primary'}`}
            onClick={() => setActiveTab('quick')}
          >
            {t('quickTest')}
          </button>
          <button
            className={`px-4 py-2 font-medium transition-all duration-200 ease-out hover:bg-accent/20 ${activeTab === 'custom' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-primary'}`}
            onClick={() => setActiveTab('custom')}
          >
            {t('customRequest')}
          </button>
          <button
            className={`px-4 py-2 font-medium transition-all duration-200 ease-out hover:bg-accent/20 ${activeTab === 'history' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-primary'}`}
            onClick={() => setActiveTab('history')}
          >
            {t('history')}
          </button>
        </div>

        {activeTab === 'quick' && (
          <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                {t('commonEndpoints')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4">
                {COMMON_ENDPOINTS.map((endpoint) => (
                  <div key={endpoint.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Badge variant={endpoint.method === 'GET' ? 'secondary' : 'default'}>
                          {endpoint.method}
                        </Badge>
                        <span className="font-medium">{endpoint.name}</span>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleQuickTest(endpoint)}
                        disabled={testMutation.isPending}
                        className="min-w-[80px]"
                      >
                        {testMutation.isPending ? (
                          <div className="flex items-center gap-2">
                            <div className="animate-spin h-3 w-3 border-2 border-current border-t-transparent rounded-full" />
                            {t('testing')}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Play className="h-3 w-3" />
                            {t('test')}
                          </div>
                        )}
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{endpoint.description}</p>
                    <code className="text-xs bg-muted px-2 py-1 rounded">{endpoint.path}</code>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          </div>
        )}

        {activeTab === 'custom' && (
          <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                {t('customRequest')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <Label htmlFor="method">{t('method')}</Label>
                  <Select
                    value={customRequest.method}
                    onValueChange={(value) => 
                      setCustomRequest(prev => ({ ...prev, method: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {HTTP_METHODS.map(method => (
                        <SelectItem key={method} value={method}>{method}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-3">
                  <Label htmlFor="url">{t('url')}</Label>
                  <Input
                    id="url"
                    placeholder={t('urlPlaceholder')}
                    value={customRequest.url}
                    onChange={(e) => setCustomRequest(prev => ({ ...prev, url: e.target.value }))}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="headers">{t('headersJson')}</Label>
                <Textarea
                  id="headers"
                  placeholder='{\n  "Content-Type": "application/json"\n}'
                  value={customRequest.headers}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCustomRequest(prev => ({ ...prev, headers: e.target.value }))}
                  rows={4}
                />
              </div>

              {customRequest.method !== 'GET' && (
                <div>
                  <Label htmlFor="body">{t('bodyJson')}</Label>
                  <Textarea
                    id="body"
                    className="min-h-[120px]"
                    placeholder='{\n  "key": "value"\n}'
                    value={customRequest.body}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCustomRequest(prev => ({ ...prev, body: e.target.value }))}
                    rows={6}
                  />
                </div>
              )}

              <Button
                onClick={handleCustomTest}
                disabled={testMutation.isPending || !customRequest.url}
                className="w-full min-h-[44px]"
              >
                {testMutation.isPending ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
                    {t('executing')}
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <Play className="h-4 w-4" />
                    {t('executeTest')}
                  </div>
                )}
              </Button>
            </CardContent>
          </Card>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                {t('testHistory')} ({testHistory.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {testHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>{t('noTestsExecuted')}</p>
                  <p className="text-sm">{t('executeTestsToSeeHistory')}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {testHistory.map((test) => (
                    <div key={test.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={test.method === 'GET' ? 'secondary' : 'default'}>
                            {test.method}
                          </Badge>
                          <code className="text-sm">{test.url}</code>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {test.timestamp.toLocaleString()}
                          </span>
                          {test.response && (
                            <Badge variant={test.response.status < 300 ? 'default' : 'destructive'}>
                              {test.response.status}
                            </Badge>
                          )}
                          {test.error && (
                            <Badge variant="destructive">{t('error')}</Badge>
                          )}
                          {(test.response?.creditsUsed || test.creditsUsed) && (
                            <Badge variant="outline" className="flex items-center gap-1">
                              <Coins className="h-3 w-3" />
                              {test.response?.creditsUsed || test.creditsUsed}
                            </Badge>
                          )}
                        </div>
                      </div>

                      {test.response && (
                        <div className="mt-3">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-4">
                              <span className="text-sm font-medium">{t('response')} ({test.response.executionTime}ms)</span>
                              {test.response.creditsUsed && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Coins className="h-3 w-3" />
                                  {t('credits')}: {test.response.creditsUsed}
                                </span>
                              )}
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => copyToClipboard(JSON.stringify(test.response?.data, null, 2))}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                          </div>
                          <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-32">
                            {JSON.stringify(test.response.data, null, 2)}
                          </pre>
                        </div>
                      )}

                      {test.error && (
                        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded">
                          <p className="text-sm text-red-800">{test.error}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
          </div>
        )}
      </div>
    </div>
  )
}