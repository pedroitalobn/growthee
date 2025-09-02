# Plano de Implementação - Otimização de Scraping EnrichStory

## Visão Geral

Este plano detalha a implementação das melhorias propostas para o sistema de scraping do EnrichStory, organizadas em fases incrementais para minimizar riscos e maximizar o ROI.

## Fase 1: Correções Críticas e Fundação (Semanas 1-2)

### Objetivos
- Corrigir bugs críticos identificados
- Estabelecer base sólida para melhorias futuras
- Implementar monitoramento básico

### Tarefas Prioritárias

#### 1.1 Correção do Método `_map_data_to_schema`
**Problema:** Método chamado mas não implementado
**Solução:**
```python
# api/services.py - Adicionar método ausente
def _map_data_to_schema(self, data: dict, schema: dict) -> dict:
    """
    Mapeia dados extraídos para o schema esperado
    """
    try:
        mapped_data = {}
        
        for field, field_config in schema.get('properties', {}).items():
            # Busca valor nos dados extraídos
            value = self._extract_field_value(data, field, field_config)
            
            if value is not None:
                mapped_data[field] = self._validate_field_type(value, field_config)
        
        return mapped_data
    except Exception as e:
        logger.error(f"Error mapping data to schema: {e}")
        return {}

def _extract_field_value(self, data: dict, field: str, config: dict):
    """Extrai valor do campo dos dados"""
    # Busca direta
    if field in data:
        return data[field]
    
    # Busca por aliases comuns
    aliases = {
        'company_name': ['name', 'title', 'company'],
        'website': ['url', 'website_url', 'site'],
        'employees': ['employee_count', 'size', 'team_size']
    }
    
    for alias in aliases.get(field, []):
        if alias in data:
            return data[alias]
    
    return None

def _validate_field_type(self, value, config: dict):
    """Valida e converte tipo do campo"""
    field_type = config.get('type', 'string')
    
    if field_type == 'integer':
        return int(value) if str(value).isdigit() else None
    elif field_type == 'number':
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    elif field_type == 'boolean':
        return str(value).lower() in ['true', '1', 'yes']
    else:
        return str(value).strip() if value else None
```

#### 1.2 Implementar Cache Redis Básico
**Arquivo:** `api/cache_service.py`
```python
import redis
import json
import hashlib
from datetime import timedelta
from typing import Optional, Any
from pydantic import BaseModel

class CacheConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    default_ttl: int = 3600  # 1 hora

class ScrapingCache:
    def __init__(self, config: CacheConfig):
        self.redis = redis.Redis(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.password,
            decode_responses=True
        )
        self.default_ttl = config.default_ttl
    
    def _generate_key(self, url: str, cache_type: str = "response") -> str:
        """Gera chave única para cache"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"scraping:{cache_type}:{url_hash}"
    
    def get(self, url: str, cache_type: str = "response") -> Optional[dict]:
        """Recupera dados do cache"""
        try:
            key = self._generate_key(url, cache_type)
            cached_data = self.redis.get(key)
            return json.loads(cached_data) if cached_data else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, url: str, data: Any, ttl: Optional[int] = None, cache_type: str = "response") -> bool:
        """Armazena dados no cache"""
        try:
            key = self._generate_key(url, cache_type)
            ttl = ttl or self.default_ttl
            
            self.redis.setex(
                key,
                timedelta(seconds=ttl),
                json.dumps(data, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, url: str, cache_type: str = "response") -> bool:
        """Remove dados do cache"""
        try:
            key = self._generate_key(url, cache_type)
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def clear_domain(self, domain: str) -> int:
        """Limpa cache de um domínio específico"""
        pattern = f"scraping:*:{domain}:*"
        keys = self.redis.keys(pattern)
        return self.redis.delete(*keys) if keys else 0
```

#### 1.3 Configurar Monitoramento Básico
**Arquivo:** `api/monitoring.py`
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
from functools import wraps

# Métricas Prometheus
scraping_requests_total = Counter(
    'scraping_requests_total',
    'Total de requests de scraping',
    ['domain', 'method', 'status']
)

scraping_duration_seconds = Histogram(
    'scraping_duration_seconds',
    'Duração do scraping em segundos',
    ['domain', 'method']
)

active_scrapers = Gauge(
    'active_scrapers_count',
    'Número de scrapers ativos'
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total de cache hits',
    ['cache_type']
)

def monitor_scraping(domain: str, method: str):
    """Decorator para monitorar operações de scraping"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            active_scrapers.inc()
            
            try:
                result = await func(*args, **kwargs)
                scraping_requests_total.labels(
                    domain=domain, 
                    method=method, 
                    status='success'
                ).inc()
                return result
            except Exception as e:
                scraping_requests_total.labels(
                    domain=domain, 
                    method=method, 
                    status='error'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                scraping_duration_seconds.labels(
                    domain=domain, 
                    method=method
                ).observe(duration)
                active_scrapers.dec()
        
        return wrapper
    return decorator

# Endpoint para métricas
@app.get("/metrics")
async def get_metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )
```

### Entregáveis Fase 1
- [ ] Método `_map_data_to_schema` implementado e testado
- [ ] Cache Redis configurado e funcionando
- [ ] Métricas Prometheus coletando dados
- [ ] Testes unitários para novas funcionalidades
- [ ] Documentação atualizada

## Fase 2: Sistema Anti-Bot (Semanas 3-4)

### Objetivos
- Implementar rotação de proxies
- Adicionar browser fingerprinting
- Configurar retry logic avançado

### 2.1 Integração com Botasaurus
**Arquivo:** `api/scraping/botasaurus_scraper.py`
```python
from botasaurus import *
from typing import List, Dict, Optional
import random

class EnhancedBotasaurusScraper:
    def __init__(self, proxy_list: List[str] = None):
        self.proxy_list = proxy_list or []
        self.user_agents = self._load_user_agents()
    
    def _load_user_agents(self) -> List[str]:
        """Carrega lista de user agents"""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            # ... mais user agents
        ]
    
    @browser(
        headless=True,
        block_images=True,
        block_resources=['stylesheet', 'font'],
        wait_for_complete_page_load=True
    )
    def scrape_company_data(self, driver, data: Dict) -> Dict:
        """Scraping com anti-bot automático"""
        try:
            # Configurar proxy aleatório
            if self.proxy_list:
                proxy = random.choice(self.proxy_list)
                driver.set_proxy(proxy)
            
            # User agent aleatório
            user_agent = random.choice(self.user_agents)
            driver.set_user_agent(user_agent)
            
            # Navegar para URL
            driver.get(data['url'])
            
            # Aguardar carregamento
            driver.wait_for_element('.company-info', timeout=10)
            
            # Extrair dados
            company_data = {
                'name': driver.get_text('.company-name', default=''),
                'description': driver.get_text('.company-description', default=''),
                'website': driver.get_attribute('.website-link', 'href', default=''),
                'employees': self._extract_employee_count(driver),
                'industry': driver.get_text('.industry', default='')
            }
            
            return company_data
            
        except Exception as e:
            logger.error(f"Botasaurus scraping error: {e}")
            return {'error': str(e)}
    
    def _extract_employee_count(self, driver) -> Optional[int]:
        """Extrai número de funcionários"""
        try:
            text = driver.get_text('.employee-count', default='')
            # Regex para extrair números
            import re
            numbers = re.findall(r'\d+', text.replace(',', ''))
            return int(numbers[0]) if numbers else None
        except:
            return None
```

### 2.2 Sistema de Proxy Rotation
**Arquivo:** `api/scraping/proxy_manager.py`
```python
import random
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ProxyInfo:
    url: str
    type: str  # 'residential', 'datacenter'
    country: str
    success_rate: float = 1.0
    last_used: Optional[datetime] = None
    failures: int = 0
    is_active: bool = True

class ProxyManager:
    def __init__(self, proxies: List[Dict]):
        self.proxies = [ProxyInfo(**proxy) for proxy in proxies]
        self.max_failures = 3
        self.cooldown_minutes = 10
    
    def get_best_proxy(self, country: str = None, proxy_type: str = None) -> Optional[ProxyInfo]:
        """Seleciona o melhor proxy disponível"""
        available_proxies = self._filter_available_proxies(country, proxy_type)
        
        if not available_proxies:
            return None
        
        # Ordena por success rate e último uso
        available_proxies.sort(
            key=lambda p: (p.success_rate, -(p.last_used or datetime.min).timestamp()),
            reverse=True
        )
        
        return available_proxies[0]
    
    def _filter_available_proxies(self, country: str = None, proxy_type: str = None) -> List[ProxyInfo]:
        """Filtra proxies disponíveis"""
        now = datetime.now()
        available = []
        
        for proxy in self.proxies:
            # Verifica se está ativo
            if not proxy.is_active:
                continue
            
            # Verifica cooldown
            if proxy.last_used:
                time_since_use = now - proxy.last_used
                if time_since_use < timedelta(minutes=self.cooldown_minutes):
                    continue
            
            # Filtra por país
            if country and proxy.country != country:
                continue
            
            # Filtra por tipo
            if proxy_type and proxy.type != proxy_type:
                continue
            
            available.append(proxy)
        
        return available
    
    def mark_success(self, proxy: ProxyInfo):
        """Marca proxy como sucesso"""
        proxy.last_used = datetime.now()
        proxy.failures = 0
        # Aumenta success rate gradualmente
        proxy.success_rate = min(1.0, proxy.success_rate + 0.01)
    
    def mark_failure(self, proxy: ProxyInfo):
        """Marca proxy como falha"""
        proxy.failures += 1
        proxy.success_rate = max(0.1, proxy.success_rate - 0.1)
        
        if proxy.failures >= self.max_failures:
            proxy.is_active = False
            logger.warning(f"Proxy {proxy.url} desativado por muitas falhas")
    
    def test_proxy(self, proxy: ProxyInfo) -> bool:
        """Testa se proxy está funcionando"""
        try:
            response = requests.get(
                'http://httpbin.org/ip',
                proxies={'http': proxy.url, 'https': proxy.url},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def health_check(self):
        """Verifica saúde de todos os proxies"""
        for proxy in self.proxies:
            if not proxy.is_active:
                continue
            
            if self.test_proxy(proxy):
                proxy.is_active = True
                proxy.failures = 0
            else:
                self.mark_failure(proxy)
```

### Entregáveis Fase 2
- [ ] Botasaurus integrado e configurado
- [ ] Sistema de proxy rotation funcionando
- [ ] Browser fingerprinting implementado
- [ ] Retry logic avançado
- [ ] Testes de anti-bot em sites reais

## Fase 3: Otimização de Performance (Semanas 5-6)

### Objetivos
- Implementar processamento assíncrono com Celery
- Otimizar queries de banco de dados
- Adicionar circuit breakers

### 3.1 Celery Task Queue
**Arquivo:** `api/tasks/scraping_tasks.py`
```python
from celery import Celery
from celery.exceptions import Retry
from typing import Dict, List
import asyncio

# Configuração Celery
celery_app = Celery(
    'scraping_tasks',
    broker='redis://localhost:6379/1',
    backend='redis://localhost:6379/1'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'scraping_tasks.scrape_company': {'queue': 'company_scraping'},
        'scraping_tasks.scrape_linkedin': {'queue': 'linkedin_scraping'},
        'scraping_tasks.bulk_scrape': {'queue': 'bulk_processing'}
    }
)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_company_task(self, company_data: Dict) -> Dict:
    """Task assíncrona para scraping de empresa"""
    try:
        # Importar serviços necessários
        from api.services import CompanyEnrichmentService
        
        service = CompanyEnrichmentService()
        result = asyncio.run(service.enrich_company(company_data))
        
        return {
            'status': 'success',
            'data': result,
            'company_id': company_data.get('id')
        }
        
    except Exception as exc:
        logger.error(f"Scraping task failed: {exc}")
        
        # Retry com backoff exponencial
        raise self.retry(
            exc=exc,
            countdown=60 * (2 ** self.request.retries)
        )

@celery_app.task(bind=True)
def bulk_scrape_companies(self, company_list: List[Dict]) -> Dict:
    """Task para scraping em lote"""
    results = {
        'success': [],
        'failed': [],
        'total': len(company_list)
    }
    
    # Processa em chunks para evitar sobrecarga
    chunk_size = 10
    for i in range(0, len(company_list), chunk_size):
        chunk = company_list[i:i + chunk_size]
        
        # Cria subtasks
        job = group(scrape_company_task.s(company) for company in chunk)
        result = job.apply_async()
        
        # Coleta resultados
        for task_result in result.get():
            if task_result['status'] == 'success':
                results['success'].append(task_result)
            else:
                results['failed'].append(task_result)
    
    return results

@celery_app.task
def cleanup_old_cache():
    """Task de limpeza de cache antigo"""
    from api.cache_service import ScrapingCache
    
    cache = ScrapingCache()
    # Implementar lógica de limpeza
    cleaned_keys = cache.cleanup_expired()
    
    logger.info(f"Cleaned {cleaned_keys} expired cache entries")
    return cleaned_keys
```

### 3.2 Circuit Breaker Pattern
**Arquivo:** `api/utils/circuit_breaker.py`
```python
from pybreaker import CircuitBreaker
from functools import wraps
import logging

# Configurações de circuit breakers por serviço
SCRAPING_BREAKER = CircuitBreaker(
    fail_max=5,
    reset_timeout=300,  # 5 minutos
    exclude=[TimeoutError, ConnectionError]
)

LLM_BREAKER = CircuitBreaker(
    fail_max=3,
    reset_timeout=600,  # 10 minutos
    exclude=[]
)

PROXY_BREAKER = CircuitBreaker(
    fail_max=10,
    reset_timeout=180,  # 3 minutos
    exclude=[]
)

def with_circuit_breaker(breaker: CircuitBreaker):
    """Decorator para aplicar circuit breaker"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await breaker(func)(*args, **kwargs)
            except Exception as e:
                logger.error(f"Circuit breaker triggered for {func.__name__}: {e}")
                raise
        return wrapper
    return decorator

# Exemplo de uso
@with_circuit_breaker(SCRAPING_BREAKER)
async def scrape_with_protection(url: str) -> Dict:
    """Scraping protegido por circuit breaker"""
    # Lógica de scraping
    pass
```

### Entregáveis Fase 3
- [ ] Celery configurado e funcionando
- [ ] Tasks assíncronas implementadas
- [ ] Circuit breakers em operações críticas
- [ ] Otimizações de banco de dados
- [ ] Monitoramento de performance

## Fase 4: Otimização de AI (Semanas 7-8)

### Objetivos
- Reduzir custos de LLM em 70%+
- Implementar fallback híbrido
- Otimizar prompts

### 4.1 Integração Ollama (LLM Local)
**Arquivo:** `api/ai/local_llm.py`
```python
import ollama
from typing import Dict, Optional
import json

class LocalLLMService:
    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model
        self._ensure_model_available()
    
    def _ensure_model_available(self):
        """Garante que o modelo está disponível"""
        try:
            models = ollama.list()['models']
            if not any(m['name'] == self.model for m in models):
                logger.info(f"Downloading model {self.model}...")
                ollama.pull(self.model)
        except Exception as e:
            logger.error(f"Error setting up local LLM: {e}")
    
    def extract_structured_data(self, content: str, schema: Dict) -> Optional[Dict]:
        """Extrai dados estruturados usando LLM local"""
        try:
            prompt = self._build_extraction_prompt(content, schema)
            
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }],
                options={
                    'temperature': 0.1,
                    'top_p': 0.9
                }
            )
            
            # Parse JSON response
            result_text = response['message']['content']
            return self._parse_json_response(result_text)
            
        except Exception as e:
            logger.error(f"Local LLM extraction error: {e}")
            return None
    
    def _build_extraction_prompt(self, content: str, schema: Dict) -> str:
        """Constrói prompt otimizado para extração"""
        schema_fields = list(schema.get('properties', {}).keys())
        
        prompt = f"""
Extract the following information from the text below and return ONLY a valid JSON object:

Required fields: {', '.join(schema_fields)}

Text to analyze:
{content[:2000]}  # Limita tamanho para performance

Return format: {{
    "field1": "value1",
    "field2": "value2"
}}

JSON:"""
        
        return prompt
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse resposta JSON do LLM"""
        try:
            # Remove markdown formatting
            response = response.strip()
            if response.startswith('```'):
                response = response.split('\n', 1)[1]
            if response.endswith('```'):
                response = response.rsplit('\n', 1)[0]
            
            return json.loads(response)
        except json.JSONDecodeError:
            # Tenta extrair JSON com regex
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return None
```

### 4.2 Sistema Híbrido de Extração
**Arquivo:** `api/ai/hybrid_extractor.py`
```python
from typing import Dict, Optional, List
from enum import Enum

class ExtractionMethod(Enum):
    CSS_SELECTOR = "css"
    XPATH = "xpath"
    REGEX = "regex"
    LOCAL_LLM = "local_llm"
    CLOUD_LLM = "cloud_llm"

class HybridExtractor:
    def __init__(self):
        self.local_llm = LocalLLMService()
        self.extraction_rules = self._load_extraction_rules()
    
    def _load_extraction_rules(self) -> Dict:
        """Carrega regras de extração por domínio"""
        return {
            'linkedin.com': {
                'company_name': {
                    'method': ExtractionMethod.CSS_SELECTOR,
                    'selector': 'h1.org-top-card-summary__title'
                },
                'employees': {
                    'method': ExtractionMethod.REGEX,
                    'pattern': r'(\d+[,\d]*) employees'
                },
                'description': {
                    'method': ExtractionMethod.CSS_SELECTOR,
                    'selector': '.org-top-card-summary__tagline'
                }
            },
            'default': {
                'fallback_method': ExtractionMethod.LOCAL_LLM
            }
        }
    
    async def extract_data(self, url: str, content: str, schema: Dict) -> Dict:
        """Extração híbrida inteligente"""
        domain = self._extract_domain(url)
        rules = self.extraction_rules.get(domain, self.extraction_rules['default'])
        
        extracted_data = {}
        
        # Tenta extração tradicional primeiro
        for field, field_schema in schema.get('properties', {}).items():
            if field in rules:
                rule = rules[field]
                value = await self._extract_with_rule(content, rule)
                if value:
                    extracted_data[field] = value
        
        # Se dados insuficientes, usa LLM local
        if len(extracted_data) < len(schema.get('properties', {})) * 0.7:
            llm_data = self.local_llm.extract_structured_data(content, schema)
            if llm_data:
                # Merge dados, priorizando extração tradicional
                for key, value in llm_data.items():
                    if key not in extracted_data and value:
                        extracted_data[key] = value
        
        # Fallback para LLM cloud se ainda insuficiente
        if len(extracted_data) < len(schema.get('properties', {})) * 0.5:
            cloud_data = await self._extract_with_cloud_llm(content, schema)
            if cloud_data:
                for key, value in cloud_data.items():
                    if key not in extracted_data and value:
                        extracted_data[key] = value
        
        return extracted_data
    
    async def _extract_with_rule(self, content: str, rule: Dict) -> Optional[str]:
        """Extrai dados usando regra específica"""
        method = rule['method']
        
        if method == ExtractionMethod.CSS_SELECTOR:
            return self._extract_with_css(content, rule['selector'])
        elif method == ExtractionMethod.REGEX:
            return self._extract_with_regex(content, rule['pattern'])
        # ... outros métodos
        
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extrai domínio da URL"""
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower()
```

### Entregáveis Fase 4
- [ ] Ollama configurado e funcionando
- [ ] Sistema híbrido implementado
- [ ] Redução de custos de LLM validada
- [ ] Prompts otimizados
- [ ] Testes de qualidade de dados

## Fase 5: Monitoramento Avançado (Semanas 9-10)

### Objetivos
- Dashboard Grafana completo
- Alertas automáticos
- Performance tuning final

### 5.1 Dashboard Grafana
**Arquivo:** `monitoring/grafana-dashboard.json`
```json
{
  "dashboard": {
    "title": "EnrichStory Scraping Metrics",
    "panels": [
      {
        "title": "Scraping Success Rate",
        "type": "stat",
        "targets": [{
          "expr": "rate(scraping_requests_total{status='success'}[5m]) / rate(scraping_requests_total[5m]) * 100"
        }]
      },
      {
        "title": "Response Time by Domain",
        "type": "graph",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(scraping_duration_seconds_bucket[5m]))"
        }]
      },
      {
        "title": "Cache Hit Rate",
        "type": "stat",
        "targets": [{
          "expr": "rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) * 100"
        }]
      },
      {
        "title": "Active Proxies",
        "type": "stat",
        "targets": [{
          "expr": "active_proxies_count"
        }]
      }
    ]
  }
}
```

### 5.2 Sistema de Alertas
**Arquivo:** `monitoring/alerts.yml`
```yaml
groups:
  - name: scraping_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(scraping_requests_total{status="error"}[5m]) / rate(scraping_requests_total[5m]) > 0.2
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate in scraping"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      - alert: SlowScraping
        expr: histogram_quantile(0.95, rate(scraping_duration_seconds_bucket[5m])) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow scraping detected"
          description: "95th percentile latency is {{ $value }}s"
      
      - alert: LowCacheHitRate
        expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.5
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }}"
```

### Entregáveis Fase 5
- [ ] Dashboard Grafana configurado
- [ ] Alertas automáticos funcionando
- [ ] Documentação completa
- [ ] Treinamento da equipe
- [ ] Performance tuning final

## Cronograma Resumido

| Fase | Duração | Principais Entregas | Impacto Esperado |
|------|---------|-------------------|------------------|
| 1 | 2 semanas | Correções críticas, cache, monitoramento | Estabilidade +50% |
| 2 | 2 semanas | Anti-bot, proxies, fingerprinting | Success rate +40% |
| 3 | 2 semanas | Celery, circuit breakers, otimizações | Performance +300% |
| 4 | 2 semanas | LLM local, extração híbrida | Custos -70% |
| 5 | 2 semanas | Dashboard, alertas, tuning | Observabilidade 100% |

## Recursos Necessários

### Infraestrutura
- **Redis Cluster**: Cache distribuído
- **Celery Workers**: 4-6 workers
- **Proxy Pool**: 50-100 proxies premium
- **Monitoring Stack**: Prometheus + Grafana

### Equipe
- **1 Senior Developer**: Implementação principal
- **1 DevOps Engineer**: Infraestrutura e monitoramento
- **1 QA Engineer**: Testes e validação

### Orçamento Estimado
- **Infraestrutura**: $500-800/mês
- **Proxies Premium**: $300-500/mês
- **Ferramentas**: $200-300/mês
- **Total**: $1000-1600/mês

## Métricas de Sucesso

### Performance
- [ ] Throughput: 3-5x maior
- [ ] Latência: 50-70% menor
- [ ] Success rate: 95%+

### Custos
- [ ] LLM costs: 70% redução
- [ ] Infrastructure ROI: 300%+
- [ ] Maintenance: 50% menos tempo

### Confiabilidade
- [ ] Uptime: 99.5%+
- [ ] Error recovery: Automático
- [ ] Monitoring: Real-time

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|----------|
| Bloqueio de proxies | Alta | Médio | Pool diversificado, rotação |
| Falha de LLM local | Média | Baixo | Fallback para cloud |
| Sobrecarga de sistema | Baixa | Alto | Circuit breakers, monitoring |
| Mudanças em sites | Alta | Médio | Extração híbrida, alertas |

---

**Próximo Passo:** Aprovação do plano e início da Fase 1