from typing import Dict, Any, List, Optional, Union
import requests
import json
import os
from bs4 import BeautifulSoup
import logging

class FirecrawlApp:
    """Cliente para a API Firecrawl"""
    
    def __init__(self, api_key: str = None):
        """Inicializa o cliente Firecrawl"""
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.base_url = "https://api.firecrawl.dev/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def scrape_url(self, url: str, params: Dict[str, Any] = None) -> Union[Dict[str, Any], List[str], str]:
        """Faz scraping de uma URL usando Firecrawl"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        endpoint = f"{self.base_url}/scrape"
        
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
            logging.error(f"Firecrawl scraping error: {e}")
            return {"error": str(e)}
    
    def extract_structured_data(self, url: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados estruturados de uma URL usando schema"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        endpoint = f"{self.base_url}/extract"
        
        payload = {
            "url": url,
            "schema": schema,
            "options": {
                "waitFor": 3000,
                "timeout": 45000,
                "extractionMethod": "llm",
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
            logging.error(f"Firecrawl extraction error: {e}")
            return {"error": str(e)}
    
    def extract_structured_data_from_html(self, html_content: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extrai dados estruturados de conteúdo HTML usando schema"""
        if not self.api_key:
            raise ValueError("API key is required")
        
        # Usar o endpoint extract com o conteúdo HTML
        endpoint = f"{self.base_url}/extract"
        
        # Criar uma URL temporária para o conteúdo HTML
        temp_url = "https://example.com/temp-content"
        
        payload = {
            "url": temp_url,  # URL temporária
            "html": html_content,  # Conteúdo HTML
            "schema": schema,
            "options": {
                "waitFor": 1000,
                "timeout": 30000,
                "extractionMethod": "llm",
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
            logging.error(f"Firecrawl HTML extraction error: {e}")
            return {"error": str(e)}