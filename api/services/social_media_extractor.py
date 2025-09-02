import re
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
import httpx
from ..log_service import LogService
from .brave_search_service import BraveSearchService

class SocialMediaExtractor:
    """Extrator avançado de redes sociais que coleta 100% dos links disponíveis"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        self.session = None
        self.brave_search = BraveSearchService(log_service)
        
        # Padrões de redes sociais mais abrangentes
        self.social_patterns = {
            'facebook': [
                r'(?:https?://)?(?:www\.)?(?:m\.)?facebook\.com/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?fb\.com/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?fb\.me/([^/?\s]+)'
            ],
            'instagram': [
                r'(?:https?://)?(?:www\.)?instagram\.com/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?instagr\.am/([^/?\s]+)'
            ],
            'twitter': [
                r'(?:https?://)?(?:www\.)?twitter\.com/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?x\.com/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?t\.co/([^/?\s]+)'
            ],
            'linkedin': [
                r'(?:https?://)?(?:www\.)?linkedin\.com/company/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?linkedin\.com/in/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?linkedin\.com/pub/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?linkedin\.com/profile/view\?id=([^&\s]+)'
            ],
            'youtube': [
                r'(?:https?://)?(?:www\.)?youtube\.com/channel/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?youtube\.com/user/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?youtube\.com/c/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?youtube\.com/@([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?youtu\.be/([^/?\s]+)'
            ],
            'tiktok': [
                r'(?:https?://)?(?:www\.)?tiktok\.com/@([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?tiktok\.com/([^/?\s]+)'
            ],
            'whatsapp': [
                r'(?:https?://)?(?:www\.)?wa\.me/([\d+]+)',
                r'(?:https?://)?(?:www\.)?api\.whatsapp\.com/send\?phone=([\d+]+)',
                r'(?:https?://)?(?:www\.)?chat\.whatsapp\.com/([^/?\s]+)',
                r'whatsapp://send\?phone=([\d+]+)',
                r'whatsapp://chat\?code=([^&\s]+)',
                r'https://chat\.whatsapp\.com/([A-Za-z0-9]+)'
            ],
            'telegram': [
                r'(?:https?://)?(?:www\.)?t\.me/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?telegram\.me/([^/?\s]+)',
                r'tg://resolve\?domain=([^&\s]+)'
            ],
            'pinterest': [
                r'(?:https?://)?(?:www\.)?pinterest\.com/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?pin\.it/([^/?\s]+)'
            ],
            'snapchat': [
                r'(?:https?://)?(?:www\.)?snapchat\.com/add/([^/?\s]+)',
                r'snapchat://add/([^/?\s]+)'
            ],
            'discord': [
                r'(?:https?://)?(?:www\.)?discord\.gg/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?discord\.com/invite/([^/?\s]+)'
            ],
            'reddit': [
                r'(?:https?://)?(?:www\.)?reddit\.com/r/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?reddit\.com/u/([^/?\s]+)',
                r'(?:https?://)?(?:www\.)?reddit\.com/user/([^/?\s]+)'
            ],
            'github': [
                r'(?:https?://)?(?:www\.)?github\.com/([^/?\s]+)'
            ],
            'medium': [
                r'(?:https?://)?(?:www\.)?medium\.com/@([^/?\s]+)',
                r'(?:https?://)?([^.]+)\.medium\.com'
            ],
            'behance': [
                r'(?:https?://)?(?:www\.)?behance\.net/([^/?\s]+)'
            ],
            'dribbble': [
                r'(?:https?://)?(?:www\.)?dribbble\.com/([^/?\s]+)'
            ],
            'vimeo': [
                r'(?:https?://)?(?:www\.)?vimeo\.com/([^/?\s]+)'
            ],
            'twitch': [
                r'(?:https?://)?(?:www\.)?twitch\.tv/([^/?\s]+)'
            ]
        }
        
        # Seletores CSS para busca em elementos HTML
        self.css_selectors = [
            'a[href*="facebook.com"]',
            'a[href*="instagram.com"]',
            'a[href*="twitter.com"]',
            'a[href*="x.com"]',
            'a[href*="linkedin.com"]',
            'a[href*="youtube.com"]',
            'a[href*="tiktok.com"]',
            'a[href*="wa.me"]',
            'a[href*="whatsapp.com"]',
            'a[href*="t.me"]',
            'a[href*="telegram.me"]',
            'a[href*="pinterest.com"]',
            'a[href*="snapchat.com"]',
            'a[href*="discord.gg"]',
            'a[href*="reddit.com"]',
            'a[href*="github.com"]',
            'a[href*="medium.com"]',
            'a[href*="behance.net"]',
            'a[href*="dribbble.com"]',
            'a[href*="vimeo.com"]',
            'a[href*="twitch.tv"]'
        ]
    
    async def extract_all_social_media(self, html_content: str, base_url: str) -> Dict[str, Any]:
        """Extrai todas as redes sociais possíveis do HTML"""
        try:
            self.log_service.log_debug("Iniciando extração completa de redes sociais", {
                "base_url": base_url,
                "html_length": len(html_content)
            })
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Múltiplas estratégias de extração
            results = {
                'regex_extraction': await self._extract_by_regex(html_content),
                'css_selector_extraction': await self._extract_by_css_selectors(soup, base_url),
                'meta_tags_extraction': await self._extract_from_meta_tags(soup),
                'json_ld_extraction': await self._extract_from_json_ld(soup),
                'text_analysis_extraction': await self._extract_from_text_analysis(html_content),
                'contact_info': await self._extract_contact_info(soup, html_content)
            }
            
            # Consolidar resultados
            consolidated = await self._consolidate_results(results)
            
            self.log_service.log_debug("Extração de redes sociais concluída", {
                "total_platforms_found": len(consolidated.get('social_media', [])),
                "platforms": list(consolidated.get('social_media', {}).keys())
            })
            
            return consolidated
        except Exception as e:
            self.log_service.log_error(f"Erro na extração de redes sociais: {str(e)}")
            return self._empty_result()
    
    async def extract_social_media_info(self, url: str, html_content: str = None) -> Dict[str, Any]:
        """Extrai informações de redes sociais de uma URL com busca externa"""
        try:
            if not html_content:
                html_content = await self._fetch_content(url)
            
            if not html_content:
                return self._empty_result()
            
            # Extrair informações básicas do site
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extrair links de redes sociais do HTML
            social_links = self._extract_social_links(soup, url)
            
            # Extrair informações de contato
            contact_info = self._extract_contact_info(soup)
            
            # Extrair metadados
            metadata = self._extract_metadata(soup)
            
            # Buscar redes sociais via Brave Search se não encontradas
            domain = urlparse(url).netloc.replace('www.', '')
            company_name = metadata.get('title', '').split(' - ')[0].strip()
            
            # Buscar redes sociais adicionais via Brave Search
            brave_social_results = await self.brave_search.search_company_social_media(domain, company_name)
            
            # Mesclar resultados do site com resultados da busca
            enhanced_social_links = self._merge_social_results(social_links, brave_social_results)
            
            # Buscar informações adicionais da empresa
            company_info = await self.brave_search.search_company_info(domain, company_name)
            
            # Consolidar resultados
            result = self._consolidate_enhanced_results(enhanced_social_links, contact_info, metadata, company_info)
            
            self.log_service.log_info(f"Extração de redes sociais concluída para {url} (com busca externa)")
            return result
            
        except Exception as e:
            self.log_service.log_error(f"Erro na extração de redes sociais de {url}: {str(e)}")
            return self._empty_result()
    
    async def _fetch_content(self, url: str) -> str:
        """Busca o conteúdo HTML de uma URL"""
        try:
            if not self.session:
                self.session = httpx.AsyncClient(timeout=30.0)
            
            response = await self.session.get(url)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            self.log_service.log_error(f"Erro ao buscar conteúdo de {url}: {str(e)}")
            return ""
    
    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List[str]]:
        """Extrai links de redes sociais do HTML"""
        social_links = {}
        
        # Buscar por links usando seletores CSS
        for selector in self.css_selectors:
            elements = soup.select(selector)
            
            for element in elements:
                href = element.get('href', '')
                if href:
                    full_url = urljoin(base_url, href)
                    platform = self._identify_platform(full_url)
                    
                    if platform:
                        if platform not in social_links:
                            social_links[platform] = []
                        social_links[platform].append(full_url)
        
        return social_links
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrai metadados do HTML"""
        metadata = {}
        
        # Título
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        
        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag:
            metadata['description'] = desc_tag.get('content', '').strip()
        
        # Open Graph
        og_title = soup.find('meta', property='og:title')
        if og_title:
            metadata['og_title'] = og_title.get('content', '').strip()
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            metadata['og_description'] = og_desc.get('content', '').strip()
        
        return metadata
    
    def _merge_social_results(self, site_results: Dict[str, List[str]], brave_results: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Mescla resultados do site com resultados da busca Brave"""
        merged = site_results.copy()
        
        for platform, urls in brave_results.items():
            if platform not in merged:
                merged[platform] = []
            
            # Adicionar URLs únicas
            for url in urls:
                if url not in merged[platform]:
                    merged[platform].append(url)
        
        return merged
    
    def _consolidate_enhanced_results(self, social_links: Dict[str, List[str]], contact_info: Dict[str, Any], metadata: Dict[str, str], company_info: Dict[str, Any]) -> Dict[str, Any]:
        """Consolida todos os resultados incluindo informações da empresa"""
        return {
            'social_media': {
                platform: {
                    'urls': urls,
                    'primary_url': urls[0] if urls else None,
                    'total_found': len(urls)
                }
                for platform, urls in social_links.items()
            },
            'contact_info': contact_info,
            'metadata': metadata,
            'company_info': company_info,
            'extraction_summary': {
                'total_platforms_found': len(social_links),
                'platforms': list(social_links.keys()),
                'has_external_search': True
            }
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vazio"""
        return {
            'social_media': {},
            'contact_info': {},
            'metadata': {},
            'company_info': {},
            'extraction_summary': {
                'total_platforms_found': 0,
                'platforms': [],
                'has_external_search': False
            }
        }
    
    async def close(self):
        """Fecha a sessão HTTP"""
        if self.session:
            await self.session.aclose()
    
    async def _extract_by_regex(self, html_content: str) -> Dict[str, List[str]]:
        """Extração usando regex patterns"""
        results = {}
        
        for platform, patterns in self.social_patterns.items():
            found_urls = set()
            
            for pattern in patterns:
                matches = re.finditer(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    url = match.group(0)
                    if not url.startswith('http'):
                        url = 'https://' + url
                    found_urls.add(url)
            
            if found_urls:
                results[platform] = list(found_urls)
        
        return results
    
    async def _extract_by_css_selectors(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List[str]]:
        """Extração usando seletores CSS"""
        results = {}
        
        for selector in self.css_selectors:
            elements = soup.select(selector)
            
            for element in elements:
                href = element.get('href', '')
                if href:
                    full_url = urljoin(base_url, href)
                    platform = self._identify_platform(full_url)
                    
                    if platform:
                        if platform not in results:
                            results[platform] = []
                        results[platform].append(full_url)
        
        return results
    
    async def _extract_from_meta_tags(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extração de meta tags Open Graph e Twitter Cards"""
        results = {}
        
        # Meta tags Open Graph
        og_tags = soup.find_all('meta', property=lambda x: x and x.startswith('og:'))
        for tag in og_tags:
            content = tag.get('content', '')
            if any(social in content.lower() for social in ['facebook', 'instagram', 'twitter', 'linkedin']):
                platform = self._identify_platform(content)
                if platform:
                    if platform not in results:
                        results[platform] = []
                    results[platform].append(content)
        
        # Twitter Cards
        twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
        for tag in twitter_tags:
            content = tag.get('content', '')
            if 'twitter.com' in content.lower():
                if 'twitter' not in results:
                    results['twitter'] = []
                results['twitter'].append(content)
        
        return results
    
    async def _extract_from_json_ld(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extração de dados estruturados JSON-LD"""
        results = {}
        
        json_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                # Buscar por sameAs (redes sociais)
                if isinstance(data, dict) and 'sameAs' in data:
                    same_as = data['sameAs']
                    if isinstance(same_as, list):
                        for url in same_as:
                            platform = self._identify_platform(url)
                            if platform:
                                if platform not in results:
                                    results[platform] = []
                                results[platform].append(url)
                
                # Buscar recursivamente em objetos aninhados
                await self._search_json_recursive(data, results)
                
            except json.JSONDecodeError:
                continue
        
        return results
    
    async def _extract_from_text_analysis(self, html_content: str) -> Dict[str, List[str]]:
        """Análise de texto para encontrar menções de redes sociais"""
        results = {}
        
        # Padrões para encontrar handles/usernames mencionados no texto
        text_patterns = {
            'instagram': r'@([a-zA-Z0-9_.]+)\s*(?:no\s+instagram|on\s+instagram)',
            'twitter': r'@([a-zA-Z0-9_]+)\s*(?:no\s+twitter|on\s+twitter)',
            'facebook': r'facebook\.com/([a-zA-Z0-9_.]+)',
            'linkedin': r'linkedin\.com/(?:company|in)/([a-zA-Z0-9-]+)'
        }
        
        for platform, pattern in text_patterns.items():
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                username = match.group(1)
                if platform == 'instagram':
                    url = f"https://www.instagram.com/{username}"
                elif platform == 'twitter':
                    url = f"https://twitter.com/{username}"
                elif platform == 'facebook':
                    url = f"https://www.facebook.com/{username}"
                elif platform == 'linkedin':
                    url = f"https://www.linkedin.com/company/{username}"
                
                if platform not in results:
                    results[platform] = []
                results[platform].append(url)
        
        return results
    
    async def _extract_contact_info(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Extrai informações de contato completas"""
        contact_info = {
            'emails': [],
            'phones': [],
            'addresses': [],
            'whatsapp_numbers': []
        }
        
        # Emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, html_content)
        contact_info['emails'] = list(set(emails))
        
        # Telefones (múltiplos formatos)
        phone_patterns = [
            r'\+?\d{1,4}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}',
            r'\(\d{2,3}\)\s?\d{4,5}-?\d{4}',
            r'\d{2,3}\s?\d{4,5}-?\d{4}'
        ]
        
        phones = set()
        for pattern in phone_patterns:
            matches = re.findall(pattern, html_content)
            phones.update(matches)
        
        contact_info['phones'] = list(phones)
        
        # WhatsApp específico - padrões mais robustos
        whatsapp_patterns = [
            r'wa\.me/([\d+]+)',
            r'whatsapp\.com/send\?phone=([\d+]+)',
            r'whatsapp://send\?phone=([\d+]+)',
            r'api\.whatsapp\.com/send\?phone=([\d+]+)',
            r'web\.whatsapp\.com/send\?phone=([\d+]+)',
            # Padrões para números em texto
            r'whatsapp[:\s]*([\d\s\+\-\(\)]{10,20})',
            r'whatsa[p]*[:\s]*([\d\s\+\-\(\)]{10,20})',
            r'zap[:\s]*([\d\s\+\-\(\)]{10,20})'
        ]
        
        whatsapp_numbers = set()
        for pattern in whatsapp_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Limpar e validar número
                clean_number = re.sub(r'[^\d+]', '', match)
                if len(clean_number) >= 10:  # Número mínimo válido
                    whatsapp_numbers.add(clean_number)
        
        contact_info['whatsapp_numbers'] = list(whatsapp_numbers)
        
        return contact_info
    
    async def _search_json_recursive(self, data: Any, results: Dict[str, List[str]]) -> None:
        """Busca recursiva em estruturas JSON"""
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and any(social in value.lower() for social in ['facebook', 'instagram', 'twitter', 'linkedin']):
                    platform = self._identify_platform(value)
                    if platform:
                        if platform not in results:
                            results[platform] = []
                        results[platform].append(value)
                elif isinstance(value, (dict, list)):
                    await self._search_json_recursive(value, results)
        elif isinstance(data, list):
            for item in data:
                await self._search_json_recursive(item, results)
    
    def _identify_platform(self, url: str) -> Optional[str]:
        """Identifica a plataforma baseada na URL"""
        url_lower = url.lower()
        
        if 'facebook.com' in url_lower or 'fb.com' in url_lower:
            return 'facebook'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'linkedin.com' in url_lower:
            return 'linkedin'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'wa.me' in url_lower or 'whatsapp.com' in url_lower:
            return 'whatsapp'
        elif 't.me' in url_lower or 'telegram.me' in url_lower:
            return 'telegram'
        elif 'pinterest.com' in url_lower:
            return 'pinterest'
        elif 'snapchat.com' in url_lower:
            return 'snapchat'
        elif 'discord.gg' in url_lower or 'discord.com' in url_lower:
            return 'discord'
        elif 'reddit.com' in url_lower:
            return 'reddit'
        elif 'github.com' in url_lower:
            return 'github'
        elif 'medium.com' in url_lower:
            return 'medium'
        elif 'behance.net' in url_lower:
            return 'behance'
        elif 'dribbble.com' in url_lower:
            return 'dribbble'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        elif 'twitch.tv' in url_lower:
            return 'twitch'
        
        return None
    
    async def _consolidate_results(self, results: Dict[str, Dict[str, List[str]]]) -> Dict[str, Any]:
        """Consolida todos os resultados das diferentes estratégias"""
        consolidated = {
            'social_media': {},
            'contact_info': {},
            'extraction_summary': {
                'total_methods_used': len(results),
                'methods_with_results': 0,
                'total_platforms_found': 0
            }
        }
        
        # Consolidar redes sociais
        all_social_urls = {}
        
        for method, method_results in results.items():
            if method == 'contact_info':
                consolidated['contact_info'] = method_results
                continue
                
            if method_results:
                consolidated['extraction_summary']['methods_with_results'] += 1
                
                for platform, urls in method_results.items():
                    if platform not in all_social_urls:
                        all_social_urls[platform] = set()
                    
                    if isinstance(urls, list):
                        all_social_urls[platform].update(urls)
                    else:
                        all_social_urls[platform].add(urls)
        
        # Converter sets para listas e limpar duplicatas
        for platform, urls in all_social_urls.items():
            unique_urls = list(set(urls))
            consolidated['social_media'][platform] = {
                'urls': unique_urls,
                'primary_url': unique_urls[0] if unique_urls else None,
                'total_found': len(unique_urls)
            }
        
        consolidated['extraction_summary']['total_platforms_found'] = len(all_social_urls)
        
        return consolidated