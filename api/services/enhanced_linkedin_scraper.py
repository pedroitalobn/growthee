import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dataclasses import dataclass
from ..log_service import LogService
from .brave_search_service import BraveSearchService

@dataclass
class LinkedInExtractionResult:
    """Resultado estruturado da extração do LinkedIn"""
    company_name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    employee_count: Optional[int] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None
    specialties: Optional[List[str]] = None
    follower_count: Optional[int] = None
    
    # Enhanced location fields
    country: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None
    
    # Enhanced company data
    company_history: Optional[str] = None
    employee_count_range: Optional[str] = None
    employee_count_exact: Optional[int] = None
    
    confidence_score: float = 0.0
    extraction_methods: List[str] = None

class EnhancedLinkedInScraper:
    """Scraper LinkedIn aprimorado com múltiplas estratégias de extração"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        self.brave_search = BraveSearchService(log_service)
        
        # Padrões regex aprimorados para extração de dados
        self.regex_patterns = {
            'company_name': [
                r'<h1[^>]*>([^<]+)</h1>',
                r'"name"\s*:\s*"([^"]+)"',
                r'<title>([^|]+)\s*\|\s*LinkedIn</title>',
                r'og:title"\s*content="([^"]+)"'
            ],
            'description': [
                r'"description"\s*:\s*"([^"]+)"',
                r'<meta\s+name="description"\s+content="([^"]+)"',
                r'<p[^>]*class="[^"]*description[^"]*"[^>]*>([^<]+)</p>'
            ],
            'industry': [
                r'Industry[^>]*>\s*([^<]+)',
                r'"industry"\s*:\s*"([^"]+)"',
                r'<dd[^>]*>([^<]*(?:Technology|Finance|Healthcare|Manufacturing|Retail|Education|Consulting)[^<]*)</dd>'
            ],
            'employee_count': [
                r'([0-9,]+)\s*employees?',
                r'([0-9,]+)-([0-9,]+)\s*employees?',
                r'"employeeCountRange"\s*:\s*"([^"]+)"',
                r'([0-9,]+)\s*(?:to|-)\s*([0-9,]+)\s*employees?',
                r'Size\s*[:\-]?\s*([0-9,]+(?:\s*[-–]\s*[0-9,]+)?)\s*employees?',
                r'Company\s*size[:\s]*([0-9,]+(?:\s*[-–]\s*[0-9,]+)?)\s*employees?'
            ],
            'headquarters': [
                r'Headquarters[^>]*>\s*([^<]+)',
                r'"headquarters"\s*:\s*"([^"]+)"',
                r'<dd[^>]*>([^<]*(?:Street|Avenue|Road|Boulevard|Drive)[^<]*)</dd>',
                r'Location[:\s]*([^\n\r<]+(?:Street|Avenue|Road|Boulevard|Drive|City|State|Country)[^\n\r<]*)',
                r'Based\s*in[:\s]*([^\n\r<]+)'
            ],
            'founded': [
                r'Founded[^>]*>\s*([0-9]{4})',
                r'"founded"\s*:\s*"?([0-9]{4})"?',
                r'Since\s+([0-9]{4})',
                r'Established[:\s]*([0-9]{4})'
            ],
            'follower_count': [
                r'([0-9,]+)\s*followers?',
                r'"followerCount"\s*:\s*([0-9,]+)'
            ],
            # Enhanced location patterns
            'country': [
                r'Country[:\s]*([A-Za-z\s]+)',
                r'"addressCountry"\s*:\s*"([^"]+)"',
                r'([A-Za-z\s]+)(?:\s*,\s*[A-Z]{2,3})?$',  # Country at end of address
                r'Location[^>]*>\s*[^,]*,\s*[^,]*,\s*([A-Za-z\s]+)'
            ],
            'region': [
                r'State[:\s]*([A-Za-z\s]+)',
                r'Region[:\s]*([A-Za-z\s]+)',
                r'"addressRegion"\s*:\s*"([^"]+)"',
                r'([A-Za-z\s]+)\s*,\s*[A-Za-z\s]+$'  # State/Region before country
            ],
            'city': [
                r'City[:\s]*([A-Za-z\s]+)',
                r'"addressLocality"\s*:\s*"([^"]+)"',
                r'^([A-Za-z\s]+)\s*,'  # City at beginning of address
            ],
            'company_history': [
                r'About\s*us[^>]*>([^<]{100,})',
                r'Company\s*history[^>]*>([^<]{100,})',
                r'Our\s*story[^>]*>([^<]{100,})',
                r'"about"\s*:\s*"([^"]{100,})"'
            ]
        }
        
        # Seletores CSS aprimorados
        self.css_selectors = {
            'company_name': [
                'h1[data-test-id="org-top-card-summary-info-list"]',
                '.org-top-card-summary-info-list__info-item h1',
                '.top-card-layout__title h1',
                'h1.top-card-layout__title',
                '.org-top-card__primary-content h1',
                '[data-test-id="company-name"]',
                '.org-top-card-summary__title'
            ],
            'description': [
                '.org-about-us-organization-description__text',
                '.org-about-company-module__company-description',
                '.break-words p',
                '.org-page-details__definition-text',
                '[data-test-id="about-us-description"]',
                '.org-about-us-organization-description p'
            ],
            'industry': [
                '[data-test-id="org-industry"]',
                '.org-top-card-summary__industry',
                '.org-page-details__definition-text',
                '.industry-name'
            ],
            'employee_count': [
                '[data-test-id="org-employees-count"]',
                '.org-top-card-summary__employee-count',
                '.org-page-details__definition-text:contains("employees")',
                '.company-size',
                '[data-test-id="company-size"]',
                '.org-about-company-module__company-staff-count-range',
                '.org-top-card-summary__employee-count',
                '.employee-count'
            ],
            'headquarters': [
                '[data-test-id="org-headquarters"]',
                '.org-about-company-module__headquarters',
                '.org-top-card-summary__headquarters',
                '.headquarters-info'
            ],
            'founded': [
                '[data-test-id="org-founded"]',
                '.org-about-company-module__founded',
                '.founded-year'
            ],
            'website': [
                '[data-test-id="org-website"]',
                '.org-about-company-module__website a',
                '.website-link'
            ],
            'specialties': [
                '[data-test-id="org-specialties"]',
                '.org-about-company-module__specialties',
                '.specialties-list'
            ],
            'location': [
                '[data-test-id="org-location"]',
                '.org-top-card-summary__location',
                '.org-about-company-module__location',
                '.company-location',
                '.location-info'
            ],
            'country': [
                '.org-location-country',
                '.company-country',
                '[data-test-id="company-country"]'
            ],
            'city': [
                '.org-location-city',
                '.company-city',
                '[data-test-id="company-city"]'
            ],
            'company_history': [
                '.org-about-us-organization-description__text',
                '.org-about-company-module__description',
                '.company-description',
                '.about-us-description',
                '[data-test-id="company-description"]'
            ]
        }
    
    async def scrape_linkedin_data(self, domain: str, company_name: str = None, linkedin_url: str = None) -> LinkedInExtractionResult:
        """Método principal para extrair dados do LinkedIn com fallback para Brave Search"""
        try:
            result = LinkedInExtractionResult()
            
            # Se temos URL do LinkedIn, tentar extração direta
            if linkedin_url:
                result = await self.scrape_linkedin_company_enhanced(linkedin_url)
            
            # Se não temos dados suficientes, usar Brave Search para encontrar LinkedIn
            if result.confidence_score < 50:
                self.log_service.log_debug(f"Buscando LinkedIn via Brave Search para {domain}")
                linkedin_profile = await self.brave_search.search_linkedin_profile(domain, company_name)
                
                if linkedin_profile:
                    # Tentar extrair dados do LinkedIn encontrado
                    linkedin_result = await self.scrape_linkedin_company_enhanced(linkedin_profile)
                    if linkedin_result.confidence_score > result.confidence_score:
                        result = linkedin_result
            
            # Enriquecer com dados adicionais do Brave Search
            result = await self._enhance_with_search_data(result, domain, company_name)
            
            return result
            
        except Exception as e:
            self.log_service.log_error(f"Erro no scraping LinkedIn: {e}")
            return LinkedInExtractionResult()
    
    async def scrape_linkedin_company_enhanced(self, linkedin_url: str, html_content: str = None, use_firecrawl: bool = True) -> LinkedInExtractionResult:
        """Scraping aprimorado com múltiplas estratégias e validação"""
        try:
            self.log_service.log_debug("Iniciando scraping LinkedIn aprimorado", {
                "linkedin_url": linkedin_url,
                "use_firecrawl": use_firecrawl
            })
            
            # Obter HTML se não fornecido
            if not html_content:
                html_content = await self._get_html_content(linkedin_url, use_firecrawl)
            
            if not html_content:
                self.log_service.log_debug("Não foi possível obter conteúdo HTML")
                return LinkedInExtractionResult()
            
            # Aplicar múltiplas estratégias de extração
            extraction_results = await self._apply_extraction_strategies(html_content)
            
            # Consolidar e validar resultados
            final_result = await self._consolidate_and_validate(extraction_results, linkedin_url)
            
            self.log_service.log_debug("Scraping LinkedIn concluído", {
                "confidence_score": final_result.confidence_score,
                "methods_used": len(final_result.extraction_methods or [])
            })
            
            return final_result
            
        except Exception as e:
            self.log_service.log_debug(f"Erro no scraping LinkedIn aprimorado: {e}")
            return LinkedInExtractionResult()
    
    async def _get_html_content(self, url: str, use_firecrawl: bool) -> Optional[str]:
        """Obtém conteúdo HTML usando Firecrawl ou Crawl4AI"""
        try:
            if use_firecrawl:
                return await self._scrape_with_firecrawl(url)
            else:
                return await self._scrape_with_crawlai(url)
        except Exception as e:
            self.log_service.log_debug(f"Erro ao obter HTML: {e}")
            return None
    
    async def _scrape_with_firecrawl(self, url: str) -> Optional[str]:
        """Scraping usando Firecrawl com configurações otimizadas"""
        try:
            from firecrawl import FirecrawlApp
            
            app = FirecrawlApp(api_key=os.getenv('FIRECRAWL_API_KEY'))
            
            scrape_result = app.scrape_url(
                url,
                params={
                    'formats': ['html'],
                    'includeTags': ['div', 'span', 'p', 'h1', 'h2', 'h3', 'a', 'meta', 'script'],
                    'excludeTags': ['nav', 'footer', 'aside'],
                    'waitFor': 5000,
                    'timeout': 45000,
                    'onlyMainContent': False
                }
            )
            
            return scrape_result.get('html', '')
            
        except Exception as e:
            self.log_service.log_debug(f"Erro no Firecrawl: {e}")
            return None
    
    async def _scrape_with_crawlai(self, url: str) -> Optional[str]:
        """Scraping usando Crawl4AI como fallback"""
        try:
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    extraction_strategy=None,
                    chunking_strategy=None,
                    bypass_cache=True,
                    wait_for="networkidle",
                    timeout=30000
                )
                
                return result
        except Exception as e:
            self.log_service.log_error(f"Erro no Crawl4AI: {str(e)}")
            return None
    
    async def _enhance_with_search_data(self, linkedin_result: LinkedInExtractionResult, domain: str, company_name: str = None) -> LinkedInExtractionResult:
        """Enriquece dados do LinkedIn com informações do Brave Search"""
        try:
            # Se já temos dados suficientes, retornar como está
            if linkedin_result.confidence_score >= 80:
                return linkedin_result
            
            # Buscar dados adicionais via Brave Search
            search_data = await self.brave_search.search_company_info(domain, company_name)
            
            if search_data:
                # Preencher campos vazios com dados do search
                if not linkedin_result.company_name and search_data.get('name'):
                    linkedin_result.company_name = search_data['name']
                
                if not linkedin_result.description and search_data.get('description'):
                    linkedin_result.description = search_data['description']
                
                if not linkedin_result.industry and search_data.get('industry'):
                    linkedin_result.industry = search_data['industry']
                
                if not linkedin_result.website and search_data.get('website'):
                    linkedin_result.website = search_data['website']
                
                # Adicionar método de enriquecimento
                if linkedin_result.extraction_methods is None:
                    linkedin_result.extraction_methods = []
                linkedin_result.extraction_methods.append('brave_search_enhancement')
                
                # Recalcular score de confiança
                filled_fields = sum(1 for field in [linkedin_result.company_name, linkedin_result.description, 
                                                   linkedin_result.industry, linkedin_result.website] if field)
                linkedin_result.confidence_score = min(linkedin_result.confidence_score + (filled_fields * 5), 100.0)
            
            return linkedin_result
            
        except Exception as e:
            self.log_service.log_debug(f"Erro ao enriquecer dados: {e}")
            return linkedin_result
    
    async def _apply_extraction_strategies(self, html_content: str) -> Dict[str, Dict[str, Any]]:
        """Aplica múltiplas estratégias de extração"""
        strategies = {
            'css_selectors': await self._extract_with_css_selectors(html_content),
            'regex_patterns': await self._extract_with_regex(html_content),
            'json_ld': await self._extract_json_ld_data(html_content),
            'meta_tags': await self._extract_meta_tags(html_content),
            'structured_data': await self._extract_structured_data(html_content),
            'text_analysis': await self._analyze_text_patterns(html_content)
        }
        
        return strategies
    
    async def _extract_with_css_selectors(self, html_content: str) -> Dict[str, Any]:
        """Extração usando seletores CSS aprimorados"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = {}
            
            for field, selectors in self.css_selectors.items():
                for selector in selectors:
                    try:
                        elements = soup.select(selector)
                        if elements:
                            text = elements[0].get_text(strip=True)
                            if text and len(text) > 2:
                                results[field] = self._clean_extracted_text(text)
                                break
                    except Exception:
                        continue
            
            return results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na extração CSS: {e}")
            return {}
    
    async def _extract_with_regex(self, html_content: str) -> Dict[str, Any]:
        """Extração usando padrões regex aprimorados"""
        try:
            results = {}
            
            for field, patterns in self.regex_patterns.items():
                for pattern in patterns:
                    try:
                        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                        if matches:
                            if field == 'employee_count' and len(matches[0]) > 1:
                                # Tratar ranges de funcionários
                                results[field] = f"{matches[0][0]}-{matches[0][1]}"
                            else:
                                match_text = matches[0] if isinstance(matches[0], str) else matches[0][0]
                                cleaned = self._clean_extracted_text(match_text)
                                if cleaned:
                                    results[field] = cleaned
                                    break
                    except Exception:
                        continue
            
            return results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na extração regex: {e}")
            return {}
    
    async def _extract_json_ld_data(self, html_content: str) -> Dict[str, Any]:
        """Extração de dados estruturados JSON-LD"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = {}
            
            # Buscar scripts JSON-LD
            json_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Processar diferentes tipos de schema
                    if isinstance(data, dict):
                        if data.get('@type') == 'Organization':
                            results.update(self._extract_organization_schema(data))
                        elif data.get('@type') == 'Corporation':
                            results.update(self._extract_organization_schema(data))
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') in ['Organization', 'Corporation']:
                                results.update(self._extract_organization_schema(item))
                                
                except json.JSONDecodeError:
                    continue
            
            return results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na extração JSON-LD: {e}")
            return {}
    
    def _extract_organization_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados do schema Organization"""
        results = {}
        
        mapping = {
            'name': 'company_name',
            'description': 'description',
            'industry': 'industry',
            'numberOfEmployees': 'employee_count',
            'foundingDate': 'founded',
            'url': 'website'
        }
        
        for schema_key, result_key in mapping.items():
            if schema_key in data and data[schema_key]:
                value = data[schema_key]
                if isinstance(value, dict) and 'name' in value:
                    value = value['name']
                results[result_key] = str(value).strip()
        
        # Processar endereço
        if 'address' in data:
            address = data['address']
            if isinstance(address, dict):
                address_parts = []
                for key in ['streetAddress', 'addressLocality', 'addressRegion', 'addressCountry']:
                    if key in address and address[key]:
                        address_parts.append(str(address[key]))
                if address_parts:
                    results['headquarters'] = ', '.join(address_parts)
        
        return results
    
    async def _extract_meta_tags(self, html_content: str) -> Dict[str, Any]:
        """Extração aprimorada de meta tags"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = {}
            
            # Meta tags relevantes
            meta_mappings = {
                'og:title': 'company_name',
                'og:description': 'description',
                'description': 'description',
                'twitter:title': 'company_name',
                'twitter:description': 'description'
            }
            
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                
                if name and content and name in meta_mappings:
                    field = meta_mappings[name]
                    if field not in results:  # Priorizar primeira ocorrência
                        results[field] = self._clean_extracted_text(content)
            
            return results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na extração de meta tags: {e}")
            return {}
    
    async def _extract_structured_data(self, html_content: str) -> Dict[str, Any]:
        """Extração de dados estruturados específicos do LinkedIn"""
        try:
            results = {}
            
            # Buscar dados em atributos data-*
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Elementos com data-test-id
            test_id_mappings = {
                'org-top-card-summary-info-list': 'company_name',
                'about-us-description': 'description',
                'org-industry': 'industry',
                'org-employees-count': 'employee_count',
                'org-headquarters': 'headquarters',
                'org-founded': 'founded'
            }
            
            for test_id, field in test_id_mappings.items():
                elements = soup.find_all(attrs={'data-test-id': test_id})
                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 2:
                        results[field] = self._clean_extracted_text(text)
                        break
            
            return results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na extração de dados estruturados: {e}")
            return {}
    
    async def _analyze_text_patterns(self, html_content: str) -> Dict[str, Any]:
        """Análise de padrões de texto para extração contextual"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text()
            results = {}
            
            # Padrões contextuais
            patterns = {
                'employee_count': r'(?:We have|Company has|Team of)\s+([0-9,]+(?:-[0-9,]+)?)\s+(?:employees?|people|staff)',
                'founded': r'(?:Founded in|Established in|Since)\s+([0-9]{4})',
                'industry': r'(?:We are|Leading|Specialized in)\s+([^.]{10,50})\s+(?:company|industry|sector)',
                'headquarters': r'(?:Headquartered in|Based in|Located in)\s+([^.]{5,50})',
            }
            
            for field, pattern in patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    results[field] = self._clean_extracted_text(matches[0])
            
            return results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na análise de padrões: {e}")
            return {}
    
    async def _consolidate_and_validate(self, extraction_results: Dict[str, Dict[str, Any]], linkedin_url: str) -> LinkedInExtractionResult:
        """Consolida resultados e calcula score de confiança"""
        result = LinkedInExtractionResult()
        result.extraction_methods = []
        
        # Prioridade das estratégias (mais confiável primeiro)
        strategy_priority = ['json_ld', 'structured_data', 'css_selectors', 'meta_tags', 'regex_patterns', 'text_analysis']
        
        # Campos e seus pesos para cálculo de confiança
        field_weights = {
            'company_name': 0.25,
            'description': 0.20,
            'industry': 0.15,
            'employee_count': 0.10,
            'headquarters': 0.10,
            'founded': 0.08,
            'website': 0.07,
            'specialties': 0.05
        }
        
        # Consolidar dados por prioridade
        consolidated_data = {}
        method_scores = {}
        
        for strategy in strategy_priority:
            if strategy in extraction_results:
                strategy_data = extraction_results[strategy]
                method_scores[strategy] = len(strategy_data)
                
                for field, value in strategy_data.items():
                    if field not in consolidated_data and value:
                        validated_value = self._validate_field_value(field, value)
                        if validated_value:
                            consolidated_data[field] = validated_value
                            if strategy not in result.extraction_methods:
                                result.extraction_methods.append(strategy)
        
        # Mapear dados consolidados para o resultado
        result.company_name = consolidated_data.get('company_name')
        result.description = consolidated_data.get('description')
        result.industry = consolidated_data.get('industry')
        result.company_size = consolidated_data.get('company_size')
        result.headquarters = consolidated_data.get('headquarters')
        result.founded = consolidated_data.get('founded')
        result.website = consolidated_data.get('website')
        
        # Novos campos de localização
        result.country = consolidated_data.get('country')
        result.city = consolidated_data.get('city')
        result.region = consolidated_data.get('region')
        result.postal_code = consolidated_data.get('postal_code')
        result.street_address = consolidated_data.get('street_address')
        
        # Histórico da empresa
        result.company_history = consolidated_data.get('company_history')
        result.employee_count_range = consolidated_data.get('employee_count_range')
        
        # Processar localização a partir do headquarters se disponível
        if result.headquarters and not result.country:
            location_parts = result.headquarters.split(',')
            if len(location_parts) >= 2:
                result.city = location_parts[0].strip()
                result.country = location_parts[-1].strip()
                if len(location_parts) >= 3:
                    result.region = location_parts[1].strip()
        
        # Gerar código do país se temos o nome do país
        if result.country and not result.country_code:
            result.country_code = self._get_country_code(result.country)
        
        # Processar employee_count
        if 'employee_count' in consolidated_data:
            result.employee_count = self._parse_employee_count(consolidated_data['employee_count'])
            result.employee_count_exact = result.employee_count
        
        # Processar specialties
        if 'specialties' in consolidated_data:
            result.specialties = self._parse_specialties(consolidated_data['specialties'])
        
        # Processar follower_count
        if 'follower_count' in consolidated_data:
            result.follower_count = self._parse_number(consolidated_data['follower_count'])
        
        # Calcular score de confiança
        result.confidence_score = self._calculate_confidence_score(consolidated_data, field_weights, method_scores)
        
        return result
    
    def _validate_field_value(self, field: str, value: str) -> Optional[str]:
        """Valida e limpa valores de campos específicos"""
        if not value or not isinstance(value, str):
            return None
        
        value = value.strip()
        
        # Validações específicas por campo
        if field == 'company_name':
            if len(value) < 2 or len(value) > 200:
                return None
            # Remover sufixos comuns
            value = re.sub(r'\s*\|\s*LinkedIn.*$', '', value, flags=re.IGNORECASE)
            
        elif field == 'description':
            if len(value) < 10 or len(value) > 2000:
                return None
                
        elif field == 'founded':
            # Extrair apenas o ano
            year_match = re.search(r'(19|20)\d{2}', value)
            if year_match:
                year = int(year_match.group())
                if 1800 <= year <= 2024:
                    return str(year)
            return None
            
        elif field == 'employee_count':
            # Validar formato de contagem de funcionários
            if not re.match(r'^[0-9,\-\s]+$', value):
                return None
        
        return value
    
    def _parse_employee_count(self, value: str) -> Optional[int]:
        """Converte string de contagem de funcionários para número"""
        try:
            # Remover vírgulas e espaços
            clean_value = re.sub(r'[,\s]', '', value)
            
            # Se for um range, pegar o valor médio
            if '-' in clean_value:
                parts = clean_value.split('-')
                if len(parts) == 2:
                    min_val = int(parts[0])
                    max_val = int(parts[1])
                    return (min_val + max_val) // 2
            else:
                return int(clean_value)
                
        except (ValueError, IndexError):
            return None
    
    def _parse_specialties(self, value: str) -> List[str]:
        """Converte string de especialidades para lista"""
        if not value:
            return []
        
        # Dividir por vírgulas, pontos e vírgulas, ou quebras de linha
        specialties = re.split(r'[,;\n]', value)
        return [s.strip() for s in specialties if s.strip()]
    
    def _parse_number(self, value: str) -> Optional[int]:
        """Extrai número de uma string"""
        try:
            # Remove caracteres não numéricos exceto vírgulas e pontos
            clean_value = re.sub(r'[^0-9,.]', '', value)
            # Remove vírgulas (separadores de milhares)
            clean_value = clean_value.replace(',', '')
            return int(float(clean_value))
        except (ValueError, TypeError):
            return None
    
    def _get_country_code(self, country_name: str) -> Optional[str]:
        """Converte nome do país para código ISO"""
        if not country_name:
            return None
            
        country_mapping = {
            'United States': 'US', 'USA': 'US', 'America': 'US',
            'United Kingdom': 'GB', 'UK': 'GB', 'England': 'GB',
            'Brazil': 'BR', 'Brasil': 'BR',
            'Canada': 'CA',
            'Germany': 'DE', 'Deutschland': 'DE',
            'France': 'FR',
            'Italy': 'IT', 'Italia': 'IT',
            'Spain': 'ES', 'España': 'ES',
            'Netherlands': 'NL', 'Holland': 'NL',
            'Australia': 'AU',
            'Japan': 'JP',
            'China': 'CN',
            'India': 'IN',
            'Mexico': 'MX', 'México': 'MX',
            'Argentina': 'AR',
            'Chile': 'CL',
            'Colombia': 'CO',
            'Peru': 'PE', 'Perú': 'PE',
            'Portugal': 'PT',
            'Russia': 'RU',
            'South Korea': 'KR', 'Korea': 'KR',
            'Singapore': 'SG',
            'Switzerland': 'CH',
            'Sweden': 'SE',
            'Norway': 'NO',
            'Denmark': 'DK',
            'Finland': 'FI',
            'Belgium': 'BE',
            'Austria': 'AT',
            'Ireland': 'IE',
            'Poland': 'PL',
            'Czech Republic': 'CZ',
            'Hungary': 'HU',
            'Romania': 'RO',
            'Bulgaria': 'BG',
            'Croatia': 'HR',
            'Slovenia': 'SI',
            'Slovakia': 'SK',
            'Lithuania': 'LT',
            'Latvia': 'LV',
            'Estonia': 'EE'
        }
        
        country_clean = country_name.strip().title()
        return country_mapping.get(country_clean)
    
    def _clean_extracted_text(self, text: str) -> str:
        """Limpa texto extraído removendo caracteres desnecessários"""
        if not text:
            return ""
        
        # Remover quebras de linha excessivas e espaços
        text = re.sub(r'\s+', ' ', text)
        
        # Remover caracteres especiais no início e fim
        text = text.strip('\n\r\t •-')
        
        # Decodificar entidades HTML
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        
        return text.strip()
    
    def _calculate_confidence_score(self, data: Dict[str, Any], field_weights: Dict[str, float], method_scores: Dict[str, int]) -> float:
        """Calcula score de confiança baseado na qualidade dos dados extraídos"""
        total_score = 0.0
        
        # Score baseado nos campos preenchidos
        for field, weight in field_weights.items():
            if field in data and data[field]:
                total_score += weight
        
        # Bonus por múltiplos métodos de extração
        method_bonus = min(len(method_scores) * 0.1, 0.3)
        
        # Bonus por métodos mais confiáveis
        reliability_bonus = 0.0
        if 'json_ld' in method_scores:
            reliability_bonus += 0.15
        if 'structured_data' in method_scores:
            reliability_bonus += 0.10
        
        final_score = min((total_score + method_bonus + reliability_bonus) * 100, 100.0)
        return round(final_score, 2)
    
    def is_linkedin_company_url(self, url: str) -> bool:
        """Verifica se a URL é de uma página de empresa do LinkedIn"""
        if not url:
            return False
        
        url_lower = url.lower()
        return 'linkedin.com/company/' in url_lower
    
    def extract_company_slug(self, linkedin_url: str) -> Optional[str]:
        """Extrai o slug da empresa da URL do LinkedIn"""
        try:
            if '/company/' in linkedin_url:
                return linkedin_url.split('/company/')[1].split('/')[0].split('?')[0]
            return None
        except Exception:
            return None