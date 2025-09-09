"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Activity, 
  DollarSign, 
  Zap, 
  TrendingUp, 
  AlertTriangle, 
  RefreshCw,
  Download,
  Trash2,
  Eye,
  Filter
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface APIServiceStats {
  service_name: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_response_time_ms: number;
  last_request_timestamp: string | null;
  daily_requests: number;
  monthly_requests: number;
}

interface APIUsageResponse {
  services: APIServiceStats[];
  total_requests_today: number;
  total_cost_today: number;
  total_tokens_today: number;
  most_used_service: string | null;
  cost_breakdown: Record<string, number>;
  request_trends: Record<string, any>;
}

interface APIService {
  name: string;
  display_name: string;
  category: string;
}

interface APILog {
  timestamp: string;
  service_name: string;
  endpoint: string;
  method: string;
  response_status: number;
  response_time_ms: number;
  tokens_used?: number;
  cost_usd?: number;
  user_id?: string;
  error_message?: string;
}

export function APIUsageDashboard() {
  const [selectedDays, setSelectedDays] = useState(7);
  const [selectedService, setSelectedService] = useState<string>('all');
  const [selectedLogService, setSelectedLogService] = useState<string>('all');
  const [selectedLogStatus, setSelectedLogStatus] = useState<string>('all');
  const queryClient = useQueryClient();

  // Fetch API usage statistics
  const { data: usageData, isLoading: usageLoading, refetch: refetchUsage } = useQuery({
    queryKey: ['api-usage-stats', selectedDays, selectedService],
    queryFn: async () => {
      const params = new URLSearchParams({
        days: selectedDays.toString()
      });
      if (selectedService !== 'all') {
        params.append('service_filter', selectedService);
      }
      const response = await adminApi.get(`/api-usage/stats?${params}`);
      return response.data as APIUsageResponse;
    },
    refetchInterval: 30000 // Refresh every 30 seconds
  });

  // Fetch available services
  const { data: servicesData } = useQuery({
    queryKey: ['api-services'],
    queryFn: async () => {
      const response = await adminApi.get('/api-usage/services');
      return response.data.services as APIService[];
    }
  });

  // Fetch API logs
  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery({
    queryKey: ['api-usage-logs', selectedLogService, selectedLogStatus],
    queryFn: async () => {
      const params = new URLSearchParams({
        limit: '100'
      });
      if (selectedLogService !== 'all') {
        params.append('service_filter', selectedLogService);
      }
      if (selectedLogStatus !== 'all') {
        params.append('status_filter', selectedLogStatus);
      }
      const response = await adminApi.get(`/api-usage/logs?${params}`);
      return response.data;
    },
    refetchInterval: 10000 // Refresh every 10 seconds
  });

  // Clear logs mutation
  const clearLogsMutation = useMutation({
    mutationFn: async (days: number) => {
      const response = await adminApi.delete(`/api-usage/logs/clear?older_than_days=${days}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-usage-logs'] });
      queryClient.invalidateQueries({ queryKey: ['api-usage-stats'] });
    }
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR').format(value);
  };

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-600';
    if (status >= 400 && status < 500) return 'text-yellow-600';
    if (status >= 500) return 'text-red-600';
    return 'text-gray-600';
  };

  const getServiceCategoryColor = (category: string) => {
    switch (category) {
      case 'AI/LLM': return 'bg-purple-100 text-purple-800';
      case 'Search': return 'bg-blue-100 text-blue-800';
      case 'Web Scraping': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (usageLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin" />
        <span className="ml-2">Carregando estatísticas...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Monitoramento de APIs</h2>
          <p className="text-muted-foreground">
            Acompanhe o uso e custos de serviços externos
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Select value={selectedDays.toString()} onValueChange={(value) => setSelectedDays(parseInt(value))}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Hoje</SelectItem>
              <SelectItem value="7">7 dias</SelectItem>
              <SelectItem value="30">30 dias</SelectItem>
              <SelectItem value="90">90 dias</SelectItem>
            </SelectContent>
          </Select>
          <Select value={selectedService} onValueChange={setSelectedService}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Todos os serviços" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os serviços</SelectItem>
              {servicesData?.map((service) => (
                <SelectItem key={service.name} value={service.name}>
                  {service.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => refetchUsage()} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Requests Hoje</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(usageData?.total_requests_today || 0)}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Custo Hoje</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(usageData?.total_cost_today || 0)}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Tokens Hoje</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatNumber(usageData?.total_tokens_today || 0)}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Serviço Mais Usado</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-medium">
              {usageData?.most_used_service ? (
                servicesData?.find(s => s.name === usageData.most_used_service)?.display_name || usageData.most_used_service
              ) : 'N/A'}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="services" className="space-y-4">
        <TabsList>
          <TabsTrigger value="services">Serviços</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="costs">Custos</TabsTrigger>
        </TabsList>

        <TabsContent value="services" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Estatísticas por Serviço</CardTitle>
              <CardDescription>
                Desempenho e uso de cada serviço externo
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Serviço</TableHead>
                    <TableHead>Categoria</TableHead>
                    <TableHead>Requests</TableHead>
                    <TableHead>Sucesso</TableHead>
                    <TableHead>Falhas</TableHead>
                    <TableHead>Tokens</TableHead>
                    <TableHead>Custo</TableHead>
                    <TableHead>Tempo Médio</TableHead>
                    <TableHead>Último Uso</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {usageData?.services?.map((service) => {
                    const serviceInfo = servicesData?.find(s => s.name === service.service_name);
                    const successRate = service.total_requests > 0 
                      ? (service.successful_requests / service.total_requests) * 100 
                      : 0;
                    
                    return (
                      <TableRow key={service.service_name}>
                        <TableCell className="font-medium">
                          {serviceInfo?.display_name || service.service_name}
                        </TableCell>
                        <TableCell>
                          <Badge className={getServiceCategoryColor(serviceInfo?.category || 'Other')}>
                            {serviceInfo?.category || 'Other'}
                          </Badge>
                        </TableCell>
                        <TableCell>{formatNumber(service.total_requests)}</TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <span>{formatNumber(service.successful_requests)}</span>
                            <Progress value={successRate} className="w-16 h-2" />
                            <span className="text-xs text-muted-foreground">
                              {successRate.toFixed(1)}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-red-600">
                          {formatNumber(service.failed_requests)}
                        </TableCell>
                        <TableCell>{formatNumber(service.total_tokens)}</TableCell>
                        <TableCell>{formatCurrency(service.total_cost_usd)}</TableCell>
                        <TableCell>
                          {service.avg_response_time_ms > 0 
                            ? `${service.avg_response_time_ms.toFixed(0)}ms`
                            : 'N/A'
                          }
                        </TableCell>
                        <TableCell>
                          {service.last_request_timestamp 
                            ? formatDistanceToNow(new Date(service.last_request_timestamp), {
                                addSuffix: true,
                                locale: ptBR
                              })
                            : 'Nunca'
                          }
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Logs de Requisições</CardTitle>
                  <CardDescription>
                    Histórico detalhado de chamadas para APIs externas
                  </CardDescription>
                </div>
                <div className="flex items-center space-x-2">
                  <Select value={selectedLogService} onValueChange={setSelectedLogService}>
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      {servicesData?.map((service) => (
                        <SelectItem key={service.name} value={service.name}>
                          {service.display_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={selectedLogStatus} onValueChange={setSelectedLogStatus}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos</SelectItem>
                      <SelectItem value="success">Sucesso</SelectItem>
                      <SelectItem value="error">Erro</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button onClick={() => refetchLogs()} variant="outline" size="sm">
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                  <Button 
                    onClick={() => clearLogsMutation.mutate(30)} 
                    variant="outline" 
                    size="sm"
                    disabled={clearLogsMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {logsLoading ? (
                <div className="flex items-center justify-center h-32">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Serviço</TableHead>
                      <TableHead>Endpoint</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Tempo</TableHead>
                      <TableHead>Tokens</TableHead>
                      <TableHead>Custo</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logsData?.logs?.map((log: APILog, index: number) => (
                      <TableRow key={index}>
                        <TableCell className="text-xs">
                          {new Date(log.timestamp).toLocaleString('pt-BR')}
                        </TableCell>
                        <TableCell>
                          <Badge className={getServiceCategoryColor(
                            servicesData?.find(s => s.name === log.service_name)?.category || 'Other'
                          )}>
                            {servicesData?.find(s => s.name === log.service_name)?.display_name || log.service_name}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs font-mono">
                          {log.method} {log.endpoint}
                        </TableCell>
                        <TableCell>
                          <span className={getStatusColor(log.response_status)}>
                            {log.response_status}
                          </span>
                        </TableCell>
                        <TableCell>{log.response_time_ms}ms</TableCell>
                        <TableCell>{log.tokens_used ? formatNumber(log.tokens_used) : '-'}</TableCell>
                        <TableCell>{log.cost_usd ? formatCurrency(log.cost_usd) : '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="costs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Breakdown de Custos</CardTitle>
              <CardDescription>
                Distribuição de custos por serviço
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(usageData?.cost_breakdown || {}).map(([service, cost]) => {
                  const serviceInfo = servicesData?.find(s => s.name === service);
                  const totalCost = Object.values(usageData?.cost_breakdown || {}).reduce((a, b) => a + b, 0);
                  const percentage = totalCost > 0 ? (cost / totalCost) * 100 : 0;
                  
                  return (
                    <div key={service} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <Badge className={getServiceCategoryColor(serviceInfo?.category || 'Other')}>
                          {serviceInfo?.display_name || service}
                        </Badge>
                        <Progress value={percentage} className="w-32" />
                        <span className="text-sm text-muted-foreground">
                          {percentage.toFixed(1)}%
                        </span>
                      </div>
                      <div className="font-medium">
                        {formatCurrency(cost)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}