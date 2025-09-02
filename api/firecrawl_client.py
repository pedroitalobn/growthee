from typing import Dict, Any, List, Optional, Union
import requests
import json
import os
from bs4 import BeautifulSoup
import logging
import time

class FirecrawlApp:
    """Cliente para a API Firecrawl"""
    
    def __init__(self, api_key: str = None):
        """Inicializa o cliente Firecrawl"""
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.base_url_v1 = "https://api.firecrawl.dev/v1"
        self.base_url_v2 = "https://api.firecrawl.dev/v2"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def scrape_url(self, url: str, params: Dict[str, Any] = None) -> Union[Dict[str, Any], List[str], str]:
        """Faz scraping de uma URL usando Firecrawl v2"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        endpoint = f"{self.base_url_v2}/scrape"
        
        # Parâmetros padrão se não fornecidos
        payload = {"url": url}
        if params:
            payload.update(params)
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Verificar se a resposta foi bem-sucedida
            if result.get("success") and "data" in result:
                return result["data"]
            else:
                error_msg = result.get("error", "Unknown error")
                logging.error(f"Firecrawl scraping error: {error_msg}")
                return {"error": error_msg}
                
        except Exception as e:
            logging.error(f"Firecrawl scraping error: {e}")
            return {"error": str(e)}
            
    def scrape_url_v1(self, url: str, params: Dict[str, Any] = None) -> Union[Dict[str, Any], List[str], str]:
        """Faz scraping de uma URL usando Firecrawl v1 (legado)"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        endpoint = f"{self.base_url_v1}/scrape"
        
        # Parâmetros padrão se não fornecidos
        if not params:
            params = {
                'formats': ['html', 'markdown'],
                'includeTags': ['div', 'span', 'p', 'h1', 'h2', 'h3', 'a', 'meta'],
                'excludeTags': ['script', 'style', 'nav', 'footer'],
                'waitFor': 3000,
                'timeout': 30000
            }
        
        payload = {
            "url": url,
            **params
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Verificar se o resultado é uma lista de formatos
            if isinstance(result, list):
                return result
            # Verificar se é um objeto com atributos específicos
            elif isinstance(result, dict):
                return result
            # Fallback para string
            else:
                return str(result)
                
        except Exception as e:
            logging.error(f"Firecrawl v1 scraping error: {e}")
            return {"error": str(e)}
    
    def extract_structured_data(self, url: str, schema: Dict[str, Any], prompt: str = None, use_deepseek: bool = True) -> Dict[str, Any]:
        """Extrai dados estruturados de uma URL usando schema com a API v2"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        endpoint = f"{self.base_url_v2}/extract"
        
        # Configurar o payload para a API v2
        payload = {
            "urls": [url],
            "schema": schema
        }
        
        # Adicionar prompt se fornecido
        if prompt:
            payload["prompt"] = prompt
        
        try:
            # Iniciar a extração
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Verificar se a extração foi iniciada com sucesso
            if result.get("success") and "id" in result:
                extraction_id = result["id"]
                
                # Aguardar a conclusão da extração
                return self._wait_for_extraction_result(extraction_id)
            else:
                error_msg = result.get("error", "Unknown error")
                logging.error(f"Firecrawl extraction error: {error_msg}")
                return {"error": error_msg}
                
        except Exception as e:
            logging.error(f"Firecrawl extraction error: {e}")
            return {"error": str(e)}
            
    def _wait_for_extraction_result(self, extraction_id: str, max_retries: int = 10, retry_delay: int = 2) -> Dict[str, Any]:
        """Aguarda e recupera o resultado da extração"""
        endpoint = f"{self.base_url_v2}/extract/{extraction_id}"
        
        for attempt in range(max_retries):
            try:
                response = requests.get(endpoint, headers=self.headers)
                response.raise_for_status()
                
                result = response.json()
                
                # Verificar se a extração foi concluída
                if result.get("status") == "completed":
                    if result.get("success") and "data" in result:
                        return result["data"]
                    else:
                        return {"error": "Extraction completed but no data available"}
                        
                # Se ainda estiver em andamento, aguardar e tentar novamente
                time.sleep(retry_delay)
                
            except Exception as e:
                logging.error(f"Error checking extraction status: {e}")
                time.sleep(retry_delay)
        
        return {"error": "Extraction timed out or failed"}
        
    def extract_structured_data_v1(self, url: str, schema: Dict[str, Any], use_deepseek: bool = True) -> Dict[str, Any]:
        """Extrai dados estruturados de uma URL usando schema com a API v1 (legado)"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        endpoint = f"{self.base_url_v1}/extract"
        
        # Configurar o método de extração para usar DeepSeek se solicitado
        extraction_method = "deepseek" if use_deepseek else "llm"
        
        payload = {
            "url": url,
            "schema": schema,
            "options": {
                "waitFor": 3000,
                "timeout": 45000,
                "extractionMethod": extraction_method,
                "includeTags": ["div", "span", "p", "h1", "h2", "h3", "a", "meta", "script"],
                "excludeTags": ["nav", "footer", "aside"],
                "onlyMainContent": False
            }
        }
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Verificar se o resultado é um objeto com os dados extraídos
            if isinstance(result, dict):
                return result
            else:
                return {"error": "Unexpected response format"}
                
        except Exception as e:
            logging.error(f"Firecrawl v1 extraction error: {e}")
            return {"error": str(e)}
    
    def extract_structured_data_from_html(self, html_content: str, schema: Dict[str, Any], prompt: str = None) -> Dict[str, Any]:
        """Extrai dados estruturados de conteúdo HTML usando schema com a API v2"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        # Para a API v2, precisamos primeiro criar uma URL temporária para o conteúdo HTML
        # Vamos usar a API v1 para este caso específico, pois a v2 não suporta diretamente HTML
        return self.extract_structured_data_from_html_v1(html_content, schema)
            
    def extract_structured_data_from_html_v1(self, html_content: str, schema: Dict[str, Any], use_deepseek: bool = True) -> Dict[str, Any]:
        """Extrai dados estruturados de conteúdo HTML usando schema com a API v1 (legado)"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        # Vamos usar o método de scrape para obter o conteúdo e depois extrair os dados
        try:
            # Primeiro, vamos criar um arquivo temporário com o HTML
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
                temp_file.write(html_content.encode('utf-8'))
                temp_path = temp_file.name
            
            # Agora vamos extrair os dados do HTML usando regex ou processamento simples
            # Esta é uma solução temporária até resolvermos o problema com a API
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extrair dados básicos com base no schema
            result = {}
            
            # Tentar extrair título
            if 'title' in schema.get('properties', {}):
                title_tag = soup.find('title')
                if title_tag:
                    result['title'] = title_tag.text.strip()
                else:
                    h1_tag = soup.find('h1')
                    if h1_tag:
                        result['title'] = h1_tag.text.strip()
            
            # Tentar extrair conteúdo principal
            if 'content' in schema.get('properties', {}) or 'mainText' in schema.get('properties', {}):
                content = []
                for p in soup.find_all('p'):
                    content.append(p.text.strip())
                
                main_text = ' '.join(content)
                if 'content' in schema.get('properties', {}):
                    result['content'] = main_text
                if 'mainText' in schema.get('properties', {}):
                    result['mainText'] = main_text
            
            # Tentar extrair autor
            if 'author' in schema.get('properties', {}):
                author_tag = soup.find(class_='author') or soup.find(class_='byline')
                if author_tag:
                    result['author'] = author_tag.text.strip()
            
            # Tentar extrair data
            if 'date' in schema.get('properties', {}):
                date_tag = soup.find(class_='date') or soup.find('time')
                if date_tag:
                    result['date'] = date_tag.text.strip()
            
            # Limpar o arquivo temporário
            os.unlink(temp_path)
            
            return result
                
        except Exception as e:
            logging.error(f"HTML extraction error: {e}")
            return {"error": str(e)}