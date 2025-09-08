from typing import Dict, Any, Optional
import logging
import re
from ..log_service import LogService

class TikTokScraperService:
    """Serviço para scraping de perfis do TikTok"""
    
    def __init__(self, log_service: LogService):
        self.log_service = log_service
        self.logger = logging.getLogger(__name__)
    
    async def scrape_profile(self, url: str) -> Dict[str, Any]:
        """Extrai dados de um perfil do TikTok"""
        try:
            # Extrair username da URL
            username_match = re.search(r'tiktok\.com/@([^/?]+)', url)
            if not username_match:
                return {"error": "URL inválida do TikTok"}
            
            username = username_match.group(1)
            normalized_url = f"https://www.tiktok.com/@{username}"
            
            # Log da tentativa
            self.log_service.log_access(
                "Iniciando scraping de perfil TikTok",
                {"url": normalized_url, "username": username}
            )
            
            # Usar Hyperbrowser para scraping do TikTok
            from ..mcp_client import run_mcp
            
            # Task detalhada para o agente
            task = f"""
            Visit {normalized_url}
            
            Esta é uma página de perfil do TikTok. Extraia as seguintes informações:
            
            1. Nome de usuário (@username)
            2. Nome de exibição do perfil
            3. Biografia/descrição do perfil
            4. Número de seguidores
            5. Número de pessoas seguindo
            6. Número de curtidas totais
            7. Número de vídeos
            8. Link do website (se houver)
            9. Email (se mencionado na bio)
            10. Telefone (se mencionado na bio)
            11. Localização (se mencionada na bio)
            
            Aguarde o carregamento completo da página e role um pouco para garantir que todos os dados sejam carregados.
            Retorne os dados em formato JSON estruturado com as chaves: username, name, bio, followers, following, likes, videos, website, email, phone, location.
            """
            
            # Usar Claude Computer Use Agent para melhor precisão
            result = await run_mcp(
                "mcp.config.usrlocalmcp.Hyperbrowser",
                "claude_computer_use_agent",
                {
                    "task": task,
                    "maxSteps": 15
                }
            )
            
            if result and "error" not in result:
                # Processar resultado do agente
                extracted_data = self._parse_agent_result(result, username, normalized_url)
                
                self.log_service.log_access(
                    "TikTok profile data extracted with Claude agent",
                    {"username": extracted_data.get("username")}
                )
                
                return extracted_data
            else:
                error_msg = result.get("error", "Erro desconhecido no agente") if result else "Falha na comunicação com o agente"
                self.logger.error(f"Erro no Claude agent: {error_msg}")
                
                # Fallback para Puppeteer
                return await self._fallback_puppeteer_scraping(normalized_url, username)
                
        except Exception as e:
            self.logger.error(f"Erro no scraping do TikTok: {str(e)}")
            return {"error": f"Erro no scraping do TikTok: {str(e)}"}
    
    def _parse_agent_result(self, result: Dict[str, Any], username: str, url: str) -> Dict[str, Any]:
        """Processa o resultado do agente Claude"""
        try:
            # Extrair dados do resultado do agente
            content = result.get("content", "")
            
            # Tentar extrair JSON do conteúdo
            import json
            
            # Procurar por JSON no conteúdo
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return self._normalize_tiktok_data(data, username, url)
                except json.JSONDecodeError:
                    pass
            
            # Se não encontrar JSON, tentar extrair dados com regex
            return self._extract_data_with_regex(content, username, url)
            
        except Exception as e:
            self.logger.error(f"Erro ao processar resultado do agente: {str(e)}")
            return {
                "username": username,
                "profile_url": url,
                "error": "Erro ao processar dados extraídos"
            }
    
    def _extract_data_with_regex(self, content: str, username: str, url: str) -> Dict[str, Any]:
        """Extrai dados usando regex quando JSON não está disponível"""
        data = {
            "username": username,
            "profile_url": url
        }
        
        # Padrões regex para extrair informações
        patterns = {
            "name": r'nome[^:]*:?\s*([^\n]+)',
            "bio": r'bio[^:]*:?\s*([^\n]+)',
            "followers": r'seguidores?[^:]*:?\s*([\d.,KMB]+)',
            "following": r'seguindo[^:]*:?\s*([\d.,KMB]+)',
            "likes": r'curtidas?[^:]*:?\s*([\d.,KMB]+)',
            "videos": r'v[íi]deos?[^:]*:?\s*([\d.,KMB]+)',
            "website": r'website[^:]*:?\s*([^\n\s]+)',
            "email": r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            "phone": r'(\+?[\d\s\-\(\)]{10,})',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                data[key] = match.group(1).strip()
        
        return data
    
    def _normalize_tiktok_data(self, data: Dict[str, Any], username: str, url: str) -> Dict[str, Any]:
        """Normaliza os dados extraídos do TikTok"""
        normalized = {
            "username": data.get("username", username),
            "name": data.get("name", data.get("display_name")),
            "bio": data.get("bio", data.get("description")),
            "followers": data.get("followers", data.get("follower_count")),
            "following": data.get("following", data.get("following_count")),
            "likes": data.get("likes", data.get("total_likes")),
            "videos": data.get("videos", data.get("video_count")),
            "website": data.get("website", data.get("link")),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "location": data.get("location"),
            "profile_url": url
        }
        
        # Converter números para inteiros quando possível
        for key in ["followers", "following", "likes", "videos"]:
            if normalized.get(key):
                normalized[f"{key}_count"] = self._convert_to_int(normalized[key])
        
        return normalized
    
    def _convert_to_int(self, value: str) -> Optional[int]:
        """Converte string com sufixos (K, M, B) para inteiro"""
        if not value or not isinstance(value, str):
            return None
        
        try:
            # Remover espaços e converter para minúsculo
            value = value.replace(" ", "").replace(",", "").lower()
            
            # Verificar sufixos
            multipliers = {"k": 1000, "m": 1000000, "b": 1000000000}
            
            for suffix, multiplier in multipliers.items():
                if value.endswith(suffix):
                    number = float(value[:-1])
                    return int(number * multiplier)
            
            # Se não tem sufixo, tentar converter diretamente
            return int(float(value))
            
        except (ValueError, TypeError):
            return None
    
    async def _fallback_puppeteer_scraping(self, url: str, username: str) -> Dict[str, Any]:
        """Fallback usando Puppeteer quando Claude falha"""
        try:
            from ..mcp_client import run_mcp
            
            # Navegar para a página
            await run_mcp(
                "mcp.config.usrlocalmcp.Puppeteer",
                "puppeteer_navigate",
                {"url": url}
            )
            
            # Aguardar carregamento
            await run_mcp(
                "mcp.config.usrlocalmcp.Puppeteer",
                "puppeteer_evaluate",
                {"script": "await new Promise(resolve => setTimeout(resolve, 5000));"}
            )
            
            # Extrair dados com JavaScript
            script = """
            (() => {
                const data = {};
                
                // Tentar extrair dados básicos
                try {
                    // Username
                    const usernameEl = document.querySelector('[data-e2e="user-title"]');
                    if (usernameEl) data.username = usernameEl.textContent.trim();
                    
                    // Nome de exibição
                    const nameEl = document.querySelector('[data-e2e="user-subtitle"]');
                    if (nameEl) data.name = nameEl.textContent.trim();
                    
                    // Bio
                    const bioEl = document.querySelector('[data-e2e="user-bio"]');
                    if (bioEl) data.bio = bioEl.textContent.trim();
                    
                    // Estatísticas
                    const statsEls = document.querySelectorAll('[data-e2e="followers-count"], [data-e2e="following-count"], [data-e2e="likes-count"]');
                    statsEls.forEach(el => {
                        const text = el.textContent.trim();
                        if (el.getAttribute('data-e2e') === 'followers-count') data.followers = text;
                        if (el.getAttribute('data-e2e') === 'following-count') data.following = text;
                        if (el.getAttribute('data-e2e') === 'likes-count') data.likes = text;
                    });
                    
                } catch (e) {
                    console.error('Erro ao extrair dados:', e);
                }
                
                return data;
            })()
            """
            
            result = await run_mcp(
                "mcp.config.usrlocalmcp.Puppeteer",
                "puppeteer_evaluate",
                {"script": script}
            )
            
            if result and "result" in result:
                data = result["result"]
                return self._normalize_tiktok_data(data, username, url)
            else:
                return {
                    "username": username,
                    "profile_url": url,
                    "error": "Falha na extração com Puppeteer"
                }
                
        except Exception as e:
            self.logger.error(f"Erro no fallback Puppeteer: {str(e)}")
            return {
                "username": username,
                "profile_url": url,
                "error": f"Erro no fallback Puppeteer: {str(e)}"
            }