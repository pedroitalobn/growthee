import asyncio
import json
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime

@dataclass
class LinkedInCompanyData:
    """Estrutura de dados padronizada para empresas do LinkedIn"""
    linkedin_url: str
    company_name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    employee_count: Optional[str] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    website: Optional[str] = None
    specialties: Optional[List[str]] = None
    follower_count: Optional[str] = None
    recent_posts: Optional[List[str]] = None
    leadership: Optional[List[Dict[str, str]]] = None
    
    # Dados de localização
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None
    
    # Metadados
    extraction_timestamp: Optional[str] = None
    data_source: Optional[str] = None
    confidence_score: Optional[float] = None
    extraction_methods: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.extraction_timestamp is None:
            self.extraction_timestamp = datetime.utcnow().isoformat()
        if self.specialties is None:
            self.specialties = []
        if self.recent_posts is None:
            self.recent_posts = []
        if self.leadership is None:
            self.leadership = []
        if self.extraction_methods is None:
            self.extraction_methods = []

class EnhancedLinkedInScraper:
    """Scraper LinkedIn avançado com múltiplas estratégias e alta precisão"""
    
    def __init__(self, log_service):
        self.log_service = log_service
        
        # Seletores CSS atualizados para LinkedIn 2024
        self.css_selectors = {
            'company_name': [
                'h1[data-test-id="org-top-card-summary-info-list"]',
                '.org-top-card-summary-info-list__info-item h1',
                '.top-card-layout__title h1',
                'h1.top-card-layout__title',
                '.org-top-card__primary-content h1',
                '.org-top-card-summary__title h1',
                '[data-test-id="company-name"] h1'
            ],
            'tagline': [
                '.org-top-card-summary__tagline',
                '.org-top-card-summary-info-list__info-item .break-words',
                '[data-test-id="company-tagline"]'
            ],
            'description': [
                '.org-about-us-organization-description__text',
                '.org-about-company-module__company-description',
                '.break-words p',
                '.org-page-details__definition-text',
                '[data-test-id="about-us-description"]',
                '.org-about-module__description'
            ],
            'industry': [
                '.org-top-card-summary-info-list__info-item:contains("Industry")',
                '.org-page-details__definition-text',
                '[data-test-id="org-industry"]',
                '.org-top-card-summary__industry',
                '.org-about-company-module__industry'
            ],
            'company_size': [
                '.org-top-card-summary-info-list__info-item:contains("employees")',
                '[data-test-id="org-employees-count"]',
                '.org-about-company-module__company-staff-count-range',
                '.org-top-card-summary__employee-count',
                '.org-about-company-module__company-size'
            ],
            'headquarters': [
                '.org-top-card-summary-info-list__info-item:contains("headquarters")',
                '[data-test-id="org-headquarters"]',
                '.org-about-company-module__headquarters',
                '.org-top-card-summary__headquarters',
                '.org-about-company-module__location'
            ],
            # Novos seletores para dados de localização
            'country': [
                '.org-location-card__card-subtitle:contains("Country")',
                '.org-about-company-module__headquarters span:contains("Country")',
                '[data-test-id="org-location-country"]'
            ],
            'region': [
                '.org-location-card__card-subtitle:contains("Region")',
                '.org-about-company-module__headquarters span:contains("Region")',
                '[data-test-id="org-location-region"]'
            ],
            'city': [
                '.org-location-card__card-subtitle:contains("City")',
                '.org-about-company-module__headquarters span:contains("City")',
                '[data-test-id="org-location-city"]'
            ],
            'founded': [
                '.org-about-company-module__founded',
                '[data-test-id="org-founded"]',
                '.org-top-card-summary__founded',
                '.org-about-company-module__founding-date'
            ],
            'website': [
                '.org-about-company-module__website a',
                '[data-test-id="org-website"] a',
                '.org-top-card-summary__website a',
                '.org-about-company-module__link a'
            ],
            'specialties': [
                '.org-about-company-module__specialties',
                '[data-test-id="org-specialties"]',
                '.org-page-details__definition-text',
                '.org-about-company-module__specialties-list'
            ],
            'follower_count': [
                '.org-top-card-summary-info-list__info-item:contains("followers")',
                '[data-test-id="org-followers-count"]',
                '.org-top-card__follower-count',
                '.org-top-card-summary__followers'
            ]
        }
        
        # Padrões regex aprimorados
        self.regex_patterns = {
            'employee_count': [
                r'([\d,]+(?:-[\d,]+)?)\s*employees?',
                r'([\d,]+)\s*employees?\s*on\s*LinkedIn',
                r'Company\s*size[:\s]*([\d,]+(?:-[\d,]+)?)\s*employees?'
            ],
            'follower_count': [
                r'([\d,]+)\s*followers?',
                r'([\d,]+)\s*people\s*follow'
            ],
            'founded_year': [
                r'founded[\s]*(?:in[\s]*)?(\d{4})',
                r'established[\s]*(?:in[\s]*)?(\d{4})',
                r'since[\s]*(\d{4})'
            ],
            'industry_text': r'industry[\s]*:?[\s]*([^\n\r]+)',
            'headquarters_text': r'headquarters[\s]*:?[\s]*([^\n\r]+)',
            'website_url': r'https?://(?:www\.)?[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}(?:/[^\s]*)?'
        }
        
        # Mapeamento de campos JSON-LD
        self.json_ld_mappings = {
            'name': 'company_name',
            'alternateName': 'tagline',
            'description': 'description',
            'industry': 'industry',
            'numberOfEmployees': 'employee_count',
            'foundingDate': 'founded',
            'url': 'website',
            'address': 'headquarters',
            'location': 'headquarters',
            'sameAs': 'website'
        }
    
    async def scrape_company(self, linkedin_url: str, html_content: str = None, 
                           use_firecrawl: bool = True, use_crawlai: bool = True) -> LinkedInCompanyData:
        """Método principal para scraping de empresa LinkedIn"""
        try:
            self.log_service.log_debug("Starting enhanced LinkedIn company scraping", {
                "url": linkedin_url,
                "has_html": html_content is not None,
                "use_firecrawl": use_firecrawl,
                "use_crawlai": use_crawlai
            })
            
            # Obter HTML se não fornecido
            if not html_content:
                html_content = await self._get_html_content(linkedin_url, use_firecrawl, use_crawlai)
            
            if not html_content:
                return LinkedInCompanyData(
                    linkedin_url=linkedin_url,
                    data_source="failed_to_fetch",
                    confidence_score=0.0
                )
            
            # Executar múltiplas estratégias de extração
            extraction_results = await self._run_extraction_strategies(html_content)
            
            # Consolidar dados
            consolidated_data = await self._consolidate_data(extraction_results, linkedin_url)
            
            # Calcular score de confiança
            confidence_score = self._calculate_confidence_score(consolidated_data, extraction_results)
            
            # Criar objeto de dados final
            company_data = LinkedInCompanyData(
                linkedin_url=linkedin_url,
                company_name=consolidated_data.get('company_name'),
                tagline=consolidated_data.get('tagline'),
                description=consolidated_data.get('description'),
                industry=consolidated_data.get('industry'),
                company_size=consolidated_data.get('company_size'),
                employee_count=consolidated_data.get('employee_count'),
                headquarters=consolidated_data.get('headquarters'),
                founded=consolidated_data.get('founded'),
                website=consolidated_data.get('website'),
                specialties=consolidated_data.get('specialties', []),
                follower_count=consolidated_data.get('follower_count'),
                recent_posts=consolidated_data.get('recent_posts', []),
                leadership=consolidated_data.get('leadership', []),
                # Adicionar dados de localização
                country=consolidated_data.get('country'),
                region=consolidated_data.get('region'),
                city=consolidated_data.get('city'),
                postal_code=consolidated_data.get('postal_code'),
                street_address=consolidated_data.get('street_address'),
                data_source=consolidated_data.get('data_source', 'enhanced_scraper'),
                confidence_score=confidence_score,
                extraction_methods=list(extraction_results.keys())
            )
            
            self.log_service.log_debug("LinkedIn scraping completed", {
                "url": linkedin_url,
                "confidence_score": confidence_score,
                "fields_extracted": len([v for v in asdict(company_data).values() if v]),
                "methods_used": len(extraction_results)
            })
            
            return company_data
            
        except Exception as e:
            self.log_service.log_debug(f"Enhanced LinkedIn scraping error: {e}", {
                "url": linkedin_url,
                "error": str(e)
            })
            return LinkedInCompanyData(
                linkedin_url=linkedin_url,
                data_source="error",
                confidence_score=0.0
            )
    
    async def _get_html_content(self, url: str, use_firecrawl: bool, use_crawlai: bool) -> Optional[str]:
        """Obtém conteúdo HTML usando múltiplos provedores"""
        html_content = None
        
        # Tentar Firecrawl primeiro
        if use_firecrawl:
            html_content = await self._scrape_with_firecrawl(url)
            if html_content:
                return html_content
        
        # Fallback para CrawlAI
        if use_crawlai:
            html_content = await self._scrape_with_crawlai(url)
        
        return html_content
    
    async def _scrape_with_firecrawl(self, url: str) -> Optional[str]:
        """Scraping usando Firecrawl"""
        try:
            from firecrawl import FirecrawlApp
            from ..config import settings
            
            if not hasattr(settings, 'FIRECRAWL_API_KEY') or not settings.FIRECRAWL_API_KEY:
                return None
            
            app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
            
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
            
            return scrape_result.get('html', '') if scrape_result else None
            
        except Exception as e:
            self.log_service.log_debug(f"Firecrawl error: {e}")
            return None
    
    async def _scrape_with_crawlai(self, url: str) -> Optional[str]:
        """Scraping usando CrawlAI"""
        try:
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    bypass_cache=True,
                    wait_for="css:.org-top-card-summary-info-list,css:.org-about-company-module",
                    delay_before_return_html=5.0,
                    page_timeout=45000,
                    js_code=[
                        "window.scrollTo(0, document.body.scrollHeight/3);",
                        "await new Promise(resolve => setTimeout(resolve, 2000));",
                        "window.scrollTo(0, document.body.scrollHeight/2);",
                        "await new Promise(resolve => setTimeout(resolve, 2000));"
                    ]
                )
                
                return result.html if result.success else None
                
        except Exception as e:
            self.log_service.log_debug(f"CrawlAI error: {e}")
            return None
    
    async def _run_extraction_strategies(self, html_content: str) -> Dict[str, Dict[str, Any]]:
        """Executa múltiplas estratégias de extração"""
        strategies = {
            'css_selectors': self._extract_with_css_selectors,
            'regex_patterns': self._extract_with_regex,
            'json_ld': self._extract_json_ld_data,
            'meta_tags': self._extract_meta_tags,
            'text_analysis': self._extract_text_content,
            'structured_data': self._extract_structured_data
        }
        
        results = {}
        for strategy_name, strategy_func in strategies.items():
            try:
                result = await strategy_func(html_content)
                if result:
                    results[strategy_name] = result
            except Exception as e:
                self.log_service.log_debug(f"Strategy {strategy_name} failed: {e}")
        
        return results
    
    async def _extract_with_css_selectors(self, html_content: str) -> Dict[str, Any]:
        """Extração usando seletores CSS"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for field, selectors in self.css_selectors.items():
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        element = elements[0]
                        
                        if field == 'website':
                            href = element.get('href')
                            if href and self._is_valid_url(href):
                                results[field] = href
                                break
                        elif field == 'specialties':
                            # Especialidades podem estar em lista
                            text = element.get_text(strip=True)
                            if text:
                                specialties = [s.strip() for s in re.split(r'[,•·]', text) if s.strip()]
                                results[field] = specialties[:10]  # Limitar a 10
                                break
                        else:
                            text = element.get_text(strip=True)
                            if text and len(text) > 1:
                                results[field] = self._clean_text(text)
                                break
                except Exception:
                    continue
        
        return results
    
    async def _extract_with_regex(self, html_content: str) -> Dict[str, Any]:
        """Extração usando padrões regex"""
        results = {}
        
        for field, patterns in self.regex_patterns.items():
            if isinstance(patterns, list):
                for pattern in patterns:
                    matches = re.finditer(pattern, html_content, re.IGNORECASE | re.MULTILINE)
                    for match in matches:
                        value = match.group(1).strip()
                        if value and len(value) > 1:
                            results[field] = self._clean_text(value)
                            break
                    if field in results:
                        break
            else:
                matches = re.finditer(patterns, html_content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    value = match.group(1).strip()
                    if value and len(value) > 1:
                        results[field] = self._clean_text(value)
                        break
        
        return results
    
    async def _extract_json_ld_data(self, html_content: str) -> Dict[str, Any]:
        """Extração de dados estruturados JSON-LD"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, list):
                    data = data[0] if data else {}
                
                if isinstance(data, dict):
                    # Processar dados JSON-LD
                    for json_field, our_field in self.json_ld_mappings.items():
                        if json_field in data and data[json_field]:
                            value = data[json_field]
                            if isinstance(value, str):
                                results[our_field] = self._clean_text(value)
                            elif isinstance(value, (int, float)):
                                results[our_field] = str(value)
                            elif isinstance(value, list) and value:
                                results[our_field] = [str(v) for v in value[:5]]  # Limitar a 5
                
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return results
    
    async def _extract_meta_tags(self, html_content: str) -> Dict[str, Any]:
        """Extração de meta tags"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        meta_mappings = {
            'og:title': 'company_name',
            'og:description': 'description',
            'og:url': 'linkedin_url',
            'twitter:title': 'company_name',
            'twitter:description': 'description',
            'description': 'description'
        }
        
        for meta_property, field in meta_mappings.items():
            meta_tag = (soup.find('meta', property=meta_property) or 
                       soup.find('meta', attrs={'name': meta_property}))
            if meta_tag:
                content = meta_tag.get('content')
                if content and content.strip():
                    results[field] = self._clean_text(content.strip())
        
        return results
    
    async def _extract_text_content(self, html_content: str) -> Dict[str, Any]:
        """Análise de texto para extração contextual"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        # Padrões contextuais avançados
        contextual_patterns = {
            'company_size_range': r'(\d{1,3}(?:,\d{3})*\s*-\s*\d{1,3}(?:,\d{3})*)\s*employees',
            'exact_employee_count': r'(\d{1,3}(?:,\d{3})*)\s*employees?\s*on\s*LinkedIn',
            'industry_context': r'(?:industry|sector|field)\s*:?\s*([^\n\r\.]{10,80})',
            'location_context': r'(?:based|located|headquarters|hq)\s*(?:in|at)\s*([^\n\r\.]{5,50})',
            'founded_context': r'(?:founded|established|started|since)\s*(?:in|on)?\s*(\d{4})',
            'website_context': r'(?:website|site|web)\s*:?\s*(https?://[^\s\n\r]+)',
            'tagline_context': r'(?:tagline|slogan|motto)\s*:?\s*([^\n\r\.]{10,100})'
        }
        
        for pattern_name, pattern in contextual_patterns.items():
            try:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    value = match.group(1).strip()
                    if value and len(value) > 2:
                        results[pattern_name] = self._clean_text(value)
                        break
            except Exception:
                continue
        
        return results
    
    async def _extract_structured_data(self, html_content: str) -> Dict[str, Any]:
        """Extração de dados estruturados específicos do LinkedIn"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Buscar por elementos específicos do LinkedIn
        try:
            # Posts recentes
            post_elements = soup.select('.feed-shared-update-v2, .occludable-update')
            if post_elements:
                posts = []
                for post in post_elements[:5]:  # Máximo 5 posts
                    post_text = post.get_text(strip=True)
                    if post_text and len(post_text) > 20:
                        posts.append(post_text[:200])  # Limitar tamanho
                results['recent_posts'] = posts
            
            # Liderança/Funcionários
            leadership_elements = soup.select('.org-people-profile-card, .people-card')
            if leadership_elements:
                leadership = []
                for leader in leadership_elements[:10]:  # Máximo 10
                    name_elem = leader.select_one('.people-card__name, .profile-card__name')
                    title_elem = leader.select_one('.people-card__title, .profile-card__title')
                    
                    if name_elem:
                        leader_data = {'name': name_elem.get_text(strip=True)}
                        if title_elem:
                            leader_data['title'] = title_elem.get_text(strip=True)
                        leadership.append(leader_data)
                
                results['leadership'] = leadership
        
        except Exception as e:
            self.log_service.log_debug(f"Structured data extraction error: {e}")
        
        return results
    
    async def _consolidate_data(self, extraction_results: Dict[str, Dict[str, Any]], 
                              linkedin_url: str) -> Dict[str, Any]:
        """Consolida dados de múltiplas estratégias com priorização inteligente"""
        consolidated = {'linkedin_url': linkedin_url}
        
        # Prioridade de fontes (mais confiável primeiro)
        source_priority = [
            'json_ld',
            'css_selectors', 
            'structured_data',
            'meta_tags',
            'regex_patterns',
            'text_analysis'
        ]
        
        # Mapeamento de campos com aliases
        field_mappings = {
            'company_name': ['company_name', 'name'],
            'tagline': ['tagline', 'tagline_context'],
            'description': ['description', 'company_description'],
            'industry': ['industry', 'industry_text', 'industry_mention', 'industry_context'],
            'company_size': ['company_size', 'company_size_range', 'exact_employee_count'],
            'employee_count': ['employee_count', 'exact_employee_count', 'company_size_range'],
            'headquarters': ['headquarters', 'headquarters_text', 'location_mention', 'location_context'],
            'founded': ['founded', 'founded_year', 'founded_mention', 'founded_context'],
            'website': ['website', 'website_context'],
            'specialties': ['specialties', 'specialties_mention'],
            'follower_count': ['follower_count'],
            'recent_posts': ['recent_posts'],
            'leadership': ['leadership']
        }
        
        # Consolidar por prioridade
        for field, possible_keys in field_mappings.items():
            for source in source_priority:
                if source in extraction_results:
                    source_data = extraction_results[source]
                    for key in possible_keys:
                        if key in source_data and source_data[key]:
                            value = source_data[key]
                            
                            # Validação e limpeza específica por campo
                            cleaned_value = self._validate_and_clean_field(field, value)
                            if cleaned_value:
                                consolidated[field] = cleaned_value
                                break
                
                if field in consolidated:
                    break
        
        return consolidated
    
    def _validate_and_clean_field(self, field: str, value: Any) -> Any:
        """Valida e limpa valores específicos por campo"""
        if not value:
            return None
        
        if field == 'website':
            return value if self._is_valid_url(str(value)) else None
        
        elif field in ['employee_count', 'follower_count']:
            # Extrair números de strings
            if isinstance(value, str):
                numbers = re.findall(r'[\d,]+', value)
                return numbers[0] if numbers else None
            return str(value)
        
        elif field == 'founded':
            # Extrair ano
            if isinstance(value, str):
                years = re.findall(r'\d{4}', value)
                return years[0] if years else None
            return str(value)
        
        elif field in ['specialties', 'recent_posts', 'leadership']:
            return value if isinstance(value, list) else None
        
        elif isinstance(value, str):
            cleaned = self._clean_text(value)
            return cleaned if len(cleaned) > 1 else None
        
        return value
    
    def _calculate_confidence_score(self, consolidated_data: Dict[str, Any], 
                                  extraction_results: Dict[str, Dict[str, Any]]) -> float:
        """Calcula score de confiança baseado na qualidade dos dados"""
        # Campos essenciais com pesos
        essential_fields = {
            'company_name': 0.25,
            'description': 0.20,
            'industry': 0.15,
            'company_size': 0.10,
            'headquarters': 0.10,
            'website': 0.10,
            'founded': 0.05,
            'specialties': 0.05
        }
        
        score = 0.0
        
        # Score baseado em campos preenchidos
        for field, weight in essential_fields.items():
            if consolidated_data.get(field):
                score += weight
        
        # Bonus por múltiplas fontes
        methods_bonus = min(len(extraction_results) * 0.05, 0.15)
        score += methods_bonus
        
        # Penalty por dados incompletos
        if not consolidated_data.get('company_name'):
            score *= 0.5  # Penalidade severa se não tem nome
        
        return min(score, 1.0)
    
    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza texto"""
        if not text:
            return ""
        
        # Remove caracteres especiais e normaliza espaços
        cleaned = re.sub(r'\s+', ' ', text.strip())
        cleaned = re.sub(r'[\r\n\t]+', ' ', cleaned)
        
        # Remove caracteres de controle
        cleaned = ''.join(char for char in cleaned if ord(char) >= 32 or char in '\n\r\t')
        
        return cleaned.strip()
    
    def _is_valid_url(self, url: str) -> bool:
        """Valida se é uma URL válida"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def is_linkedin_company_url(self, url: str) -> bool:
        """Verifica se é URL de empresa LinkedIn"""
        if not url:
            return False
        
        url_lower = url.lower()
        return (
            'linkedin.com/company/' in url_lower or
            'linkedin.com/school/' in url_lower
        )
    
    def extract_company_slug(self, linkedin_url: str) -> Optional[str]:
        """Extrai slug da empresa da URL"""
        try:
            if '/company/' in linkedin_url:
                return linkedin_url.split('/company/')[1].split('/')[0].split('?')[0]
            elif '/school/' in linkedin_url:
                return linkedin_url.split('/school/')[1].split('/')[0].split('?')[0]
            return None
        except Exception:
            return None
    
    async def find_linkedin_on_website(self, website_url: str) -> Optional[Dict[str, Any]]:
        """Encontra URLs do LinkedIn em websites"""
        try:
            # Tentar obter HTML do website
            html_content = await self._get_html_content(website_url, use_firecrawl=True, use_crawlai=True)
            if not html_content:
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            linkedin_urls = set()
            
            # Buscar links diretos
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'linkedin.com' in href:
                    # Normalizar URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = urljoin(website_url, href)
                    
                    if self.is_linkedin_company_url(href):
                        linkedin_urls.add(href)
            
            # Buscar em texto e scripts
            text_content = soup.get_text()
            linkedin_patterns = [
                r'https?://(?:www\.)?linkedin\.com/company/[\w-]+/?',
                r'linkedin\.com/company/[\w-]+/?'
            ]
            
            for pattern in linkedin_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if not match.startswith('http'):
                        match = 'https://' + match
                    if self.is_linkedin_company_url(match):
                        linkedin_urls.add(match)
            
            if linkedin_urls:
                # Retornar o primeiro URL encontrado com score de confiança
                linkedin_url = list(linkedin_urls)[0]
                return {
                    'linkedin_url': linkedin_url,
                    'confidence_score': 0.8,
                    'found_urls': list(linkedin_urls),
                    'extraction_method': 'website_scan'
                }
            
            return None
            
        except Exception as e:
            if hasattr(self, 'log_service'):
                self.log_service.log_debug("Error finding LinkedIn on website", {
                    "error": str(e),
                    "website_url": website_url
                })
            return None