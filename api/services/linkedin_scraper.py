import asyncio
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from ..log_service import LogService
from ..config import settings

class LinkedInScraper:
    """Scraper especializado para LinkedIn que coleta informações detalhadas da empresa"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        
        # Seletores CSS específicos do LinkedIn
        self.linkedin_selectors = {
            'company_name': [
                'h1[data-test-id="org-top-card-summary-info-list"]',
                '.org-top-card-summary-info-list__info-item h1',
                '.top-card-layout__title h1',
                'h1.top-card-layout__title',
                '.org-top-card__primary-content h1'
            ],
            'company_description': [
                '.org-about-us-organization-description__text',
                '.org-about-company-module__company-description',
                '.break-words p',
                '.org-page-details__definition-text',
                '[data-test-id="about-us-description"]'
            ],
            'industry': [
                '.org-top-card-summary-info-list__info-item:contains("Industry")',
                '.org-page-details__definition-text',
                '[data-test-id="org-industry"]',
                '.org-top-card-summary__industry'
            ],
            'company_size': [
                '.org-top-card-summary-info-list__info-item:contains("employees")',
                '[data-test-id="org-employees-count"]',
                '.org-about-company-module__company-staff-count-range',
                '.org-top-card-summary__employee-count'
            ],
            'headquarters': [
                '.org-top-card-summary-info-list__info-item:contains("headquarters")',
                '[data-test-id="org-headquarters"]',
                '.org-about-company-module__headquarters',
                '.org-top-card-summary__headquarters'
            ],
            'founded': [
                '.org-about-company-module__founded',
                '[data-test-id="org-founded"]',
                '.org-top-card-summary__founded'
            ],
            'website': [
                '.org-about-company-module__website a',
                '[data-test-id="org-website"] a',
                '.org-top-card-summary__website a'
            ],
            'specialties': [
                '.org-about-company-module__specialties',
                '[data-test-id="org-specialties"]',
                '.org-page-details__definition-text'
            ],
            'follower_count': [
                '.org-top-card-summary-info-list__info-item:contains("followers")',
                '[data-test-id="org-followers-count"]',
                '.org-top-card__follower-count'
            ],
            'employee_count': [
                '.org-about-company-module__company-staff-count-range',
                '[data-test-id="org-employees-count"]'
            ]
        }
        
        # Padrões regex para extração de dados específicos
        self.linkedin_patterns = {
            'employee_count': r'([\d,]+(?:-[\d,]+)?)[\s]*employees?',
            'follower_count': r'([\d,]+)[\s]*followers?',
            'founded_year': r'founded[\s]*(?:in[\s]*)?([\d]{4})',
            'industry_text': r'industry[\s]*:?[\s]*([^\n\r]+)',
            'headquarters_text': r'headquarters[\s]*:?[\s]*([^\n\r]+)'
        }
    
    async def scrape_linkedin_company(self, linkedin_url: str, html_content: str = None, use_firecrawl: bool = True) -> Dict[str, Any]:
        """Scraping completo de uma página de empresa no LinkedIn"""
        try:
            self.log_service.log_debug("Iniciando scraping do LinkedIn", {
                "linkedin_url": linkedin_url,
                "use_firecrawl": use_firecrawl,
                "has_html_content": html_content is not None
            })
            
            # Se não temos HTML, precisamos fazer scraping
            if not html_content:
                if use_firecrawl:
                    html_content = await self._scrape_with_firecrawl(linkedin_url)
                else:
                    html_content = await self._scrape_with_crawlai(linkedin_url)
            
            if not html_content:
                self.log_service.log_debug("Não foi possível obter conteúdo HTML do LinkedIn")
                return {}
            
            # Múltiplas estratégias de extração
            results = {
                'css_extraction': await self._extract_with_css_selectors(html_content),
                'regex_extraction': await self._extract_with_regex(html_content),
                'json_ld_extraction': await self._extract_json_ld_data(html_content),
                'meta_tags_extraction': await self._extract_meta_tags(html_content),
                'text_analysis': await self._analyze_text_content(html_content)
            }
            
            # Consolidar resultados
            consolidated = await self._consolidate_linkedin_data(results, linkedin_url)
            
            self.log_service.log_debug("Scraping do LinkedIn concluído", {
                "linkedin_url": linkedin_url,
                "fields_extracted": len([k for k, v in consolidated.items() if v])
            })
            
            return consolidated
            
        except Exception as e:
            self.log_service.log_debug(f"Erro no scraping do LinkedIn: {e}", {
                "linkedin_url": linkedin_url,
                "error": str(e)
            })
            return {}
    
    async def _scrape_with_firecrawl(self, url: str) -> Optional[str]:
        """Scraping usando Firecrawl"""
        try:
            from firecrawl import FirecrawlApp
            
            app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
            
            scrape_result = app.scrape_url(
                url,
                params={
                    'formats': ['html', 'markdown'],
                    'includeTags': ['div', 'span', 'p', 'h1', 'h2', 'h3', 'a', 'meta'],
                    'excludeTags': ['script', 'style', 'nav', 'footer'],
                    'waitFor': 3000,
                    'timeout': 30000
                }
            )
            
            return scrape_result.get('html', '')
            
        except Exception as e:
            self.log_service.log_debug(f"Erro no Firecrawl: {e}")
            return None
    
    async def _scrape_with_crawlai(self, url: str) -> Optional[str]:
        """Scraping usando CrawlAI como fallback"""
        try:
            from crawl4ai import AsyncWebCrawler
            
            async with AsyncWebCrawler(verbose=True) as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    extraction_strategy=None,
                    chunking_strategy=None,
                    bypass_cache=True,
                    wait_for="css:.org-top-card-summary-info-list",
                    delay_before_return_html=3.0
                )
                
                return result.html if result.success else None
                
        except Exception as e:
            self.log_service.log_debug(f"Erro no CrawlAI: {e}")
            return None
    
    async def _extract_with_css_selectors(self, html_content: str) -> Dict[str, Any]:
        """Extração usando seletores CSS específicos do LinkedIn"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for field, selectors in self.linkedin_selectors.items():
            for selector in selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        if field == 'website':
                            # Para website, pegar o href
                            href = elements[0].get('href')
                            if href:
                                results[field] = href
                                break
                        else:
                            # Para outros campos, pegar o texto
                            text = elements[0].get_text(strip=True)
                            if text and len(text) > 2:
                                results[field] = text
                                break
                except Exception:
                    continue
        
        return results
    
    async def _extract_with_regex(self, html_content: str) -> Dict[str, Any]:
        """Extração usando padrões regex"""
        results = {}
        
        for field, pattern in self.linkedin_patterns.items():
            try:
                matches = re.finditer(pattern, html_content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    value = match.group(1).strip()
                    if value:
                        results[field] = value
                        break
            except Exception:
                continue
        
        return results
    
    async def _extract_json_ld_data(self, html_content: str) -> Dict[str, Any]:
        """Extração de dados estruturados JSON-LD"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, dict):
                    # Mapear campos JSON-LD para nossos campos
                    field_mapping = {
                        'name': 'company_name',
                        'description': 'company_description',
                        'industry': 'industry',
                        'numberOfEmployees': 'employee_count',
                        'foundingDate': 'founded',
                        'url': 'website',
                        'address': 'headquarters'
                    }
                    
                    for json_field, our_field in field_mapping.items():
                        if json_field in data and data[json_field]:
                            results[our_field] = data[json_field]
                
            except json.JSONDecodeError:
                continue
        
        return results
    
    async def _extract_meta_tags(self, html_content: str) -> Dict[str, Any]:
        """Extração de meta tags específicas"""
        results = {}
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Meta tags relevantes
        meta_mappings = {
            'og:title': 'company_name',
            'og:description': 'company_description',
            'og:url': 'linkedin_url',
            'twitter:title': 'company_name',
            'twitter:description': 'company_description'
        }
        
        for meta_property, field in meta_mappings.items():
            meta_tag = soup.find('meta', property=meta_property) or soup.find('meta', attrs={'name': meta_property})
            if meta_tag:
                content = meta_tag.get('content')
                if content and content.strip():
                    results[field] = content.strip()
        
        return results
    
    async def _analyze_text_content(self, html_content: str) -> Dict[str, Any]:
        """Análise de texto para extrair informações contextuais"""
        results = {}
        
        # Remover HTML e analisar texto puro
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        # Padrões para análise de texto
        text_patterns = {
            'company_size_range': r'([\d,]+)\s*-\s*([\d,]+)\s*employees',
            'exact_employee_count': r'([\d,]+)\s*employees?\s*on\s*LinkedIn',
            'industry_mention': r'(?:industry|sector)\s*:?\s*([^\n\r\.]{10,100})',
            'location_mention': r'(?:based|located|headquarters)\s*(?:in|at)\s*([^\n\r\.]{5,50})',
            'founded_mention': r'(?:founded|established|started)\s*(?:in|on)?\s*([\d]{4})',
            'specialties_mention': r'specialties\s*:?\s*([^\n\r]{20,200})'
        }
        
        for pattern_name, pattern in text_patterns.items():
            try:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    value = match.group(1).strip()
                    if value and len(value) > 2:
                        results[pattern_name] = value
                        break
            except Exception:
                continue
        
        return results
    
    async def _consolidate_linkedin_data(self, results: Dict[str, Dict[str, Any]], linkedin_url: str) -> Dict[str, Any]:
        """Consolida todos os dados extraídos do LinkedIn"""
        consolidated = {
            'linkedin_url': linkedin_url,
            'company_name': None,
            'description': None,
            'industry': None,
            'company_size': None,
            'employee_count': None,
            'headquarters': None,
            'founded': None,
            'website': None,
            'specialties': None,
            'follower_count': None,
            'extraction_summary': {
                'methods_used': len(results),
                'successful_extractions': 0,
                'data_quality_score': 0
            }
        }
        
        # Prioridade de fontes (mais confiável primeiro)
        source_priority = ['json_ld_extraction', 'css_extraction', 'meta_tags_extraction', 'regex_extraction', 'text_analysis']
        
        # Mapear campos de diferentes fontes
        field_mappings = {
            'company_name': ['company_name', 'name'],
            'description': ['company_description', 'description'],
            'industry': ['industry', 'industry_text', 'industry_mention'],
            'company_size': ['company_size', 'employee_count', 'company_size_range', 'exact_employee_count'],
            'employee_count': ['employee_count', 'exact_employee_count', 'company_size'],
            'headquarters': ['headquarters', 'headquarters_text', 'location_mention'],
            'founded': ['founded', 'founded_year', 'founded_mention'],
            'website': ['website'],
            'specialties': ['specialties', 'specialties_mention'],
            'follower_count': ['follower_count']
        }
        
        # Consolidar dados por prioridade
        for field, possible_keys in field_mappings.items():
            for source in source_priority:
                if source in results:
                    source_data = results[source]
                    for key in possible_keys:
                        if key in source_data and source_data[key]:
                            value = source_data[key]
                            if isinstance(value, str):
                                value = value.strip()
                                if len(value) > 2:  # Valor válido
                                    consolidated[field] = value
                                    consolidated['extraction_summary']['successful_extractions'] += 1
                                    break
                    if consolidated[field]:  # Se encontrou valor, parar busca
                        break
        
        # Calcular score de qualidade dos dados
        total_fields = len([k for k in consolidated.keys() if k != 'extraction_summary'])
        filled_fields = len([v for k, v in consolidated.items() if k != 'extraction_summary' and v])
        consolidated['extraction_summary']['data_quality_score'] = (filled_fields / total_fields) * 100 if total_fields > 0 else 0
        
        return consolidated
    
    def is_linkedin_company_url(self, url: str) -> bool:
        """Verifica se a URL é de uma página de empresa do LinkedIn"""
        if not url:
            return False
            
        url_lower = url.lower()
        return (
            'linkedin.com/company/' in url_lower or
            'linkedin.com/in/' in url_lower or
            'linkedin.com/pub/' in url_lower
        )
    
    def extract_company_slug(self, linkedin_url: str) -> Optional[str]:
        """Extrai o slug da empresa da URL do LinkedIn"""
        try:
            if '/company/' in linkedin_url:
                return linkedin_url.split('/company/')[1].split('/')[0].split('?')[0]
            elif '/in/' in linkedin_url:
                return linkedin_url.split('/in/')[1].split('/')[0].split('?')[0]
            return None
        except Exception:
            return None