from playwright.async_api import async_playwright
import json
import os
import time
import random
import asyncio
import httpx
from typing import Dict, Optional

class LinkedInAuthService:
    def __init__(self):
        self.cookies_file = 'linkedin_cookies.json'
        self.login_url = 'https://www.linkedin.com/login'
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        self.session_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    async def get_cookies(self) -> Optional[Dict]:
        """Obtém cookies do LinkedIn usando sessão HTTP ao invés de Playwright"""
        # Verificar se existem cookies válidos salvos (24 horas)
        if os.path.exists(self.cookies_file):
            file_stat = os.stat(self.cookies_file)
            if (time.time() - file_stat.st_mtime) < 86400:
                with open(self.cookies_file, 'r') as f:
                    return json.load(f)

        # Tentar obter cookies via sessão HTTP
        try:
            cookies = await self._login_with_session()
            if cookies:
                # Salvar cookies para reutilização
                with open(self.cookies_file, 'w') as f:
                    json.dump(cookies, f)
                return cookies
        except Exception as e:
            print(f"Erro ao obter cookies: {e}")
            
        # Fallback: usar cookies estáticos se disponíveis
        return self._get_fallback_cookies()

    async def _login_with_session(self) -> Optional[Dict]:
        """Tenta fazer login usando httpx session"""
        try:
            async with httpx.AsyncClient(headers=self.session_headers, follow_redirects=True) as client:
                # Primeiro, obter a página de login para pegar tokens CSRF
                login_response = await client.get(self.login_url)
                
                if login_response.status_code != 200:
                    return None
                
                # Extrair cookies da resposta inicial
                cookies_dict = {}
                for cookie in login_response.cookies:
                    cookies_dict[cookie.name] = cookie.value
                
                # Simular delay humano
                await asyncio.sleep(random.uniform(1, 2))
                
                # Tentar extrair CSRF token da página (se necessário)
                # Nota: LinkedIn pode requerer tokens CSRF para login
                
                # Preparar dados de login
                login_data = {
                    'session_key': self.email,
                    'session_password': self.password,
                }
                
                # Fazer POST para login
                login_post_response = await client.post(
                    'https://www.linkedin.com/checkpoint/lg/login-submit',
                    data=login_data,
                    cookies=cookies_dict
                )
                
                # Verificar se login foi bem-sucedido
                if login_post_response.status_code in [200, 302]:
                    # Combinar cookies da sessão
                    for cookie in login_post_response.cookies:
                        cookies_dict[cookie.name] = cookie.value
                    
                    # Converter para formato esperado
                    formatted_cookies = []
                    for name, value in cookies_dict.items():
                        formatted_cookies.append({
                            'name': name,
                            'value': value,
                            'domain': '.linkedin.com',
                            'path': '/'
                        })
                    
                    return formatted_cookies
                    
        except Exception as e:
            print(f"Erro no login com sessão: {e}")
            return None

    def _get_fallback_cookies(self) -> Optional[Dict]:
        """Retorna cookies estáticos como fallback"""
        # Você pode definir cookies estáticos aqui se necessário
        # ou retornar None para indicar que não há cookies disponíveis
        fallback_cookies_file = 'linkedin_cookies_backup.json'
        
        if os.path.exists(fallback_cookies_file):
            try:
                with open(fallback_cookies_file, 'r') as f:
                    return json.load(f)
            except:
                pass
                
        return None

    def format_cookies_for_scrapy(self, cookies) -> Dict[str, str]:
        """Formata cookies para uso com Scrapy"""
        if not cookies:
            return {}
            
        if isinstance(cookies, list):
            return {cookie['name']: cookie['value'] for cookie in cookies}
        elif isinstance(cookies, dict):
            return cookies
        else:
            return {}

    def get_session_headers(self) -> Dict[str, str]:
        """Retorna headers padrão para sessões HTTP"""
        return self.session_headers.copy()

    async def validate_cookies(self, cookies: Dict) -> bool:
        """Valida se os cookies ainda são válidos"""
        try:
            async with httpx.AsyncClient(headers=self.session_headers) as client:
                # Fazer uma requisição simples para verificar se os cookies funcionam
                test_response = await client.get(
                    'https://www.linkedin.com/feed/',
                    cookies=self.format_cookies_for_scrapy(cookies)
                )
                
                # Se não foi redirecionado para login, cookies são válidos
                return 'login' not in test_response.url.path
                
        except Exception:
            return False

    def clear_saved_cookies(self):
        """Remove cookies salvos"""
        if os.path.exists(self.cookies_file):
            os.remove(self.cookies_file)