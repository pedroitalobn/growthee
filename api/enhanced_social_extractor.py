import re
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import json
from dataclasses import dataclass
from .log_service import LogService

@dataclass
class SocialMediaResult:
    """Resultado estruturado de extração de redes sociais"""
    platform: str
    url: str
    username: Optional[str] = None
    confidence_score: float = 0.0
    extraction_method: str = ""
    is_verified: bool = False

class EnhancedSocialExtractor:
    """Extrator avançado de redes sociais com IA e validação em tempo real"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        self.session = None
        
        # Padrões mais precisos e abrangentes
        self.platform_patterns = {
            'facebook': {
                'patterns': [
                    r'(?:https?://)?(?:www\.|m\.|mobile\.)?facebook\.com/(?:pages/)?([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?fb\.com/([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?fb\.me/([^/?#\s]+)'
                ],
                'domains': ['facebook.com', 'fb.com', 'fb.me'],
                'validation_endpoint': 'https://www.facebook.com/{username}',
                'username_regex': r'^[a-zA-Z0-9\.\-_]+$'
            },
            'instagram': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?',
                    r'(?:https?://)?(?:www\.)?instagr\.am/([a-zA-Z0-9_.]+)/?'
                ],
                'domains': ['instagram.com', 'instagr.am'],
                'validation_endpoint': 'https://www.instagram.com/{username}/',
                'username_regex': r'^[a-zA-Z0-9_.]+$'
            },
            'twitter': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)/?',
                    r'(?:https?://)?(?:www\.)?t\.co/([a-zA-Z0-9]+)'
                ],
                'domains': ['twitter.com', 'x.com', 't.co'],
                'validation_endpoint': 'https://x.com/{username}',
                'username_regex': r'^[a-zA-Z0-9_]+$'
            },
            'linkedin': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?linkedin\.com/company/([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?linkedin\.com/in/([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?linkedin\.com/pub/([^/?#\s]+)'
                ],
                'domains': ['linkedin.com'],
                'validation_endpoint': 'https://www.linkedin.com/company/{username}',
                'username_regex': r'^[a-zA-Z0-9\-_]+$'
            },
            'youtube': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?youtube\.com/(?:channel|c|user)/([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?youtube\.com/@([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?youtu\.be/([^/?#\s]+)'
                ],
                'domains': ['youtube.com', 'youtu.be'],
                'validation_endpoint': 'https://www.youtube.com/@{username}',
                'username_regex': r'^[a-zA-Z0-9\-_]+$'
            },
            'tiktok': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9_.]+)',
                    r'(?:https?://)?(?:www\.)?tiktok\.com/([a-zA-Z0-9_.]+)'
                ],
                'domains': ['tiktok.com'],
                'validation_endpoint': 'https://www.tiktok.com/@{username}',
                'username_regex': r'^[a-zA-Z0-9_.]+$'
            },
            'whatsapp': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?wa\.me/([0-9]+)',
                    r'(?:https?://)?(?:www\.)?api\.whatsapp\.com/send\?phone=([0-9]+)',
                    r'(?:https?://)?(?:www\.)?chat\.whatsapp\.com/([a-zA-Z0-9]+)'
                ],
                'domains': ['wa.me', 'whatsapp.com'],
                'validation_endpoint': 'https://wa.me/{username}',
                'username_regex': r'^[0-9]+$'
            },
            'telegram': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)',
                    r'(?:https?://)?(?:www\.)?telegram\.me/([a-zA-Z0-9_]+)'
                ],
                'domains': ['t.me', 'telegram.me'],
                'validation_endpoint': 'https://t.me/{username}',
                'username_regex': r'^[a-zA-Z0-9_]+$'
            },
            'pinterest': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?pinterest\.com/([^/?#\s]+)',
                    r'(?:https?://)?(?:www\.)?pin\.it/([a-zA-Z0-9]+)'
                ],
                'domains': ['pinterest.com', 'pin.it'],
                'validation_endpoint': 'https://www.pinterest.com/{username}/',
                'username_regex': r'^[a-zA-Z0-9_]+$'
            },
            'github': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-_]+)'
                ],
                'domains': ['github.com'],
                'validation_endpoint': 'https://github.com/{username}',
                'username_regex': r'^[a-zA-Z0-9\-_]+$'
            },
            'discord': {
                'patterns': [
                    r'(?:https?://)?(?:www\.)?discord\.gg/([a-zA-Z0-9]+)',
                    r'(?:https?://)?(?:www\.)?discord\.com/invite/([a-zA-Z0-9]+)'
                ],
                'domains': ['discord.gg', 'discord.com'],
                'validation_endpoint': 'https://discord.gg/{username}',
                'username_regex': r'^[a-zA-Z0-9]+$'
            }
        }
        
        # Seletores CSS específicos por contexto
        self.contextual_selectors = {
            'header': ['header a[href*="{platform}"]', 'nav a[href*="{platform}"]'],
            'footer': ['footer a[href*="{platform}"]', '.footer a[href*="{platform}"]'],
            'social_section': ['.social a[href*="{platform}"]', '.social-media a[href*="{platform}"]', '.social-links a[href*="{platform}"]'],
            'contact': ['.contact a[href*="{platform}"]', '.contact-info a[href*="{platform}"]'],
            'general': ['a[href*="{platform}"]']
        }
    
    async def __aenter__(self):
        """Context manager para sessão HTTP"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={'User-Agent': 'Mozilla/5.0 (compatible; SocialExtractor/1.0)'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fechar sessão HTTP"""
        if self.session:
            await self.session.close()
    
    async def extract_comprehensive_social_media(self, html_content: str, base_url: str, 
                                               validate_urls: bool = True) -> Dict[str, Any]:
        """Extração completa e inteligente de redes sociais"""
        try:
            self.log_service.log_debug("Iniciando extração completa de redes sociais", {
                "base_url": base_url,
                "html_length": len(html_content),
                "validate_urls": validate_urls
            })
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Múltiplas estratégias de extração
            extraction_tasks = [
                self._extract_by_advanced_regex(html_content),
                self._extract_by_contextual_selectors(soup, base_url),
                self._extract_from_structured_data(soup),
                self._extract_from_meta_properties(soup),
                self._extract_from_text_analysis(html_content),
                self._extract_from_javascript(html_content),
                self._extract_contact_information(soup, html_content)
            ]
            
            results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
            
            # Processar resultados
            all_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.log_service.log_debug(f"Erro na estratégia {i}: {result}")
                    continue
                if result:
                    all_results.extend(result)
            
            # Consolidar e validar
            consolidated = await self._consolidate_and_validate(all_results, validate_urls)
            
            # Calcular scores de confiança
            final_results = await self._calculate_confidence_scores(consolidated)
            
            self.log_service.log_debug("Extração completa finalizada", {
                "total_platforms": len(final_results.get('social_media', {})),
                "platforms_found": list(final_results.get('social_media', {}).keys()),
                "total_urls": sum(len(data.get('urls', [])) for data in final_results.get('social_media', {}).values())
            })
            
            return final_results
            
        except Exception as e:
            self.log_service.log_debug(f"Erro na extração de redes sociais: {e}")
            return {}
    
    async def _extract_by_advanced_regex(self, html_content: str) -> List[SocialMediaResult]:
        """Extração usando regex avançado com validação"""
        results = []
        
        for platform, config in self.platform_patterns.items():
            for pattern in config['patterns']:
                matches = re.finditer(pattern, html_content, re.IGNORECASE)
                
                for match in matches:
                    try:
                        full_match = match.group(0)
                        username = match.group(1) if match.groups() else None
                        
                        # Validar username se existir
                        if username and config.get('username_regex'):
                            if not re.match(config['username_regex'], username):
                                continue
                        
                        # Construir URL completa
                        if not full_match.startswith('http'):
                            url = f"https://{full_match}"
                        else:
                            url = full_match
                            
                        # Garantir que a URL está completa para cada plataforma
                        if platform == "instagram" and username:
                            url = f"https://www.instagram.com/{username}/"
                        elif platform == "facebook" and username:
                            url = f"https://www.facebook.com/{username}/"
                        elif platform == "twitter" and username:
                            url = f"https://twitter.com/{username}"
                        elif platform == "linkedin" and username:
                            url = f"https://www.linkedin.com/company/{username}/"
                        elif platform == "youtube" and username:
                            url = f"https://www.youtube.com/channel/{username}"
                        elif platform == "tiktok" and username:
                            url = f"https://www.tiktok.com/@{username}"
                        
                        results.append(SocialMediaResult(
                            platform=platform,
                            url=url,
                            username=username,
                            confidence_score=0.8,
                            extraction_method="advanced_regex"
                        ))
                        
                    except Exception as e:
                        self.log_service.log_debug(f"Erro no regex para {platform}: {e}")
                        continue
        
        return results
    
    async def _extract_by_contextual_selectors(self, soup: BeautifulSoup, base_url: str) -> List[SocialMediaResult]:
        """Extração usando seletores CSS contextuais"""
        results = []
        
        for platform, config in self.platform_patterns.items():
            for domain in config['domains']:
                for context, selectors in self.contextual_selectors.items():
                    for selector_template in selectors:
                        selector = selector_template.format(platform=domain)
                        
                        try:
                            elements = soup.select(selector)
                            
                            for element in elements:
                                href = element.get('href', '')
                                if not href:
                                    continue
                                
                                full_url = urljoin(base_url, href)
                                
                                # Extrair username da URL
                                username = self._extract_username_from_url(full_url, platform)
                                
                                # Score baseado no contexto
                                context_scores = {
                                    'header': 0.9,
                                    'footer': 0.8,
                                    'social_section': 0.95,
                                    'contact': 0.85,
                                    'general': 0.6
                                }
                                
                                results.append(SocialMediaResult(
                                    platform=platform,
                                    url=full_url,
                                    username=username,
                                    confidence_score=context_scores.get(context, 0.5),
                                    extraction_method=f"contextual_css_{context}"
                                ))
                                
                        except Exception as e:
                            self.log_service.log_debug(f"Erro no seletor CSS: {e}")
                            continue
        
        return results
    
    async def _extract_from_structured_data(self, soup: BeautifulSoup) -> List[SocialMediaResult]:
        """Extração de dados estruturados (JSON-LD, Microdata)"""
        results = []
        
        # JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                await self._process_structured_data(data, results, "json_ld")
            except json.JSONDecodeError:
                continue
        
        # Microdata
        microdata_elements = soup.find_all(attrs={'itemtype': True})
        for element in microdata_elements:
            social_links = element.find_all('a', attrs={'itemprop': 'sameAs'})
            for link in social_links:
                href = link.get('href', '')
                platform = self._identify_platform_from_url(href)
                if platform:
                    username = self._extract_username_from_url(href, platform)
                    results.append(SocialMediaResult(
                        platform=platform,
                        url=href,
                        username=username,
                        confidence_score=0.9,
                        extraction_method="microdata"
                    ))
        
        return results
    
    async def _extract_from_meta_properties(self, soup: BeautifulSoup) -> List[SocialMediaResult]:
        """Extração de meta properties (Open Graph, Twitter Cards)"""
        results = []
        
        # Open Graph
        og_properties = ['og:url', 'og:see_also', 'article:author']
        for prop in og_properties:
            meta_tags = soup.find_all('meta', property=prop)
            for tag in meta_tags:
                content = tag.get('content', '')
                platform = self._identify_platform_from_url(content)
                if platform:
                    username = self._extract_username_from_url(content, platform)
                    results.append(SocialMediaResult(
                        platform=platform,
                        url=content,
                        username=username,
                        confidence_score=0.85,
                        extraction_method="open_graph"
                    ))
        
        # Twitter Cards
        twitter_properties = ['twitter:site', 'twitter:creator']
        for prop in twitter_properties:
            meta_tags = soup.find_all('meta', attrs={'name': prop})
            for tag in meta_tags:
                content = tag.get('content', '')
                if content.startswith('@'):
                    username = content[1:]
                    url = f"https://twitter.com/{username}"
                    results.append(SocialMediaResult(
                        platform='twitter',
                        url=url,
                        username=username,
                        confidence_score=0.9,
                        extraction_method="twitter_cards"
                    ))
        
        return results
    
    async def _extract_from_text_analysis(self, html_content: str) -> List[SocialMediaResult]:
        """Análise inteligente de texto para encontrar menções"""
        results = []
        
        # Padrões de texto natural
        text_patterns = {
            'instagram': [
                r'(?:siga|follow)\s+(?:a\s+gente|us|nos)\s+no\s+instagram[:\s]*@?([a-zA-Z0-9_.]+)',
                r'instagram[:\s]*@?([a-zA-Z0-9_.]+)',
                r'@([a-zA-Z0-9_.]+)\s+no\s+insta'
            ],
            'facebook': [
                r'(?:curta|like)\s+(?:nossa|our)\s+(?:página|page)\s+(?:no|on)\s+facebook[:\s]*([^\s]+)',
                r'facebook\.com/([a-zA-Z0-9_.]+)'
            ],
            'twitter': [
                r'(?:siga|follow)\s+(?:a\s+gente|us)\s+no\s+twitter[:\s]*@?([a-zA-Z0-9_]+)',
                r'twitter[:\s]*@?([a-zA-Z0-9_]+)'
            ],
            'linkedin': [
                r'linkedin\.com/company/([a-zA-Z0-9\-_]+)',
                r'(?:conecte|connect)\s+(?:conosco|with\s+us)\s+no\s+linkedin'
            ]
        }
        
        # Remover tags HTML para análise de texto puro
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        for platform, patterns in text_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if match.groups():
                        username = match.group(1)
                        url = self._build_platform_url(platform, username)
                        if url:
                            results.append(SocialMediaResult(
                                platform=platform,
                                url=url,
                                username=username,
                                confidence_score=0.7,
                                extraction_method="text_analysis"
                            ))
        
        return results
    
    async def _extract_from_javascript(self, html_content: str) -> List[SocialMediaResult]:
        """Extração de URLs em código JavaScript"""
        results = []
        
        # Encontrar scripts
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for script_content in scripts:
            # Procurar por URLs de redes sociais em strings JavaScript
            for platform, config in self.platform_patterns.items():
                for domain in config['domains']:
                    js_pattern = rf'["\']https?://(?:www\.)?{re.escape(domain)}/([^"\'/\s]+)["\']'
                    matches = re.finditer(js_pattern, script_content, re.IGNORECASE)
                    
                    for match in matches:
                        username = match.group(1)
                        url = match.group(0).strip('"\'')
                        
                        results.append(SocialMediaResult(
                            platform=platform,
                            url=url,
                            username=username,
                            confidence_score=0.6,
                            extraction_method="javascript"
                        ))
        
        return results
    
    async def _extract_contact_information(self, soup: BeautifulSoup, html_content: str) -> List[SocialMediaResult]:
        """Extração de informações de contato relacionadas"""
        results = []
        
        # WhatsApp específico
        whatsapp_patterns = [
            r'whatsapp[:\s]*([+]?[0-9\s\-\(\)]+)',
            r'wa\.me/([0-9]+)',
            r'api\.whatsapp\.com/send\?phone=([0-9]+)'
        ]
        
        for pattern in whatsapp_patterns:
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            for match in matches:
                phone = re.sub(r'[^0-9]', '', match.group(1))
                if len(phone) >= 10:  # Validação básica de telefone
                    url = f"https://wa.me/{phone}"
                    results.append(SocialMediaResult(
                        platform='whatsapp',
                        url=url,
                        username=phone,
                        confidence_score=0.8,
                        extraction_method="contact_extraction"
                    ))
        
        return results
    
    async def _consolidate_and_validate(self, results: List[SocialMediaResult], 
                                      validate_urls: bool = True) -> Dict[str, List[SocialMediaResult]]:
        """Consolida resultados e remove duplicatas"""
        consolidated = {}
        
        for result in results:
            if result.platform not in consolidated:
                consolidated[result.platform] = []
            
            # Verificar duplicatas por URL
            existing_urls = [r.url for r in consolidated[result.platform]]
            if result.url not in existing_urls:
                consolidated[result.platform].append(result)
        
        # Validar URLs se solicitado
        if validate_urls and self.session:
            for platform, platform_results in consolidated.items():
                validated_results = []
                for result in platform_results:
                    is_valid = await self._validate_social_url(result.url)
                    result.is_verified = is_valid
                    if is_valid or not validate_urls:
                        validated_results.append(result)
                consolidated[platform] = validated_results
        
        return consolidated
    
    async def _validate_social_url(self, url: str) -> bool:
        """Valida se uma URL de rede social existe"""
        try:
            async with self.session.head(url, allow_redirects=True) as response:
                return response.status < 400
        except:
            return False
    
    async def _calculate_confidence_scores(self, consolidated: Dict[str, List[SocialMediaResult]]) -> Dict[str, Any]:
        """Calcula scores de confiança finais"""
        final_results = {
            'social_media': {},
            'extraction_summary': {
                'total_platforms': len(consolidated),
                'total_urls': sum(len(results) for results in consolidated.values()),
                'validation_enabled': self.session is not None
            }
        }
        
        for platform, results in consolidated.items():
            if not results:
                continue
            
            # Ordenar por score de confiança
            sorted_results = sorted(results, key=lambda x: x.confidence_score, reverse=True)
            
            # Preparar dados finais
            urls_data = []
            for result in sorted_results:
                urls_data.append({
                    'url': result.url,
                    'username': result.username,
                    'confidence_score': result.confidence_score,
                    'extraction_method': result.extraction_method,
                    'is_verified': result.is_verified
                })
            
            final_results['social_media'][platform] = {
                'urls': [r['url'] for r in urls_data],
                'primary_url': urls_data[0]['url'] if urls_data else None,
                'total_found': len(urls_data),
                'best_confidence': urls_data[0]['confidence_score'] if urls_data else 0,
                'all_data': urls_data
            }
        
        return final_results
    
    def _identify_platform_from_url(self, url: str) -> Optional[str]:
        """Identifica plataforma a partir da URL"""
        url_lower = url.lower()
        
        for platform, config in self.platform_patterns.items():
            for domain in config['domains']:
                if domain in url_lower:
                    return platform
        
        return None
    
    def _extract_username_from_url(self, url: str, platform: str) -> Optional[str]:
        """Extrai username de uma URL específica da plataforma"""
        try:
            config = self.platform_patterns.get(platform, {})
            for pattern in config.get('patterns', []):
                match = re.search(pattern, url, re.IGNORECASE)
                if match and match.groups():
                    return match.group(1)
        except:
            pass
        
        return None
    
    def _build_platform_url(self, platform: str, username: str) -> Optional[str]:
        """Constrói URL da plataforma a partir do username"""
        url_templates = {
            'instagram': 'https://www.instagram.com/{username}',
            'facebook': 'https://www.facebook.com/{username}',
            'twitter': 'https://twitter.com/{username}',
            'linkedin': 'https://www.linkedin.com/company/{username}',
            'youtube': 'https://www.youtube.com/@{username}',
            'tiktok': 'https://www.tiktok.com/@{username}',
            'telegram': 'https://t.me/{username}',
            'pinterest': 'https://www.pinterest.com/{username}',
            'github': 'https://github.com/{username}'
        }
        
        template = url_templates.get(platform)
        if template:
            return template.format(username=username)
        
        return None
    
    async def _process_structured_data(self, data: Any, results: List[SocialMediaResult], method: str):
        """Processa dados estruturados recursivamente"""
        if isinstance(data, dict):
            # Procurar por sameAs (padrão schema.org)
            if 'sameAs' in data:
                same_as = data['sameAs']
                if isinstance(same_as, list):
                    for url in same_as:
                        platform = self._identify_platform_from_url(url)
                        if platform:
                            username = self._extract_username_from_url(url, platform)
                            results.append(SocialMediaResult(
                                platform=platform,
                                url=url,
                                username=username,
                                confidence_score=0.95,
                                extraction_method=method
                            ))
            
            # Procurar recursivamente
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    await self._process_structured_data(value, results, method)
                elif isinstance(value, str):
                    platform = self._identify_platform_from_url(value)
                    if platform:
                        username = self._extract_username_from_url(value, platform)
                        results.append(SocialMediaResult(
                            platform=platform,
                            url=value,
                            username=username,
                            confidence_score=0.8,
                            extraction_method=method
                        ))
        
        elif isinstance(data, list):
            for item in data:
                await self._process_structured_data(item, results, method)