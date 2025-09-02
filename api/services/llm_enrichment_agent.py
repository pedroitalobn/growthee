import os
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class LLMEnrichmentAgent:
    """Agente de enriquecimento de dados usando LLMs"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat"):
        """Inicializa o agente LLM para enriquecimento de dados
        
        Args:
            api_key: Chave de API para o serviço LLM (se None, tenta obter de DEEPSEEK_API_KEY)
            model: Modelo LLM a ser usado
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        
        logger.info(f"LLM Enrichment Agent inicializado com modelo {self.model}")
        if self.api_key:
            logger.info("API key para DeepSeek configurada com sucesso")
        else:
            logger.warning("API key para DeepSeek não encontrada")
        
        if not self.api_key:
            logger.warning("API key não encontrada para o LLM. O enriquecimento de dados pode falhar.")
    
    async def extract_company_info_from_html(self, html_content: str, domain: str) -> Dict[str, Any]:
        """Extrai informações da empresa a partir do HTML do site usando LLM
        
        Args:
            html_content: Conteúdo HTML do site da empresa
            domain: Domínio do site da empresa
            
        Returns:
            Dicionário com informações extraídas da empresa
        """
        try:
            # Limpar e preparar o HTML para processamento
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remover scripts, estilos e tags desnecessárias para reduzir o tamanho
            for script in soup(["script", "style", "iframe", "noscript"]):
                script.extract()
            
            # Extrair texto principal
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Limitar o tamanho do texto para evitar exceder limites de tokens
            max_text_length = 8000
            if len(text_content) > max_text_length:
                text_content = text_content[:max_text_length]
            
            # Extrair meta tags relevantes
            meta_tags = {}
            for meta in soup.find_all('meta'):
                if meta.get('name') and meta.get('content'):
                    meta_tags[meta['name']] = meta['content']
                elif meta.get('property') and meta.get('content'):
                    meta_tags[meta['property']] = meta['content']
            
            # Construir prompt para o LLM
            prompt = f"""Você é um especialista em extração de informações de empresas.
            Analise o conteúdo do site da empresa com domínio '{domain}' e extraia as seguintes informações:
            
            1. Nome da empresa
            2. Descrição da empresa
            3. Indústria/setor
            4. Tamanho da empresa (pequena, média, grande)
            5. Ano de fundação
            6. Sede (localização principal)
            7. País
            8. Região/Estado
            9. Cidade
            10. Produtos ou serviços principais
            11. Valores da empresa
            
            Meta tags do site: {json.dumps(meta_tags, ensure_ascii=False)}
            
            Conteúdo do site:
            {text_content}
            
            Responda APENAS com um objeto JSON contendo os campos: name, description, industry, size, founded, headquarters, country, region, city, products_services, company_values. Se não encontrar alguma informação, deixe o campo como null.
            """
            
            # Chamar a API do LLM
            response = await self._call_llm_api(prompt)
            
            # Processar a resposta
            if response:
                try:
                    # Extrair o JSON da resposta
                    json_str = response.strip()
                    if json_str.startswith('```json'):
                        json_str = json_str.split('```json')[1].split('```')[0].strip()
                    elif json_str.startswith('```'):
                        json_str = json_str.split('```')[1].split('```')[0].strip()
                    
                    # Converter para dicionário
                    result = json.loads(json_str)
                    logger.info(f"LLM extraiu informações para {domain}: {result.keys()}")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar JSON da resposta do LLM: {e}")
                    logger.debug(f"Resposta do LLM: {response}")
            
            return {}
        except Exception as e:
            logger.error(f"Erro ao extrair informações com LLM: {e}")
            return {}
    
    async def _call_llm_api(self, prompt: str) -> Optional[str]:
        """Chama a API do LLM para processar o prompt
        
        Args:
            prompt: Texto do prompt para o LLM
            
        Returns:
            Resposta do LLM ou None em caso de erro
        """
        if not self.api_key:
            logger.error("API key não configurada para o LLM")
            return None
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Você é um assistente especializado em extrair informações estruturadas de textos sobre empresas."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,  # Baixa temperatura para respostas mais determinísticas
                "max_tokens": 1000
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.error(f"Resposta inesperada da API do LLM: {result}")
                    return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP ao chamar API do LLM: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Erro ao chamar API do LLM: {e}")
            return None