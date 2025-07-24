import os
import requests
import logging
import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page
from .log_service import LogService
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re

class BraveSearchRateLimiter:
    """Rate limiter para API do Brave Search"""
    
    def __init__(self, requests_per_second: float = 1.0, requests_per_month: int = 2000):
        self.requests_per_second = requests_per_second
        self.requests_per_month = requests_per_month
        self.last_request_time = 0
        self.monthly_count_file = 'logs/brave_monthly_count.json'
        self._ensure_log_directory()
        
    def _ensure_log_directory(self):
        """Garante que o diretório de logs existe"""
        os.makedirs('logs', exist_ok=True)
        
    def _get_monthly_count(self) -> Dict[str, Any]:
        """Obtém contagem mensal de requisições"""
        try:
            if os.path.exists(self.monthly_count_file):
                with open(self.monthly_count_file, 'r') as f:
                    data = json.load(f)
                    
                # Verifica se é um novo mês
                current_month = datetime.now().strftime('%Y-%m')
                if data.get('month') != current_month:
                    return {'month': current_month, 'count': 0}
                    
                return data
            else:
                current_month = datetime.now().strftime('%Y-%m')
                return {'month': current_month, 'count': 0}
        except Exception:
            current_month = datetime.now().strftime('%Y-%m')
            return {'month': current_month, 'count': 0}
            
    def _save_monthly_count(self, data: Dict[str, Any]):
        """Salva contagem mensal de requisições"""
        try:
            with open(self.monthly_count_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logging.warning(f"Erro ao salvar contagem mensal: {e}")
            
    async def wait_if_needed(self) -> bool:
        """Aguarda se necessário para respeitar rate limits. Retorna False se limite mensal atingido."""
        # Verificar limite mensal
        monthly_data = self._get_monthly_count()
        if monthly_data['count'] >= self.requests_per_month:
            logging.warning(f"Limite mensal de {self.requests_per_month} requisições atingido")
            return False
            
        # Verificar limite por segundo
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            logging.info(f"Rate limiting: aguardando {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            
        self.last_request_time = time.time()
        
        # Incrementar contador mensal
        monthly_data['count'] += 1
        self._save_monthly_count(monthly_data)
        
        return True

class EnrichmentService:
    def __init__(self):
        load_dotenv()
        self.brave_token = os.getenv('BRAVE_SEARCH_TOKEN')
        self.logger = logging.getLogger(__name__)
        self.log_service = LogService()
        self.rate_limiter = BraveSearchRateLimiter()
        
        if not self.brave_token:
            raise ValueError("BRAVE_SEARCH_TOKEN não encontrado no arquivo .env")

    async def enrich_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enriquece dados da empresa usando múltiplas fontes com estratégia híbrida"""
        self.log_service.log_debug("Starting enrichment with hybrid strategy", {"company_data": company_data})
        
        try:
            # Estratégia híbrida: Priorizar LinkedIn encontrado no site
            if company_data.get('linkedin_url'):
                # Caso 1: LinkedIn URL fornecida diretamente
                result = await self._scrape_linkedin_company(company_data['linkedin_url'])
            elif company_data.get('domain'):
                # Caso 2: Busca por domínio - ESTRATÉGIA HÍBRIDA
                result = await self._enrich_by_domain_hybrid(company_data)
            elif company_data.get('name'):
                # Caso 3: Busca por nome da empresa
                result = await self._search_company_with_brave(
                    company_data['name'],
                    region=company_data.get('region'),
                    country=company_data.get('country')
                )
            else:
                raise ValueError("Necessário fornecer nome da empresa, domínio ou URL do LinkedIn")
            
            # Enriquecimento adicional sempre executado
            result = await self._add_website_enrichment(result, company_data)
            
            return result
        
        except Exception as e:
            self.log_service.log_debug("Error during enrichment", {"error": str(e)})
            raise ValueError(str(e))

class PersonEnrichmentService:
    def __init__(self):
        load_dotenv()
        self.brave_token = os.getenv('BRAVE_SEARCH_TOKEN')
        self.logger = logging.getLogger(__name__)
        self.log_service = LogService()
        self.rate_limiter = BraveSearchRateLimiter()
        
        if not self.brave_token:
            raise ValueError("BRAVE_SEARCH_TOKEN não encontrado no arquivo .env")
    
    async def enrich_person(self, **kwargs) -> Dict[str, Any]:
        """
        Enriquece dados de pessoa usando múltiplas estratégias
        """
        self.log_service.log_debug("Starting person enrichment", {"params": kwargs})
        
        strategies = [
            self._enrich_by_linkedin_url,
            self._enrich_by_email,
            self._enrich_by_name_company,
            self._enrich_by_phone,
            self._enrich_by_general_search
        ]
        
        for strategy in strategies:
            try:
                self.log_service.log_debug(f"Trying strategy: {strategy.__name__}", {})
                result = await strategy(kwargs)
                if result and result.get('confidence_score', 0) > 0.6:
                    self.log_service.log_debug(f"Strategy {strategy.__name__} successful", {
                        "confidence_score": result.get('confidence_score'),
                        "name": result.get('full_name')
                    })
                    return result
            except Exception as e:
                self.log_service.log_debug(f"Strategy {strategy.__name__} failed", {"error": str(e)})
                continue
        
        return self._create_empty_result()
    
    async def _enrich_by_linkedin_url(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 1: LinkedIn URL direto"""
        linkedin_url = data.get('linkedin_url')
        if not linkedin_url:
            return None
            
        # Usar Playwright para scraping do LinkedIn
        person_data = await self._scrape_linkedin_person(linkedin_url)
        if person_data:
            person_data['linkedin_url'] = linkedin_url
            return self._format_person_result(person_data, source='linkedin_direct')
        return None
    
    async def _enrich_by_email(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 2: Busca por email"""
        email = data.get('email')
        if not email:
            return None
            
        # Extrair domínio do email
        domain = email.split('@')[1] if '@' in email else None
        name_part = email.split('@')[0] if '@' in email else None
        
        # Buscar no Brave: múltiplas estratégias
        search_queries = [
            f'"{email}" site:linkedin.com/in',
            f'{name_part} {domain} site:linkedin.com',
            f'{data.get("full_name", "")} {email} site:linkedin.com'
        ]
        
        return await self._search_and_scrape(search_queries, data)
    
    async def _enrich_by_name_company(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 3: Nome + Empresa"""
        full_name = data.get('full_name')
        company_name = data.get('company_name')
        
        if not full_name:
            return None
            
        search_queries = []
        
        if company_name:
            search_queries.extend([
                f'"{full_name}" "{company_name}" site:linkedin.com/in',
                f'{full_name} {company_name} linkedin',
                f'"{full_name}" {company_name} site:linkedin.com'
            ])
        
        # Adicionar busca com região se disponível
        if data.get('region'):
            search_queries.append(f'"{full_name}" {data.get("region")} site:linkedin.com/in')
        
        # Busca básica por nome
        search_queries.append(f'"{full_name}" site:linkedin.com/in')
        
        return await self._search_and_scrape(search_queries, data)
    
    async def _enrich_by_phone(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 4: Busca por telefone"""
        phone = data.get('phone')
        if not phone:
            return None
            
        # Limpar telefone para busca
        clean_phone = re.sub(r'[^0-9]', '', phone)
        
        search_queries = [
            f'"{phone}" site:linkedin.com/in',
            f'{clean_phone} site:linkedin.com',
            f'{data.get("full_name", "")} {phone} linkedin'
        ]
        
        return await self._search_and_scrape(search_queries, data)
    
    async def _enrich_by_general_search(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Estratégia 5: Busca geral"""
        full_name = data.get('full_name')
        if not full_name:
            return None
            
        search_queries = [
            f'{full_name} linkedin profile',
            f'{full_name} professional profile',
            f'{full_name} {data.get("country", "")} linkedin'
        ]
        
        return await self._search_and_scrape(search_queries, data)
    
    async def _search_and_scrape(self, search_queries: List[str], original_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Busca no Brave e scraping com Playwright"""
        for query in search_queries:
            try:
                # Buscar no Brave
                search_results = await self._brave_search_person(query)
                
                # Filtrar URLs do LinkedIn
                linkedin_urls = self._filter_linkedin_person_urls(search_results)
                
                for url in linkedin_urls[:3]:  # Testar top 3
                    person_data = await self._scrape_linkedin_person(url)
                    if person_data and self._validate_person_match(person_data, original_data):
                        person_data['linkedin_url'] = url
                        return self._format_person_result(person_data, source='brave_linkedin')
                        
            except Exception as e:
                self.log_service.log_debug(f"Search query failed: {query}", {"error": str(e)})
                continue
        
        return None
    
    async def _brave_search_person(self, query: str) -> List[Dict[str, Any]]:
        """Busca no Brave Search para pessoas com rate limiting"""
        try:
            # Verificar rate limiting
            if not await self.rate_limiter.wait_if_needed():
                self.log_service.log_debug("Brave search skipped - monthly limit reached", {"query": query})
                return []
                
            headers = {
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip',
                'X-Subscription-Token': self.brave_token
            }
            
            params = {
                'q': query,
                'count': 10,
                'offset': 0,
                'mkt': 'pt-BR',
                'safesearch': 'moderate',
                'textDecorations': False,
                'textFormat': 'Raw'
            }
            
            response = requests.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_service.log_debug("Brave search successful", {
                    "query": query,
                    "results_count": len(data.get('web', {}).get('results', []))
                })
                return data.get('web', {}).get('results', [])
            elif response.status_code == 429:
                self.log_service.log_debug("Brave search rate limited by API", {
                    "status_code": response.status_code,
                    "query": query
                })
                # Aguardar mais tempo em caso de rate limiting da API
                await asyncio.sleep(60)  # Aguardar 1 minuto
                return []
            else:
                self.log_service.log_debug("Brave search failed", {
                    "status_code": response.status_code,
                    "query": query
                })
                return []
                
        except Exception as e:
            self.log_service.log_debug("Brave search error", {"error": str(e), "query": query})
            return []
    
    def _filter_linkedin_person_urls(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Filtra URLs de perfis pessoais do LinkedIn"""
        linkedin_urls = []
        
        for result in search_results:
            url = result.get('url', '')
            if ('linkedin.com/in/' in url and 
                '/company/' not in url and
                '/school/' not in url and
                '/jobs/' not in url):
                linkedin_urls.append(url)
        
        return linkedin_urls
    
    async def _scrape_linkedin_person(self, linkedin_url: str) -> Optional[Dict[str, Any]]:
        """Scraping de perfil pessoal do LinkedIn usando Playwright"""
        try:
            self.log_service.log_debug("Starting LinkedIn person scraping", {"url": linkedin_url})
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-images',
                        '--disable-plugins',
                        '--disable-extensions'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Navegar para o perfil
                await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                
                # Extrair conteúdo da página
                page_content = await page.content()
                await browser.close()
                
                # Parse do HTML
                soup = BeautifulSoup(page_content, 'html.parser')
                
                # Seletores para dados de pessoa no LinkedIn
                extracted_data = {
                    'name': self._extract_person_name(soup),
                    'headline': self._extract_person_headline(soup),
                    'location': self._extract_person_location(soup),
                    'current_company': self._extract_current_company(soup),
                    'current_title': self._extract_current_title(soup),
                    'profile_image': self._extract_profile_image(soup),
                    'connections': self._extract_connections(soup),
                    'skills': self._extract_skills(soup),
                    'experience': self._extract_experience(soup),
                    'education': self._extract_education(soup)
                }
                
                self.log_service.log_debug("LinkedIn scraping completed", {
                    "name": extracted_data.get('name'),
                    "headline": extracted_data.get('headline')
                })
                
                return extracted_data
                
        except Exception as e:
            self.log_service.log_debug("LinkedIn scraping failed", {"error": str(e), "url": linkedin_url})
            return None
    
    def _extract_person_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai nome da pessoa"""
        selectors = [
            'h1.text-heading-xlarge',
            '.pv-text-details__left-panel h1',
            '.top-card-layout__title',
            'h1[data-generated-suggestion-target]',
            '.pv-top-card--list li:first-child'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_person_headline(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai headline/título profissional"""
        selectors = [
            '.text-body-medium.break-words',
            '.pv-text-details__left-panel .text-body-medium',
            '.top-card-layout__headline',
            '.pv-top-card--list li:nth-child(2)'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_person_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai localização"""
        selectors = [
            '.text-body-small.inline.t-black--light.break-words',
            '.pv-text-details__left-panel .text-body-small',
            '.top-card-layout__first-subline',
            '.pv-top-card--list-bullet li'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_current_company(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai empresa atual"""
        selectors = [
            '.pv-text-details__right-panel .hoverable-link-text',
            '.experience-item__title',
            '.pv-entity__company-summary-info h3',
            '.pv-top-card-v2-section__entity-name'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_current_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai cargo atual"""
        selectors = [
            '.experience-item__subtitle',
            '.pv-entity__secondary-title',
            '.pv-top-card-v2-section__info h2'
        ]
        return self._safe_extract_text(soup, selectors)
    
    def _extract_profile_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai URL da foto de perfil"""
        try:
            img_selectors = [
                '.pv-top-card-profile-picture__image',
                '.profile-photo-edit__preview',
                '.presence-entity__image'
            ]
            
            for selector in img_selectors:
                img = soup.select_one(selector)
                if img:
                    src = img.get('src')
                    if src and 'http' in src:
                        return src
            return None
        except:
            return None
    
    def _extract_connections(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai número de conexões"""
        selectors = [
            '.pv-top-card--list-bullet li',
            '.t-black--light.t-normal',
            '.pv-top-card-v2-section__connections'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if 'conexões' in text.lower() or 'connections' in text.lower():
                    return text
        return None
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[str]:
        """Extrai habilidades"""
        skills = []
        try:
            skill_selectors = [
                '.pv-skill-category-entity__name',
                '.skill-category-entity__name',
                '.pv-skill-entity__skill-name'
            ]
            
            for selector in skill_selectors:
                elements = soup.select(selector)
                for element in elements:
                    skill = element.get_text(strip=True)
                    if skill and skill not in skills:
                        skills.append(skill)
            
            return skills[:10]  # Limitar a 10 skills
        except:
            return []
    
    def _extract_experience(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai experiência profissional"""
        experience = []
        try:
            exp_sections = soup.select('.pv-profile-section__card-item-v2, .experience-item')
            
            for section in exp_sections[:5]:  # Limitar a 5 experiências
                company = self._safe_extract_text(section, ['.pv-entity__secondary-title', '.experience-item__subtitle'])
                title = self._safe_extract_text(section, ['.pv-entity__summary-info h3', '.experience-item__title'])
                duration = self._safe_extract_text(section, ['.pv-entity__date-range', '.experience-item__duration'])
                
                if company or title:
                    experience.append({
                        'company': company or 'Unknown',
                        'title': title or 'Unknown',
                        'duration': duration or 'Unknown'
                    })
            
            return experience
        except:
            return []
    
    def _extract_education(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai educação"""
        education = []
        try:
            edu_sections = soup.select('.pv-profile-section__card-item-v2, .education-item')
            
            for section in edu_sections[:3]:  # Limitar a 3 educações
                institution = self._safe_extract_text(section, ['.pv-entity__school-name', '.education-item__school'])
                degree = self._safe_extract_text(section, ['.pv-entity__degree-name', '.education-item__degree'])
                duration = self._safe_extract_text(section, ['.pv-entity__dates', '.education-item__duration'])
                
                if institution:
                    education.append({
                        'institution': institution,
                        'degree': degree or 'Unknown',
                        'duration': duration or 'Unknown'
                    })
            
            return education
        except:
            return []
    
    def _validate_person_match(self, person_data: Dict[str, Any], original_data: Dict[str, Any]) -> bool:
        """Valida se os dados extraídos correspondem à pessoa buscada"""
        if not person_data.get('name'):
            return False
        
        extracted_name = person_data.get('name', '').lower()
        
        # Verificar nome completo
        if original_data.get('full_name'):
            search_name = original_data['full_name'].lower()
            # Verificar se pelo menos 70% do nome bate
            name_parts = search_name.split()
            matches = sum(1 for part in name_parts if part in extracted_name)
            if matches / len(name_parts) < 0.7:
                return False
        
        # Verificar empresa se fornecida
        if original_data.get('company_name'):
            search_company = original_data['company_name'].lower()
            extracted_company = person_data.get('current_company', '').lower()
            if search_company not in extracted_company and extracted_company not in search_company:
                return False
        
        return True
    
    def _calculate_confidence_score(self, person_data: Dict[str, Any]) -> float:
        """Calcula score de confiança dos dados"""
        score = 0.0
        
        # Nome (peso 30%)
        if person_data.get('name') and person_data['name'] != 'Unknown':
            score += 0.3
        
        # Headline/título (peso 20%)
        if person_data.get('headline') and person_data['headline'] != 'Unknown':
            score += 0.2
        
        # Empresa atual (peso 20%)
        if person_data.get('current_company') and person_data['current_company'] != 'Unknown':
            score += 0.2
        
        # Localização (peso 10%)
        if person_data.get('location') and person_data['location'] != 'Unknown':
            score += 0.1
        
        # Experiência (peso 10%)
        if person_data.get('experience') and len(person_data['experience']) > 0:
            score += 0.1
        
        # Educação (peso 5%)
        if person_data.get('education') and len(person_data['education']) > 0:
            score += 0.05
        
        # Skills (peso 5%)
        if person_data.get('skills') and len(person_data['skills']) > 0:
            score += 0.05
        
        return min(score, 1.0)
    
    def _format_person_result(self, person_data: Dict[str, Any], source: str = 'unknown') -> Dict[str, Any]:
        """Formatar resultado final"""
        if not person_data:
            return self._create_empty_result()
        
        # Dividir nome em primeiro e último nome
        full_name = person_data.get('name', 'Unknown')
        name_parts = full_name.split() if full_name != 'Unknown' else []
        first_name = name_parts[0] if name_parts else 'Unknown'
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Unknown'
        
        # Extrair localização
        location = person_data.get('location', 'Unknown')
        location_parts = location.split(',') if location != 'Unknown' else []
        city = location_parts[0].strip() if location_parts else 'Unknown'
        region = location_parts[1].strip() if len(location_parts) > 1 else 'Unknown'
        country = location_parts[-1].strip() if len(location_parts) > 2 else 'Unknown'
        
        result = {
            'full_name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'headline': person_data.get('headline', 'Unknown'),
            'current_company': person_data.get('current_company', 'Unknown'),
            'current_title': person_data.get('current_title', 'Unknown'),
            'location': location,
            'city': city,
            'region': region,
            'country': country,
            'linkedin_url': person_data.get('linkedin_url', ''),
            'profile_image': person_data.get('profile_image', ''),
            'connections': person_data.get('connections', 'Unknown'),
            'skills': person_data.get('skills', []),
            'experience': person_data.get('experience', []),
            'education': person_data.get('education', []),
            'social_media': [],  # Pode ser expandido futuramente
            'confidence_score': self._calculate_confidence_score(person_data),
            'data_source': source,
            'last_updated': datetime.now().isoformat()
        }
        
        return result
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """Cria resultado vazio quando nenhuma estratégia funciona"""
        return {
            'full_name': 'Unknown',
            'first_name': 'Unknown',
            'last_name': 'Unknown',
            'headline': 'Unknown',
            'current_company': 'Unknown',
            'current_title': 'Unknown',
            'location': 'Unknown',
            'city': 'Unknown',
            'region': 'Unknown',
            'country': 'Unknown',
            'linkedin_url': '',
            'profile_image': '',
            'connections': 'Unknown',
            'skills': [],
            'experience': [],
            'education': [],
            'social_media': [],
            'confidence_score': 0.0,
            'data_source': 'none',
            'last_updated': datetime.now().isoformat(),
            'error': 'Não foi possível encontrar dados para esta pessoa'
        }
    
    async def _safe_extract_text_async(self, page: Page, selector: str) -> Optional[str]:
        """Extrai texto de um elemento de forma segura (versão assíncrona para Playwright)"""
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                return text.strip() if text else None
        except Exception as e:
            self.log_service.log_debug(f"Could not extract text from selector {selector}: {str(e)}", {})
        return None

    def _safe_extract_text(self, soup_or_element, selectors: List[str]) -> Optional[str]:
        """Extrai texto de forma segura usando múltiplos seletores (versão síncrona para BeautifulSoup)"""
        for selector in selectors:
            try:
                element = soup_or_element.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and text.lower() not in ['unknown', 'n/a', '-', '']:
                        return text
            except:
                continue
        return None

    async def _enrich_by_domain_hybrid(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estratégia híbrida para enriquecimento por domínio"""
        try:
            domain = company_data['domain']
            self.log_service.log_debug("Starting hybrid domain enrichment", {"domain": domain})
            
            # FASE 1: Tentar encontrar LinkedIn no site da empresa
            website_url = domain if domain.startswith(('http://', 'https://')) else f'https://{domain}'
            
            try:
                self.log_service.log_debug("Phase 1: Scraping website for LinkedIn URLs", {"website_url": website_url})
                website_data = await self._scrape_company_website(website_url)
                
                # Procurar URLs do LinkedIn nas redes sociais encontradas
                linkedin_url = self._extract_linkedin_from_social_media(website_data)
                
                if linkedin_url:
                    self.log_service.log_debug("LinkedIn URL found on website, using it directly", {"linkedin_url": linkedin_url})
                    
                    # Usar a URL do LinkedIn encontrada no site
                    result = await self._scrape_linkedin_company(linkedin_url)
                    
                    # Verificar se o scraping foi bem-sucedido com critérios mais rigorosos
                    if (result and 
                        not result.get('error') and 
                        result.get('name') and 
                        result.get('name') != 'Unknown' and 
                        result.get('name').strip() != ''):
                        
                        self.log_service.log_debug("LinkedIn scraping successful, merging with website data", {
                            "company_name": result.get('name'),
                            "linkedin_url": linkedin_url
                        })
                        
                        # Mesclar com dados do site e retornar imediatamente
                        result = self._merge_website_data(result, website_data)
                        
                        # Adicionar informação sobre a fonte dos dados
                        result['data_source'] = 'website_linkedin'
                        result['linkedin_source'] = 'found_on_website'
                        
                        return result
                    else:
                        self.log_service.log_debug("LinkedIn scraping failed or returned invalid data", {
                            "result_name": result.get('name') if result else None,
                            "has_error": result.get('error') if result else None
                        })
                else:
                    self.log_service.log_debug("No LinkedIn URL found on website", {})
                    
            except Exception as e:
                self.log_service.log_debug("Website scraping failed", {"error": str(e)})
                website_data = None
            
            # FASE 2: Fallback para busca do Brave (apenas se a Fase 1 falhou)
            self.log_service.log_debug("Phase 2: Using Brave search as fallback", {})
            result = await self._search_company_with_brave(
                domain,
                region=company_data.get('region'),
                country=company_data.get('country')
            )
            
            # Se temos dados do site da Fase 1, mesclar com resultado do Brave
            if website_data and result:
                result = self._merge_website_data(result, website_data)
            
            # Adicionar informação sobre a fonte dos dados
            if result:
                result['data_source'] = 'brave_search'
                result['linkedin_source'] = 'brave_search'
            
            return result
            
        except Exception as e:
            self.log_service.log_debug("Error during enrichment", {"error": str(e)})
            raise ValueError(str(e))

    async def _find_linkedin_on_website(self, website_url: str) -> Optional[str]:
        """Busca URL do LinkedIn no site da empresa"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-images',
                        '--disable-plugins',
                        '--disable-extensions'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Navegar para o site com timeout reduzido
                await page.goto(website_url, wait_until="domcontentloaded", timeout=10000)
                await page.wait_for_timeout(1000)
                
                # Buscar links do LinkedIn
                linkedin_selectors = [
                    'a[href*="linkedin.com/company"]',
                    'a[href*="linkedin.com/in"]',
                    'a[href*="linkedin.com"]'
                ]
                
                for selector in linkedin_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            href = await element.get_attribute('href')
                            if href and '/company/' in href:
                                await browser.close()
                                return href
                    except:
                        continue
                
                await browser.close()
                return None
                
        except Exception as e:
            self.log_service.log_debug("Error finding LinkedIn on website", {"error": str(e)})
            return None

    async def _add_website_enrichment(self, result: Dict[str, Any], company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona enriquecimento do site se ainda não foi feito"""
        # Se já tem dados do site, não precisa fazer novamente
        if result.get('company_history') or result.get('social_media'):
            return result
            
        # Tentar enriquecimento adicional
        website_url = result.get('website') or company_data.get('domain')
        if website_url and not result.get('error'):
            if not website_url.startswith(('http://', 'https://')):
                website_url = f'https://{website_url}'
            
            try:
                website_data = await self._scrape_company_website(website_url)
                if website_data:
                    result = self._merge_website_data(result, website_data)
            except Exception as e:
                self.log_service.log_debug("Additional website enrichment failed", {"error": str(e)})
        
        return result

    async def _scrape_linkedin_company(self, linkedin_url: str) -> Dict[str, Any]:
        """Faz scraping da página da empresa no LinkedIn usando Playwright - OTIMIZADO"""
        self.log_service.log_debug("Starting optimized LinkedIn scraping", {"linkedin_url": linkedin_url})
        
        try:
            self.log_service.log_debug("Initializing Playwright", {})
            async with async_playwright() as p:
                self.log_service.log_debug("Launching browser", {})
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-images',     # Acelera carregamento
                        '--disable-css',     # Remove CSS desnecessário
                        '--disable-plugins', # Remove plugins
                        '--disable-extensions' # Remove extensões
                    ]
                )
                
                self.log_service.log_debug("Browser launched successfully, creating context", {})
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US'
                )
                
                self.log_service.log_debug("Context created, opening new page", {})
                page = await context.new_page()
                
                self.log_service.log_debug("Navigating to URL", {"url": linkedin_url})
                # Timeout reduzido para 10 segundos
                await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=10000)
                self.log_service.log_debug("Page loaded successfully", {})
                
                # Aguarda apenas 500ms para conteúdo básico carregar
                self.log_service.log_debug("Waiting for content to load", {})
                await page.wait_for_timeout(500)
                
                # Verificar se a página carregou corretamente
                page_title = await page.title()
                self.log_service.log_debug("Page title obtained", {"title": page_title})
                
                # Verificar se não foi redirecionado para login
                current_url = page.url
                if "authwall" in current_url or "login" in current_url:
                    self.log_service.log_debug("Redirected to login page", {"current_url": current_url})
                    await browser.close()
                    return self._get_default_company_data(linkedin_url, "Redirected to login")
                
                self.log_service.log_debug("Starting data extraction", {})
                # Extração otimizada e paralela
                company_data = await self._extract_company_data_optimized(page)
                company_data['linkedin'] = linkedin_url
                
                self.log_service.log_debug("Closing browser", {})
                await browser.close()
                
                self.log_service.log_debug("Successfully scraped company", {"company_name": company_data.get('name', 'Unknown')})
                return company_data
                
        except Exception as e:
            self.log_service.log_debug("Error scraping LinkedIn page", {
                "error": str(e),
                "exception_type": type(e).__name__
            })
            import traceback
            self.log_service.log_debug("Full traceback", {"traceback": traceback.format_exc()})
            return self._get_default_company_data(linkedin_url, str(e))

    async def _extract_company_data_optimized(self, page: Page) -> Dict[str, Any]:
        """Extrai dados da empresa de forma otimizada com execução paralela"""
        try:
            self.log_service.log_debug("Starting optimized company data extraction", {})
            
            # Aguarda apenas elementos essenciais com timeout muito reduzido
            essential_selectors = [
                'h1[data-test-id="org-top-card-summary-info-list__title"]',
                'h1.org-top-card-summary__title',
                'h1'
            ]
            
            try:
                await page.wait_for_selector(','.join(essential_selectors), timeout=2000)
                self.log_service.log_debug("Essential selectors found", {})
            except:
                self.log_service.log_debug("Essential selectors not found, continuing anyway", {})
            
            # Extração paralela de todos os campos
            self.log_service.log_debug("Starting parallel data extraction", {})
            tasks = [
                self._extract_name_parallel(page),
                self._extract_description_parallel(page),
                self._extract_industry_parallel(page),
                self._extract_size_parallel(page),
                self._extract_website_parallel(page),
                self._extract_headquarters_parallel(page),
                self._extract_founded_parallel(page)
            ]
            
            # ✅ CORREÇÃO: Aumentar timeout para 10 segundos
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=10.0  # Aumentado de 5 para 10 segundos
            )
            
            name, description, industry, size_raw, website, headquarters_raw, founded_raw = results
            self.log_service.log_debug("Parallel extraction completed", {
                "name": name,
                "description_length": len(description) if description else 0,
                "industry": industry,
                "headquarters_raw": headquarters_raw
            })
            
            # Processamento rápido dos dados extraídos
            size = self._clean_field_text(size_raw, ['Company size\n', 'Company size', 'Tamanho da empresa\n', 'Tamanho da empresa'])
            headquarters = self._clean_field_text(headquarters_raw, ['Headquarters\n', 'Headquarters', 'Sede\n', 'Sede'])
            founded = self._clean_field_text(founded_raw, ['Founded\n', 'Founded', 'Fundada em\n', 'Fundada em'])
            
            self.log_service.log_debug("Extracted headquarters", {"headquarters": headquarters})
            
            # ✅ CORREÇÃO: Adicionar logs de debug e tratamento de erro específico
            location_data = {
                "country": None, 
                "country_code": None, 
                "region": None, 
                "region_code": None,
                "city": None,
                "country_dial_code": None
            }
            
            if headquarters:
                try:
                    self.log_service.log_debug("Starting location extraction", {"headquarters": headquarters})
                    location_data = await self._extract_location_data(headquarters)
                    self.log_service.log_debug("Location data extracted successfully", location_data)
                except Exception as location_error:
                    self.log_service.log_debug("Error during location extraction", {
                        "error": str(location_error),
                        "headquarters": headquarters
                    })
            else:
                self.log_service.log_debug("No headquarters data available for location extraction", {})
            
            result = {
                "name": name or "Unknown",
                "website": website,
                "description": description,
                "industry": industry,
                "size": size,
                "founded": founded,
                "headquarters": headquarters,
                "linkedin": None,
                "country": location_data["country"],
                "country_code": location_data["country_code"],
                "region": location_data["region"],
                "region_code": location_data["region_code"],
                "city": location_data["city"],
                "country_dial_code": location_data["country_dial_code"],
                "employees": [],
                "social_media": []
            }
            
            self.log_service.log_debug("Final result with location data", result)
            self.log_service.log_debug("Optimized company data extraction completed", {})
            
            return result
            
        except asyncio.TimeoutError:
            self.log_service.log_debug("Timeout during data extraction, returning partial data", {})
            return self._get_default_company_data()
        except Exception as e:
            self.log_service.log_debug("Error extracting company data", {"error": str(e)})
            return self._get_default_company_data()

    # Funções de extração paralela otimizadas
    async def _extract_name_parallel(self, page: Page) -> Optional[str]:
        """Extrai nome da empresa de forma otimizada"""
        selectors = [
            'h1[data-test-id="org-top-card-summary-info-list__title"]',
            'h1.org-top-card-summary__title',
            'h1.top-card-layout__title',
            'h1'
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None

    async def _extract_description_parallel(self, page: Page) -> Optional[str]:
        """Extrai descrição da empresa de forma otimizada"""
        selectors = [
            '[data-test-id="about-us__description"]',
            '.org-about-us__description',
            '.break-words'
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None

    async def _extract_industry_parallel(self, page: Page) -> Optional[str]:
        """Extrai indústria da empresa de forma otimizada"""
        selectors = [
            '[data-test-id="about-us__industry"]',
            '.org-about-us__industry'
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None

    async def _extract_size_parallel(self, page: Page) -> Optional[str]:
        """Extrai tamanho da empresa de forma otimizada"""
        selectors = [
            '[data-test-id="about-us__size"]',
            '.org-about-us__company-size'
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None

    async def _extract_website_parallel(self, page: Page) -> Optional[str]:
        """Extrai website da empresa de forma otimizada"""
        selectors = [
            '[data-test-id="about-us__website"] a',
            '.org-about-us__website a'
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    href = await element.get_attribute('href')
                    if href and href.strip():
                        # Resolver URL de redirect do LinkedIn
                        resolved_url = await self._resolve_linkedin_redirect(href.strip())
                        return resolved_url
            except:
                continue
        return None

    async def _resolve_linkedin_redirect(self, linkedin_url: str) -> str:
        """Resolve URLs de redirect do LinkedIn para obter a URL real"""
        try:
            # Verifica se é uma URL de redirect do LinkedIn
            if 'linkedin.com/redir/redirect' in linkedin_url:
                # Extrai a URL real do parâmetro 'url'
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(linkedin_url)
                query_params = parse_qs(parsed.query)
                
                if 'url' in query_params:
                    real_url = query_params['url'][0]
                    # Decodifica a URL
                    import urllib.parse
                    decoded_url = urllib.parse.unquote(real_url)
                    return decoded_url
            
            # Se não for redirect, retorna a URL original
            return linkedin_url
            
        except Exception as e:
            self.log_service.log_debug("Error resolving LinkedIn redirect", {"error": str(e)})
            return linkedin_url

    async def _extract_headquarters_parallel(self, page: Page) -> Optional[str]:
        """Extrai sede da empresa de forma otimizada"""
        # Seletores baseados na estrutura real do LinkedIn
        selectors = [
            '[data-test-id="about-us__headquarters"]',
            '.org-about-us__headquarters',
            '[data-test-id="org-about-us__headquarters"]',
            # Novos seletores baseados na estrutura encontrada
            'dt:has-text("Sede") + dd',
            'dt:has-text("Headquarters") + dd',
            '.org-about-company-module__company-details dt:has-text("Sede") + dd',
            '.org-about-company-module__company-details dt:has-text("Headquarters") + dd'
        ]
        
        self.log_service.log_debug("Starting headquarters extraction with updated selectors", {})
        
        for i, selector in enumerate(selectors):
            try:
                self.log_service.log_debug(f"Trying selector {i+1}/{len(selectors)}: {selector}", {})
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        clean_text = text.strip()
                        self.log_service.log_debug(f"Found headquarters with selector {selector}: {clean_text}", {})
                        return clean_text
            except Exception as e:
                self.log_service.log_debug(f"Error with selector {selector}: {str(e)}", {})
                continue
        
        # Fallback melhorado - buscar na estrutura de definições
        try:
            self.log_service.log_debug("Trying fallback approach - searching in definition lists", {})
            
            # Buscar por elementos dt/dd que contenham informações de sede
            dt_elements = await page.query_selector_all('dt')
            for dt in dt_elements:
                try:
                    dt_text = await dt.inner_text()
                    if dt_text and ('Sede' in dt_text or 'Headquarters' in dt_text):
                        # Encontrar o dd correspondente
                        dd = await dt.query_selector('xpath=following-sibling::dd[1]')
                        if dd:
                            dd_text = await dd.inner_text()
                            if dd_text and dd_text.strip():
                                clean_text = dd_text.strip()
                                self.log_service.log_debug(f"Found headquarters via dt/dd: {clean_text}", {})
                                return clean_text
                except:
                    continue
            
            # Fallback adicional - buscar por texto específico
            self.log_service.log_debug("Trying text-based search fallback", {})
            headquarters_elements = await page.query_selector_all('text=/Headquarters|Sede/i')
            for element in headquarters_elements[:3]:  # Limitar a 3 elementos
                try:
                    parent = await element.query_selector('..')
                    if parent:
                        parent_text = await parent.inner_text()
                        if parent_text and len(parent_text.strip()) > 5:
                            # Limpar o texto
                            clean_text = parent_text.replace('Headquarters', '').replace('Sede', '').strip()
                            if clean_text and len(clean_text) > 3 and len(clean_text) < 100:
                                self.log_service.log_debug(f"Found headquarters via text search: {clean_text}", {})
                                return clean_text
                except:
                    continue
                
        except Exception as e:
            self.log_service.log_debug(f"Error in fallback approach: {str(e)}", {})
        
        self.log_service.log_debug("No headquarters information found with any method", {})
        return None

    async def _extract_founded_parallel(self, page: Page) -> Optional[str]:
        """Extrai ano de fundação da empresa de forma otimizada"""
        selectors = [
            '[data-test-id="about-us__founded"]',
            '.org-about-us__founded'
        ]
        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
            except:
                continue
        return None

    def _get_default_company_data(self, linkedin_url: str = None, error: str = None) -> Dict[str, Any]:
        """Retorna dados padrão em caso de erro"""
        data = {
            "name": "Unknown",
            "website": None,
            "description": None,
            "industry": None,
            "size": None,
            "founded": None,
            "headquarters": None,
            "country": None,
            "country_code": None,
            "region": None,
            "city": None,
            "employees": [],
            "social_media": []
        }
        
        if linkedin_url:
            data["linkedin_url"] = linkedin_url
        
        if error:
            data["error"] = f"Erro ao fazer scraping da página: {error}"
            
        return data

    async def _extract_company_data(self, page: Page) -> Dict[str, Any]:
        """Extrai dados da empresa da página do LinkedIn"""
        try:
            self.logger.info("Starting company data extraction")
            
            self.logger.info("Extracting company name...")
            
            # Aguardar elementos específicos carregarem
            try:
                await page.wait_for_selector('[data-test-id="about-us__industry"]', timeout=5000)
            except:
                pass  # Continua mesmo se não encontrar
                
            try:
                await page.wait_for_selector('[data-test-id="about-us__size"]', timeout=5000)
            except:
                pass  # Continua mesmo se não encontrar
                
            try:
                await page.wait_for_selector('[data-test-id="about-us__website"]', timeout=5000)
            except:
                pass  # Continua mesmo se não encontrar
                
            try:
                await page.wait_for_selector('[data-test-id="about-us__headquarters"]', timeout=5000)
            except:
                pass  # Continua mesmo se não encontrar
                
            try:
                await page.wait_for_selector('[data-test-id="about-us__founded"]', timeout=5000)
            except:
                pass  # Continua mesmo se não encontrar
            
            # Scroll para garantir que todo conteúdo carregue
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            # Nome da empresa - múltiplos seletores para maior compatibilidade
            name = await self._safe_extract_text_async(page, 'h1[data-test-id="org-top-card-summary-info-list__title"]') or \
                   await self._safe_extract_text_async(page, 'h1.org-top-card-summary__title') or \
                   await self._safe_extract_text_async(page, 'h1.top-card-layout__title') or \
                   await self._safe_extract_text_async(page, 'h1')
            
            self.logger.info(f"Company name extracted: {name}")
            
            # Descrição
            description = await self._safe_extract_text_async(page, '[data-test-id="about-us__description"]') or \
                         await self._safe_extract_text_async(page, '.org-about-us__description') or \
                         await self._safe_extract_text_async(page, '.break-words')
            
            # Indústria
            industry = await self._safe_extract_text_async(page, '[data-test-id="about-us__industry"]') or \
                       await self._safe_extract_text_async(page, '.org-about-us__industry')
            
            # Tamanho da empresa
            size_raw = await self._safe_extract_text_async(page, '[data-test-id="about-us__size"]') or \
                       await self._safe_extract_text_async(page, '.org-about-us__company-size')
            
            # Limpar o campo size
            size = self._clean_field_text(size_raw, ['Company size\n', 'Company size', 'Tamanho da empresa\n', 'Tamanho da empresa'])
            
            # Website
            website = await self._safe_extract_attribute(page, '[data-test-id="about-us__website"] a', 'href') or \
                     await self._safe_extract_attribute(page, '.org-about-us__website a', 'href')
            
            # Resolver URL de redirect do LinkedIn
            website = await self._resolve_linkedin_redirect(website) if website else None
            
            # Sede
            headquarters_raw = await self._safe_extract_text_async(page, '[data-test-id="about-us__headquarters"]') or \
                              await self._safe_extract_text_async(page, '.org-about-us__headquarters')
            
            # Limpar o campo headquarters
            headquarters = self._clean_field_text(headquarters_raw, ['Headquarters\n', 'Headquarters', 'Sede\n', 'Sede'])
            
            # ✅ CORREÇÃO: Extrair dados de localização com await
            location_data = await self._extract_location_data(headquarters)
            
            # Ano de fundação
            founded_raw = await self._safe_extract_text_async(page, '[data-test-id="about-us__founded"]') or \
                         await self._safe_extract_text_async(page, '.org-about-us__founded')
            
            # Limpar o campo founded
            founded = self._clean_field_text(founded_raw, ['Founded\n', 'Founded', 'Fundada em\n', 'Fundada em'])
            
            self.logger.info("Company data extraction completed")
            
            return {
                "name": name or "Unknown",
                "website": website,
                "description": description,
                "industry": industry,
                "size": size,
                "founded": founded,
                "headquarters": headquarters,
                "country": location_data["country"],
                "country_code": location_data["country_code"],
                "region": location_data["region"],
                "region_code": location_data["region_code"],
                "city": location_data["city"],
                "country_dial_code": location_data["country_dial_code"],
                "employees": [],
                "social_media": []
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting company data: {str(e)}")
            return {
                "name": "Unknown",
                "website": None,
                "description": None,
                "industry": None,
                "size": None,
                "founded": None,
                "headquarters": None,
                "country": None,
                "country_code": None,
                "region": None,
                "city": None,
                "employees": [],
                "social_media": []
            }

    async def _safe_extract_text_async(self, page: Page, selector: str) -> Optional[str]:
        """Extrai texto de um elemento de forma segura (versão assíncrona para Playwright)"""
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                return text.strip() if text else None
        except Exception as e:
            self.log_service.log_debug(f"Could not extract text from selector {selector}: {str(e)}", {})
        return None

    async def _safe_extract_attribute(self, page: Page, selector: str, attribute: str) -> Optional[str]:
        """Extrai atributo de um elemento de forma segura"""
        try:
            element = await page.query_selector(selector)
            if element:
                attr = await element.get_attribute(attribute)
                return attr.strip() if attr else None
        except Exception as e:
            self.log_service.log_debug(f"Could not extract attribute {attribute} from selector {selector}: {str(e)}", {})
        return None

    async def _search_company_with_brave(self, search_term: str, region: Optional[str] = None, country: Optional[str] = None) -> Dict[str, Any]:
        """Busca empresa usando a API do Brave Search com parâmetros otimizados e faz scraping completo se encontrar LinkedIn URL"""
        
        # ✅ Detectar se o termo de busca é um domínio
        is_domain = self._is_domain(search_term)
        
        # ✅ Obter código do país usando a API do GeoNames (se fornecido)
        country_code = None
        if country:
            self.log_service.log_debug("Obtaining country code", {"country": country})
            country_data = await self._get_country_from_geonames(country)
            if country_data:
                country_code = country_data.get('countryCode')
                self.log_service.log_debug("Found country code", {"country_code": country_code, "country": country})
            else:
                self.log_service.log_debug("Could not find country code", {"country": country})
        
        # ✅ Estratégias de busca otimizadas baseadas no tipo de entrada
        search_strategies = []
        
        if is_domain:
            # Estratégias específicas para domínios
            domain_name = self._extract_company_name_from_domain(search_term)
            
            # Estratégia 1: Busca pelo domínio exato
            search_strategies.append({
                'query': f'site:{search_term} site:linkedin.com/company',
                'country': country_code,
                'search_lang': 'pt-br' if country_code == 'BR' else 'en',
                'ui_lang': 'pt-BR' if country_code == 'BR' else 'en-US',
                'description': f'busca por domínio exato "{search_term}"'
            })
            
            # Estratégia 2: Busca pelo nome extraído do domínio + região
            if region and domain_name:
                search_strategies.append({
                    'query': f'"{domain_name}" {region} site:linkedin.com/company',
                    'country': country_code,
                    'search_lang': 'pt-br' if country_code == 'BR' else 'en',
                    'ui_lang': 'pt-BR' if country_code == 'BR' else 'en-US',
                    'description': f'busca por nome extraído "{domain_name}" com região "{region}"'
                })
            
            # Estratégia 3: Busca pelo nome extraído do domínio
            if domain_name:
                search_strategies.append({
                    'query': f'"{domain_name}" site:linkedin.com/company',
                    'country': country_code,
                    'search_lang': 'pt-br' if country_code == 'BR' else 'en',
                    'ui_lang': 'pt-BR' if country_code == 'BR' else 'en-US',
                    'description': f'busca por nome extraído "{domain_name}"'
                })
            
            # Estratégia 4: Busca pelo domínio sem extensão
            domain_without_extension = search_term.split('.')[0]
            search_strategies.append({
                'query': f'"{domain_without_extension}" site:linkedin.com/company',
                'country': country_code,
                'search_lang': 'pt-br' if country_code == 'BR' else 'en',
                'ui_lang': 'pt-BR' if country_code == 'BR' else 'en-US',
                'description': f'busca por domínio sem extensão "{domain_without_extension}"'
            })
            
        else:
            # Estratégias originais para nome da empresa
            if region:
                query = f'"{search_term}" {region} site:linkedin.com/company'
                search_strategies.append({
                    'query': query,
                    'country': country_code,
                    'search_lang': 'pt-br' if country_code == 'BR' else 'en',
                    'ui_lang': 'pt-BR' if country_code == 'BR' else 'en-US',
                    'description': f'com região "{region}" integrada na query'
                })
            
            if country_code:
                query = f'"{search_term}" site:linkedin.com/company'
                search_strategies.append({
                    'query': query,
                    'country': country_code,
                    'search_lang': 'pt-br' if country_code == 'BR' else 'en',
                    'ui_lang': 'pt-BR' if country_code == 'BR' else 'en-US',
                    'description': f'com filtro de país "{country_code}"'
                })
        
        # Estratégia final: Busca básica sem filtros (fallback)
        fallback_term = search_term if not is_domain else self._extract_company_name_from_domain(search_term) or search_term.split('.')[0]
        search_strategies.append({
            'query': f'"{fallback_term}" site:linkedin.com/company',
            'country': None,
            'search_lang': 'en',
            'ui_lang': 'en-US',
            'description': 'busca básica sem filtros (fallback)'
        })
        
        # Tenta cada estratégia em ordem de especificidade
        for i, strategy in enumerate(search_strategies, 1):
            self.log_service.log_debug(f"Tentativa {i}/{len(search_strategies)}: {strategy['description']}", {})
            self.log_service.log_debug(f"Query: {strategy['query']}", {})
            if strategy['country']:
                self.log_service.log_debug(f"Country: {strategy['country']}, Lang: {strategy['search_lang']}", {})
            
            try:
                # Verificar rate limiting
                if not await self.rate_limiter.wait_if_needed():
                    self.logger.warning(f"Brave search skipped for strategy {i} - monthly limit reached")
                    continue
                    
                # ✅ Parâmetros otimizados da API do Brave
                params = {
                    "q": strategy['query'],
                    "search_lang": strategy['search_lang'],
                    "ui_lang": strategy['ui_lang']
                }
                
                # Adiciona filtro de país se disponível
                if strategy['country']:
                    params["country"] = strategy['country']
                
                # Faz a requisição para a API do Brave
                response = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "x-subscription-token": self.brave_token
                    },
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 429:
                    self.log_service.log_debug("Rate limited by Brave API", {"strategy": i})
                    await asyncio.sleep(60)  # Aguardar 1 minuto
                    continue
                elif response.status_code != 200:
                    self.log_service.log_debug("Brave API error", {"strategy": i, "status_code": response.status_code})
                    continue
                
                data = response.json()
                
                # ✅ Sistema de pontuação melhorado
                company_url = None
                company_title = None
                company_description = None
                best_score = 0
                
                for result in data.get('web', {}).get('results', []):
                    url = result.get('url', '')
                    title = result.get('title', '')
                    description = result.get('description', '')
                    
                    if '/company/' in url:
                        score = 0
                        
                        # Pontuação base por ter /company/ na URL
                        score += 10
                        
                        if is_domain:
                            # Sistema de pontuação específico para domínios
                            domain_name = self._extract_company_name_from_domain(search_term)
                            domain_without_extension = search_term.split('.')[0]
                            
                            # Pontuação alta se o domínio aparece no resultado
                            if search_term.lower() in (title + ' ' + description).lower():
                                score += 50
                            
                            # Pontuação se o nome extraído aparece
                            if domain_name and domain_name.lower() in title.lower():
                                score += 40
                            
                            # Pontuação se o domínio sem extensão aparece
                            if domain_without_extension.lower() in title.lower():
                                score += 30
                                
                        else:
                            # Pontuação original para nomes de empresa
                            if search_term.lower() in title.lower():
                                score += 40
                            
                            if search_term.lower() in description.lower():
                                score += 20
                        
                        # Pontuação adicional se região aparece no resultado
                        if region and region.lower() in (title + ' ' + description).lower():
                            score += 25
                        
                        # Pontuação adicional se país aparece no resultado
                        if country and country.lower() in (title + ' ' + description).lower():
                            score += 15
                        
                        # Bonificação para URLs mais limpos
                        if '?' not in url:
                            score += 5
                        
                        # Bonificação para estratégias mais específicas
                        if i == 1:  # Primeira estratégia (mais específica)
                            score += 10
                        elif i == 2:  # Segunda estratégia
                            score += 5
                        
                        # Adicionar log para cada resultado avaliado
                        self.log_service.log_debug(f"Avaliando resultado", {
                            "url": url,
                            "title": title,
                            "score": score,
                            "strategy": i
                        })
                        
                        if score > best_score:
                            best_score = score
                            company_url = url
                            company_title = title
                            company_description = description
                
                # Se encontrou uma URL com pontuação razoável, tenta fazer o scraping
                if company_url and best_score >= 20:  # Threshold ajustado
                    self.log_service.log_debug(f"Encontrou URL da empresa via estratégia {i} (pontuação: {best_score}): {company_url}", {})
                    
                    # ✅ Faz scraping completo do LinkedIn
                    self.log_service.log_debug("Starting LinkedIn scraping for found URL", {"company_url": company_url})
                    scraped_data = await self._scrape_linkedin_company(company_url)
                    
                    # Se o scraping foi bem-sucedido, retorna os dados completos
                    if scraped_data and not scraped_data.get('error'):
                        self.log_service.log_debug(f"Scraping bem-sucedido usando estratégia {i} - {strategy['description']}", {})
                        return scraped_data
                    else:
                        self.log_service.log_debug(f"Scraping falhou para URL encontrada via estratégia {i}, tentando próxima estratégia", {})
                        continue
                else:
                    if company_url:
                        self.log_service.log_debug(f"URL encontrada via estratégia {i} tem pontuação baixa ({best_score}), tentando próxima estratégia", {})
                    else:
                        self.log_service.log_debug(f"Nenhuma URL encontrada via estratégia {i}, tentando próxima estratégia", {})
                    continue
                    
            except requests.Timeout:
                self.log_service.log_debug("Request timeout", {"strategy": i})
                continue
            except requests.RequestException as e:
                self.log_service.log_debug("Request error", {"strategy": i, "error": str(e)})
                continue
            except Exception as e:
                self.log_service.log_debug("Strategy error", {"strategy": i, "error": str(e)})
                continue
        
        # Se todas as estratégias falharam
        self.log_service.log_debug("All search strategies failed", {"search_term": search_term})
        return {
            "name": search_term,
            "linkedin": None,
            "website": None,
            "description": None,
            "industry": None,
            "size": None,
            "founded": None,
            "headquarters": None,
            "country": None,
            "country_code": None,
            "region": None,
            "region_code": None,
            "city": None,
            "country_dial_code": None,
            "employees": [],
            "social_media": [],
            "error": "Página da empresa no LinkedIn não encontrada"
        }

    def _extract_company_name(self, title: str, fallback: str) -> str:
        """Extrai o nome da empresa do título do resultado"""
        if not title:
            return fallback
        
        # Remove texto comum do LinkedIn
        title = title.replace(" | LinkedIn", "")
        title = title.replace(" - LinkedIn", "")
        title = title.replace(" on LinkedIn", "")
        
        # Se o título ainda contém informação útil, usa ele
        if len(title.strip()) > 0:
            return title.strip()
        
        return fallback

    async def _scrape_company_website(self, website_url: str) -> Dict[str, Any]:
        """Faz scraping do site oficial da empresa para coletar dados adicionais"""
        self.log_service.log_debug("Starting company website scraping", {"website_url": website_url})
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-web-security',
                        '--disable-images',  # Acelera carregamento
                        '--disable-plugins',
                        '--disable-extensions'
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Navegar para o site da empresa
                await page.goto(website_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)  # Aguarda carregamento
                
                # Extração paralela de dados do site
                tasks = [
                    self._extract_social_media_links(page),
                    self._extract_company_history(page),
                    self._extract_news_and_updates(page),
                    self._extract_contact_info(page),
                    self._extract_team_info(page),
                    self._extract_products_services(page),
                    self._extract_company_values(page),
                    self._extract_certifications(page)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                social_media, history, news, contact, team, products, values, certifications = results
                
                await browser.close()
                
                return {
                    "social_media_extended": social_media or [],
                    "company_history": history,
                    "recent_news": news or [],
                    "contact_info": contact or {},
                    "team_info": team or {},
                    "products_services": products or [],
                    "company_values": values or [],
                    "certifications": certifications or []
                }
                
        except Exception as e:
            self.log_service.log_debug("Error scraping company website", {"error": str(e)})
            return {
                "social_media_extended": [],
                "company_history": None,
                "recent_news": [],
                "contact_info": {},
                "team_info": {},
                "products_services": [],
                "company_values": [],
                "certifications": [],
                "website_scraping_error": str(e)
            }

    async def _extract_social_media_links(self, page: Page) -> list:
        """Extrai links de redes sociais do site da empresa"""
        try:
            social_media = []
            
            # Seletores comuns para redes sociais
            social_selectors = {
                'facebook': ['a[href*="facebook.com"]', 'a[href*="fb.com"]'],
                'instagram': ['a[href*="instagram.com"]'],
                'twitter': ['a[href*="twitter.com"]', 'a[href*="x.com"]'],
                'linkedin': ['a[href*="linkedin.com"]'],
                'youtube': ['a[href*="youtube.com"]'],
                'tiktok': ['a[href*="tiktok.com"]'],
                'whatsapp': ['a[href*="wa.me"]', 'a[href*="whatsapp.com"]']
            }
            
            for platform, selectors in social_selectors.items():
                for selector in selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            href = await element.get_attribute('href')
                            if href and href not in [item['url'] for item in social_media]:
                                # Tentar extrair número de seguidores se visível
                                followers = await self._extract_followers_count(element)
                                social_media.append({
                                    'platform': platform,
                                    'url': href,
                                    'followers': followers
                                })
                                break  # Pega apenas o primeiro link de cada plataforma
                    except:
                        continue
            
            return social_media
            
        except Exception as e:
            self.log_service.log_debug("Error extracting social media links", {"error": str(e)})
            return []

    async def _extract_followers_count(self, element) -> Optional[int]:
        """Tenta extrair número de seguidores se visível"""
        try:
            # Buscar texto próximo que pode conter número de seguidores
            parent = await element.query_selector('..')
            if parent:
                text = await parent.inner_text()
                # Regex para encontrar números seguidos de "seguidores", "followers", etc.
                import re
                match = re.search(r'([0-9,\.]+)\s*(seguidores|followers|k|m)', text.lower())
                if match:
                    number_str = match.group(1).replace(',', '').replace('.', '')
                    multiplier = 1
                    if 'k' in match.group(2):
                        multiplier = 1000
                    elif 'm' in match.group(2):
                        multiplier = 1000000
                    return int(float(number_str) * multiplier)
        except:
            pass
        return None

    async def _extract_company_history(self, page: Page) -> Optional[str]:
        """Extrai história da empresa"""
        try:
            history_selectors = [
                'section[id*="historia"]',
                'section[id*="history"]',
                'div[class*="historia"]',
                'div[class*="history"]',
                'section[id*="sobre"]',
                'section[id*="about"]',
                'div[class*="about"]',
                '.company-history',
                '.nossa-historia',
                '.our-story'
            ]
            
            for selector in history_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 100:  # Apenas textos substanciais
                            return text.strip()
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.log_service.log_debug("Error extracting company history", {"error": str(e)})
            return None

    async def _extract_news_and_updates(self, page: Page) -> list:
        """Extrai notícias e atualizações recentes"""
        try:
            news = []
            
            news_selectors = [
                'section[id*="noticias"]',
                'section[id*="news"]',
                'div[class*="noticias"]',
                'div[class*="news"]',
                '.blog-posts',
                '.news-section',
                '.updates'
            ]
            
            for selector in news_selectors:
                try:
                    section = await page.query_selector(selector)
                    if section:
                        # Buscar artigos/posts dentro da seção
                        articles = await section.query_selector_all('article, .post, .news-item, .blog-item')
                        
                        for article in articles[:5]:  # Máximo 5 notícias
                            title_elem = await article.query_selector('h1, h2, h3, h4, .title, .headline')
                            date_elem = await article.query_selector('.date, .published, time')
                            link_elem = await article.query_selector('a')
                            
                            if title_elem:
                                title = await title_elem.inner_text()
                                date = await date_elem.inner_text() if date_elem else None
                                link = await link_elem.get_attribute('href') if link_elem else None
                                
                                news.append({
                                    'title': title.strip(),
                                    'date': date.strip() if date else None,
                                    'link': link
                                })
                        break
                except:
                    continue
            
            return news
            
        except Exception as e:
            self.log_service.log_debug("Error extracting news and updates", {"error": str(e)})
            return []

    async def _extract_contact_info(self, page: Page) -> dict:
        """Extrai informações de contato"""
        try:
            contact = {}
            
            # Buscar telefones
            phone_selectors = ['a[href^="tel:"]', '.phone', '.telefone', '.contact-phone']
            for selector in phone_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        if selector.startswith('a[href^="tel:"]'):
                            contact['phone'] = await element.get_attribute('href')
                            contact['phone'] = contact['phone'].replace('tel:', '')
                        else:
                            contact['phone'] = await element.inner_text()
                        break
                except:
                    continue
            
            # Buscar emails
            email_selectors = ['a[href^="mailto:"]', '.email', '.contact-email']
            for selector in email_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        if selector.startswith('a[href^="mailto:"]'):
                            contact['email'] = await element.get_attribute('href')
                            contact['email'] = contact['email'].replace('mailto:', '')
                        else:
                            contact['email'] = await element.inner_text()
                        break
                except:
                    continue
            
            # Buscar endereço
            address_selectors = ['.address', '.endereco', '.contact-address', '.location']
            for selector in address_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        contact['address'] = await element.inner_text()
                        break
                except:
                    continue
            
            return contact
            
        except Exception as e:
            self.log_service.log_debug("Error extracting contact info", {"error": str(e)})
            return {}

    async def _extract_team_info(self, page: Page) -> dict:
        """Extrai informações sobre a equipe/liderança"""
        try:
            team_info = {'leadership': [], 'team_size_estimate': None}
            
            # Seletores para seção de equipe
            team_selectors = [
                '.team-member',
                '.leadership',
                '[class*="team"]',
                '[class*="founder"]',
                '[class*="ceo"]',
                '[class*="director"]'
            ]
            
            for selector in team_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:10]:  # Limita a 10 membros
                        name_elem = await element.query_selector('.name, h3, h4, .title')
                        role_elem = await element.query_selector('.role, .position, .title')
                        
                        if name_elem:
                            name = await name_elem.inner_text()
                            role = await role_elem.inner_text() if role_elem else None
                            
                            team_info['leadership'].append({
                                'name': name.strip(),
                                'role': role.strip() if role else None
                            })
                except:
                    continue
            
            return team_info
            
        except Exception as e:
            self.log_service.log_debug("Error extracting team info", {"error": str(e)})
            return {'leadership': [], 'team_size_estimate': None}

    async def _extract_products_services(self, page: Page) -> list:
        """Extrai informações sobre produtos e serviços"""
        try:
            products_services = []
            
            # Seletores para produtos/serviços
            product_selectors = [
                '.product',
                '.service',
                '[class*="product"]',
                '[class*="service"]',
                '.offering'
            ]
            
            for selector in product_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:10]:  # Limita a 10 itens
                        title_elem = await element.query_selector('h1, h2, h3, h4, .title, .name')
                        desc_elem = await element.query_selector('.description, .desc, p')
                        
                        if title_elem:
                            title = await title_elem.inner_text()
                            description = await desc_elem.inner_text() if desc_elem else None
                            
                            products_services.append({
                                'name': title.strip(),
                                'description': description.strip() if description else None
                            })
                except:
                    continue
            
            return products_services
            
        except Exception as e:
            self.log_service.log_debug("Error extracting products/services", {"error": str(e)})
            return []

    async def _extract_company_values(self, page: Page) -> list:
        """Extrai valores e missão da empresa"""
        try:
            values = []
            
            # Seletores para valores/missão
            values_selectors = [
                '.value',
                '.mission',
                '.vision',
                '[class*="value"]',
                '[class*="mission"]',
                '[class*="vision"]'
            ]
            
            for selector in values_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 20:
                            values.append(text.strip())
                except:
                    continue
            
            return values
            
        except Exception as e:
            self.log_service.log_debug("Error extracting company values", {"error": str(e)})
            return []

    async def _extract_certifications(self, page: Page) -> list:
        """Extrai certificações e prêmios da empresa"""
        try:
            certifications = []
            
            # Seletores para certificações
            cert_selectors = [
                '.certification',
                '.award',
                '.certificate',
                '[class*="cert"]',
                '[class*="award"]',
                '[class*="badge"]'
            ]
            
            for selector in cert_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        text = await element.inner_text()
                        if text and len(text.strip()) > 5:
                            certifications.append(text.strip())
                except:
                    continue
            
            return certifications
            
        except Exception as e:
            self.log_service.log_debug("Error extracting certifications", {"error": str(e)})
            return []

    async def _extract_location_data(self, headquarters: str) -> Dict[str, Optional[str]]:
        """Extrai país, código do país, região, código da região, cidade e código de discagem internacional usando API do GeoNames"""
        self.log_service.log_debug("Starting location extraction", {"headquarters": headquarters})
        
        if not headquarters:
            self.log_service.log_debug("No headquarters data provided for location extraction", {})
            return {
                "country": None,
                "country_code": None,
                "region": None,
                "region_code": None,
                "city": None,
                "country_dial_code": None
            }
        
        try:
            # Divide o headquarters em partes (cidade, estado/região, país)
            parts = [part.strip() for part in headquarters.split(',')]
            self.log_service.log_debug("Headquarters parts extracted", {"parts": parts})
            
            country = None
            country_code = None
            region = None
            region_code = None
            city = None
            country_dial_code = None
            
            if len(parts) >= 1:
                city = parts[0]
                self.log_service.log_debug("Extracted city", {"city": city})
            
            if len(parts) >= 2:
                region = parts[1]
                self.log_service.log_debug("Extracted region", {"region": region})
            
            if len(parts) >= 3:
                potential_country = parts[2]
            else:
                potential_country = parts[-1] if parts else None
            
            self.log_service.log_debug("Potential country identified", {"potential_country": potential_country})
            
            # Busca o país usando a API do GeoNames
            if potential_country:
                self.log_service.log_debug("Searching country data", {"potential_country": potential_country})
                country_data = await self._get_country_from_geonames(potential_country)
                if country_data:
                    country = country_data.get('countryName')
                    country_code = country_data.get('countryCode')
                    country_dial_code = self._get_country_dial_code(country_code)
                    self.log_service.log_debug("Found country data", {
                        "country": country,
                        "country_code": country_code,
                        "dial_code": country_dial_code
                    })
                else:
                    self.log_service.log_debug("No country data found", {"potential_country": potential_country})
            
            # Se não encontrou o país, tenta buscar por cidade
            if not country and city:
                self.log_service.log_debug("Searching city data", {"city": city, "region": region})
                city_data = await self._get_city_from_geonames(city, region)
                if city_data:
                    country = city_data.get('countryName')
                    country_code = city_data.get('countryCode')
                    country_dial_code = self._get_country_dial_code(country_code)
                    region_code = city_data.get('adminCode1')  # Código da região/estado
                    if not region:
                        region = city_data.get('adminName1')  # Estado/Província
                    self.log_service.log_debug("Found city data", {
                        "city": city,
                        "country": country,
                        "country_code": country_code,
                        "region": region,
                        "region_code": region_code,
                        "dial_code": country_dial_code
                    })
                else:
                    self.log_service.log_debug("No city data found", {"city": city})
            
            result = {
                "country": country,
                "country_code": country_code,
                "region": region,
                "region_code": region_code,
                "city": city,
                "country_dial_code": country_dial_code
            }
            
            self.log_service.log_debug("Final location data", result)
            return result
            
        except Exception as e:
            self.log_service.log_debug("Error extracting location data", {"error": str(e)})
            # Fallback para dados básicos sem API
            parts = [part.strip() for part in headquarters.split(',')]
            fallback_result = {
                "country": parts[-1] if parts else None,
                "country_code": None,
                "region": parts[1] if len(parts) >= 2 else None,
                "region_code": None,
                "city": parts[0] if parts else None,
                "country_dial_code": None
            }
            self.log_service.log_debug("Fallback location data", fallback_result)
            return fallback_result

    async def _get_country_from_geonames(self, country_name: str) -> Optional[Dict[str, str]]:
        """Busca dados do país usando API do GeoNames"""
        try:
            self.log_service.log_debug("Making GeoNames API request for country", {"country_name": country_name})
            # API do GeoNames para buscar países
            response = requests.get(
                "http://api.geonames.org/searchJSON",
                params={
                    'q': country_name.strip(),
                    'featureClass': 'A',  # Administrative areas (países)
                    'featureCode': 'PCLI',  # Independent political entity (país)
                    'maxRows': 1,
                    'username': os.getenv('GEONAMES_USERNAME', 'mrstory')
                },
                timeout=5
            )
            
            self.log_service.log_debug("GeoNames country response", {"status_code": response.status_code})
            
            if response.status_code == 200:
                data = response.json()
                self.log_service.log_debug("GeoNames country response data", {"data": data})
                if data.get('geonames') and len(data['geonames']) > 0:
                    country_info = data['geonames'][0]
                    result = {
                        'countryName': country_info.get('name', country_name),
                        'countryCode': country_info.get('countryCode', ''),
                        'geonameId': country_info.get('geonameId', '')
                    }
                    self.log_service.log_debug("Returning country data", {"result": result})
                    return result
        except Exception as e:
            self.log_service.log_debug("Error fetching country data from GeoNames", {
                "country_name": country_name,
                "error": str(e)
            })
        
        return None

    async def _get_city_from_geonames(self, city_name: str, region_name: str = None) -> Optional[Dict[str, str]]:
        """Busca dados da cidade usando API do GeoNames"""
        try:
            # Constrói a query de busca
            query = city_name.strip()
            if region_name:
                query += f" {region_name.strip()}"
            
            self.log_service.log_debug("Making GeoNames API request for city", {"query": query})
            
            # API do GeoNames para buscar cidades
            response = requests.get(
                "http://api.geonames.org/searchJSON",
                params={
                    'q': query,
                    'featureClass': 'P',  # Populated places (cidades)
                    'maxRows': 1,
                    'username': os.getenv('GEONAMES_USERNAME', 'mrstory')
                },
                timeout=5
            )
            
            self.log_service.log_debug("GeoNames city response", {"status_code": response.status_code})
            
            if response.status_code == 200:
                data = response.json()
                self.log_service.log_debug("GeoNames city response data", {"data": data})
                if data.get('geonames') and len(data['geonames']) > 0:
                    city_info = data['geonames'][0]
                    result = {
                        'cityName': city_info.get('name', city_name),
                        'countryName': city_info.get('countryName', ''),
                        'countryCode': city_info.get('countryCode', ''),
                        'adminName1': city_info.get('adminName1', ''),  # Estado/Província
                        'adminCode1': city_info.get('adminCode1', ''),  # Código da região/estado - ESTA LINHA ESTAVA FALTANDO!
                        'geonameId': city_info.get('geonameId', '')
                    }
                    self.log_service.log_debug("Returning city data", {"result": result})
                    return result
        except Exception as e:
            self.log_service.log_debug("Error fetching city data from GeoNames", {
                "city_name": city_name,
                "error": str(e)
            })
        
        return None

    def _clean_field_text(self, text: str, prefixes_to_remove: list) -> Optional[str]:
        """Remove prefixos indesejados do texto extraído"""
        if not text:
            return None
            
        cleaned_text = text.strip()
        
        # Remove cada prefixo da lista
        for prefix in prefixes_to_remove:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].strip()
                break
        
        return cleaned_text if cleaned_text else None

    def _get_country_dial_code(self, country_code: str) -> Optional[str]:
        """Retorna o código de discagem internacional (DDI) para um código de país"""
        if not country_code:
            return None
        
        # Mapeamento de códigos de país para códigos de discagem internacional
        dial_codes = {
            'US': '+1', 'CA': '+1', 'BR': '+55', 'AR': '+54', 'CL': '+56', 'CO': '+57',
            'PE': '+51', 'UY': '+598', 'PY': '+595', 'BO': '+591', 'EC': '+593', 'VE': '+58',
            'GY': '+592', 'SR': '+597', 'GF': '+594', 'FK': '+500', 'MX': '+52', 'GT': '+502',
            'BZ': '+501', 'SV': '+503', 'HN': '+504', 'NI': '+505', 'CR': '+506', 'PA': '+507',
            'CU': '+53', 'JM': '+1876', 'HT': '+509', 'DO': '+1809', 'PR': '+1787', 'TT': '+1868',
            'BB': '+1246', 'GD': '+1473', 'LC': '+1758', 'VC': '+1784', 'AG': '+1268', 'DM': '+1767',
            'KN': '+1869', 'BS': '+1242', 'GB': '+44', 'IE': '+353', 'FR': '+33', 'ES': '+34',
            'PT': '+351', 'IT': '+39', 'DE': '+49', 'AT': '+43', 'CH': '+41', 'NL': '+31',
            'BE': '+32', 'LU': '+352', 'DK': '+45', 'SE': '+46', 'NO': '+47', 'FI': '+358',
            'IS': '+354', 'PL': '+48', 'CZ': '+420', 'SK': '+421', 'HU': '+36', 'SI': '+386',
            'HR': '+385', 'BA': '+387', 'RS': '+381', 'ME': '+382', 'MK': '+389', 'AL': '+355',
            'GR': '+30', 'BG': '+359', 'RO': '+40', 'MD': '+373', 'UA': '+380', 'BY': '+375',
            'LT': '+370', 'LV': '+371', 'EE': '+372', 'RU': '+7', 'KZ': '+7', 'CN': '+86',
            'JP': '+81', 'KR': '+82', 'IN': '+91', 'PK': '+92', 'BD': '+880', 'LK': '+94',
            'MV': '+960', 'NP': '+977', 'BT': '+975', 'MM': '+95', 'TH': '+66', 'LA': '+856',
            'VN': '+84', 'KH': '+855', 'MY': '+60', 'SG': '+65', 'BN': '+673', 'ID': '+62',
            'PH': '+63', 'TL': '+670', 'AU': '+61', 'NZ': '+64', 'FJ': '+679', 'PG': '+675',
            'SB': '+677', 'VU': '+678', 'NC': '+687', 'PF': '+689', 'WS': '+685', 'TO': '+676',
            'KI': '+686', 'NR': '+674', 'PW': '+680', 'FM': '+691', 'MH': '+692', 'TV': '+688',
            'ZA': '+27', 'NA': '+264', 'BW': '+267', 'ZW': '+263', 'ZM': '+260', 'MW': '+265',
            'MZ': '+258', 'SZ': '+268', 'LS': '+266', 'MG': '+261', 'MU': '+230', 'SC': '+248',
            'KM': '+269', 'YT': '+262', 'RE': '+262', 'EG': '+20', 'LY': '+218', 'TN': '+216',
            'DZ': '+213', 'MA': '+212', 'EH': '+212', 'SD': '+249', 'SS': '+211', 'ET': '+251',
            'ER': '+291', 'DJ': '+253', 'SO': '+252', 'KE': '+254', 'UG': '+256', 'TZ': '+255',
            'RW': '+250', 'BI': '+257', 'CD': '+243', 'CG': '+242', 'CF': '+236', 'CM': '+237',
            'TD': '+235', 'NE': '+227', 'NG': '+234', 'BJ': '+229', 'TG': '+228', 'GH': '+233',
            'CI': '+225', 'LR': '+231', 'SL': '+232', 'GN': '+224', 'GW': '+245', 'GM': '+220',
            'SN': '+221', 'MR': '+222', 'ML': '+223', 'BF': '+226', 'CV': '+238', 'ST': '+239',
            'GQ': '+240', 'GA': '+241', 'AO': '+244', 'IL': '+972', 'PS': '+970', 'JO': '+962',
            'SY': '+963', 'LB': '+961', 'IQ': '+964', 'IR': '+98', 'TR': '+90', 'CY': '+357',
            'GE': '+995', 'AM': '+374', 'AZ': '+994', 'KW': '+965', 'SA': '+966', 'BH': '+973',
            'QA': '+974', 'AE': '+971', 'OM': '+968', 'YE': '+967', 'AF': '+93', 'UZ': '+998',
            'TM': '+993', 'TJ': '+992', 'KG': '+996', 'MN': '+976'
        }
        
        return dial_codes.get(country_code.upper())

    def _is_domain(self, text: str) -> bool:
        """Verifica se o texto é um domínio"""
        import re
        # Padrão simples para detectar domínios
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]*\.[a-zA-Z]{2,}$'
        return bool(re.match(domain_pattern, text.strip()))

    def _extract_company_name_from_domain(self, domain: str) -> Optional[str]:
        """Extrai o nome da empresa do domínio"""
        try:
            # Remove www. se presente
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Pega a parte antes do primeiro ponto
            company_name = domain.split('.')[0]
            
            # Capitaliza adequadamente
            if company_name:
                # Se contém hífen, capitaliza cada parte
                if '-' in company_name:
                    parts = company_name.split('-')
                    return ' '.join(part.capitalize() for part in parts)
                else:
                    return company_name.capitalize()
            
            return None
        except:
            return None

    def _extract_linkedin_from_social_media(self, website_data: Dict[str, Any]) -> Optional[str]:
        """Extrai URL do LinkedIn das redes sociais encontradas no site"""
        if not website_data or 'social_media_extended' not in website_data:
            return None
            
        for social in website_data.get('social_media_extended', []):
            if (social.get('platform') == 'linkedin' and 
                social.get('url') and 
                '/company/' in social.get('url')):
                
                linkedin_url = social.get('url')
                self.log_service.log_debug("LinkedIn URL extracted from social media", {"url": linkedin_url})
                return linkedin_url
        
        return None

    def _merge_website_data(self, linkedin_data: Dict[str, Any], website_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mescla dados do LinkedIn com dados do site"""
        if not website_data:
            return linkedin_data
            
        # Combinar redes sociais
        linkedin_social = linkedin_data.get('social_media', [])
        website_social = website_data.get('social_media_extended', [])
        
        all_social = linkedin_social.copy()
        for social in website_social:
            if not any(s.get('url') == social.get('url') for s in all_social):
                all_social.append(social)
        
        # Mesclar todos os dados
        linkedin_data.update({
            'social_media': all_social,
            'company_history': website_data.get('company_history'),
            'recent_news': website_data.get('recent_news', []),
            'contact_info': website_data.get('contact_info', {}),
            'team_info': website_data.get('team_info', {}),
            'products_services': website_data.get('products_services', []),
            'company_values': website_data.get('company_values', []),
            'certifications': website_data.get('certifications', [])
        })
        
        return linkedin_data
