import os
import json
import logging
import httpx
import asyncio
from typing import Dict, Any, Optional, List, Union
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class CompanyEnrichmentResult:
    """Resultado estruturado do enriquecimento de dados da empresa"""
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    founded: Optional[str] = None
    headquarters: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    products_services: Optional[List[str]] = None
    company_values: Optional[List[str]] = None
    employee_count: Optional[int] = None
    revenue: Optional[str] = None
    website: Optional[str] = None
    social_media: Optional[Dict[str, str]] = None
    confidence_score: float = 0.0
    extraction_method: str = "llm"
    processing_time: float = 0.0

class EnhancedLLMEnrichmentAgent:
    """Agente LLM aprimorado para enriquecimento de dados empresariais"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "deepseek-chat", fallback_model: str = "gpt-3.5-turbo"):
        """Inicializa o agente LLM aprimorado
        
        Args:
            api_key: Chave de API para o serviço LLM principal
            model: Modelo LLM principal
            fallback_model: Modelo de fallback
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.fallback_model = fallback_model
        self.deepseek_api_url = "https://api.deepseek.com/v1/chat/completions"
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
        
        # Configurações de retry e timeout
        self.max_retries = 3
        self.timeout = 60.0
        self.max_tokens = 2000
        
        logger.info(f"Enhanced LLM Agent inicializado - Modelo principal: {self.model}")
        
        if not self.api_key and not self.openai_api_key:
            logger.warning("Nenhuma API key encontrada. O enriquecimento pode falhar.")
    
    async def extract_company_info_from_html(self, html_content: str, domain: str, context: Dict[str, Any] = None) -> CompanyEnrichmentResult:
        """Extrai informações da empresa usando LLM com estratégias aprimoradas
        
        Args:
            html_content: Conteúdo HTML do site
            domain: Domínio da empresa
            context: Contexto adicional (dados já extraídos, etc.)
            
        Returns:
            Resultado estruturado do enriquecimento
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Pré-processar HTML
            processed_content = await self._preprocess_html(html_content)
            
            # Construir prompt otimizado
            prompt = await self._build_enhanced_prompt(processed_content, domain, context)
            
            # Tentar extração com modelo principal
            result = await self._extract_with_primary_model(prompt)
            
            # Fallback se necessário
            if not result or result.confidence_score < 0.3:
                logger.info("Tentando fallback com modelo secundário")
                fallback_result = await self._extract_with_fallback_model(prompt)
                if fallback_result and fallback_result.confidence_score > result.confidence_score:
                    result = fallback_result
            
            # Pós-processamento e validação
            if result:
                result = await self._post_process_result(result, domain)
                result.processing_time = asyncio.get_event_loop().time() - start_time
            
            return result or CompanyEnrichmentResult()
            
        except Exception as e:
            logger.error(f"Erro no enriquecimento LLM: {e}")
            return CompanyEnrichmentResult()
    
    async def _preprocess_html(self, html_content: str) -> Dict[str, Any]:
        """Pré-processa HTML para extração otimizada"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remover elementos desnecessários
            for tag in soup(["script", "style", "iframe", "noscript", "nav", "footer", "aside"]):
                tag.extract()
            
            # Extrair seções importantes
            processed = {
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'headings': self._extract_headings(soup),
                'main_content': self._extract_main_content(soup),
                'contact_info': self._extract_contact_info(soup),
                'structured_data': self._extract_structured_data(soup),
                'key_sections': self._extract_key_sections(soup)
            }
            
            return processed
            
        except Exception as e:
            logger.error(f"Erro no pré-processamento: {e}")
            return {'raw_text': BeautifulSoup(html_content, 'html.parser').get_text()[:5000]}
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extrai título da página"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else ""
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extrai meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})
        return meta_desc.get('content', '').strip() if meta_desc else ""
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[str]:
        """Extrai cabeçalhos importantes"""
        headings = []
        for tag in soup.find_all(['h1', 'h2', 'h3']):
            text = tag.get_text().strip()
            if text and len(text) > 3:
                headings.append(text)
        return headings[:10]  # Limitar a 10 cabeçalhos
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extrai conteúdo principal da página"""
        # Tentar encontrar conteúdo principal
        main_selectors = [
            'main', '[role="main"]', '.main-content', '#main-content',
            '.content', '#content', '.page-content', '.entry-content'
        ]
        
        for selector in main_selectors:
            main_element = soup.select_one(selector)
            if main_element:
                text = main_element.get_text(separator='\n', strip=True)
                if len(text) > 100:
                    return text[:3000]  # Limitar tamanho
        
        # Fallback: pegar todo o texto do body
        body = soup.find('body')
        if body:
            return body.get_text(separator='\n', strip=True)[:3000]
        
        return soup.get_text(separator='\n', strip=True)[:3000]
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrai informações de contato"""
        contact_info = {}
        text = soup.get_text()
        
        # Email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['email'] = emails[0]
        
        # Telefone
        phone_pattern = r'\+?[1-9]\d{1,14}|\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}'
        phones = re.findall(phone_pattern, text)
        if phones:
            contact_info['phone'] = phones[0]
        
        # Endereço (padrões simples)
        address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)',
            r'[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}'
        ]
        
        for pattern in address_patterns:
            addresses = re.findall(pattern, text, re.IGNORECASE)
            if addresses:
                contact_info['address'] = addresses[0]
                break
        
        return contact_info
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai dados estruturados (JSON-LD, microdata)"""
        structured_data = {}
        
        # JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Organization':
                    structured_data.update(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Organization':
                            structured_data.update(item)
            except json.JSONDecodeError:
                continue
        
        return structured_data
    
    def _extract_key_sections(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrai seções-chave da página"""
        sections = {}
        
        # Seções comuns
        section_selectors = {
            'about': ['.about', '#about', '[class*="about"]', 'section:contains("About")'],
            'services': ['.services', '#services', '[class*="service"]', 'section:contains("Services")'],
            'products': ['.products', '#products', '[class*="product"]', 'section:contains("Products")'],
            'team': ['.team', '#team', '[class*="team"]', 'section:contains("Team")'],
            'history': ['.history', '#history', '[class*="history"]', 'section:contains("History")']
        }
        
        for section_name, selectors in section_selectors.items():
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        text = element.get_text(strip=True)
                        if len(text) > 50:
                            sections[section_name] = text[:500]
                            break
                except Exception:
                    continue
        
        return sections
    
    async def _build_enhanced_prompt(self, processed_content: Dict[str, Any], domain: str, context: Dict[str, Any] = None) -> str:
        """Constrói prompt otimizado para extração"""
        
        # Informações de contexto
        context_info = ""
        if context:
            context_info = f"\nContexto adicional: {json.dumps(context, ensure_ascii=False, indent=2)}"
        
        # Dados estruturados se disponíveis
        structured_info = ""
        if processed_content.get('structured_data'):
            structured_info = f"\nDados estruturados encontrados: {json.dumps(processed_content['structured_data'], ensure_ascii=False, indent=2)}"
        
        prompt = f"""Você é um especialista em análise de dados empresariais. Analise o conteúdo do site da empresa com domínio '{domain}' e extraia informações precisas e estruturadas.

**INSTRUÇÕES IMPORTANTES:**
1. Seja preciso e factual - não invente informações
2. Se uma informação não estiver clara, deixe o campo como null
3. Para listas, forneça arrays JSON válidos
4. Para números, use apenas valores numéricos
5. Responda APENAS com JSON válido, sem texto adicional

**DADOS DO SITE:**

Título: {processed_content.get('title', '')}
Meta Description: {processed_content.get('meta_description', '')}

Cabeçalhos principais:
{chr(10).join(processed_content.get('headings', [])[:5])}

Conteúdo principal:
{processed_content.get('main_content', '')[:2000]}

Informações de contato:
{json.dumps(processed_content.get('contact_info', {}), ensure_ascii=False)}

Seções-chave:
{json.dumps(processed_content.get('key_sections', {}), ensure_ascii=False)}{structured_info}{context_info}

**FORMATO DE RESPOSTA (JSON):**
{{
  "name": "Nome oficial da empresa",
  "description": "Descrição clara e concisa da empresa (50-200 palavras)",
  "industry": "Setor/indústria principal",
  "size": "small|medium|large|enterprise",
  "founded": "Ano de fundação (YYYY)",
  "headquarters": "Localização da sede principal",
  "country": "País",
  "region": "Estado/região",
  "city": "Cidade",
  "products_services": ["Lista de produtos/serviços principais"],
  "company_values": ["Lista de valores da empresa"],
  "employee_count": "Número estimado de funcionários (apenas número)",
  "revenue": "Receita anual estimada (se mencionada)",
  "website": "URL do site principal",
  "social_media": {{
    "linkedin": "URL do LinkedIn",
    "twitter": "URL do Twitter",
    "facebook": "URL do Facebook"
  }}
}}

Resposta JSON:"""
        
        return prompt
    
    async def _extract_with_primary_model(self, prompt: str) -> Optional[CompanyEnrichmentResult]:
        """Extração usando modelo principal (DeepSeek)"""
        if not self.api_key:
            return None
        
        try:
            response = await self._call_api(
                self.deepseek_api_url,
                self.api_key,
                prompt,
                self.model
            )
            
            if response:
                return await self._parse_llm_response(response, "deepseek")
                
        except Exception as e:
            logger.error(f"Erro no modelo principal: {e}")
        
        return None
    
    async def _extract_with_fallback_model(self, prompt: str) -> Optional[CompanyEnrichmentResult]:
        """Extração usando modelo de fallback (OpenAI)"""
        if not self.openai_api_key:
            return None
        
        try:
            response = await self._call_api(
                self.openai_api_url,
                self.openai_api_key,
                prompt,
                self.fallback_model
            )
            
            if response:
                return await self._parse_llm_response(response, "openai")
                
        except Exception as e:
            logger.error(f"Erro no modelo de fallback: {e}")
        
        return None
    
    async def _call_api(self, api_url: str, api_key: str, prompt: str, model: str) -> Optional[str]:
        """Chama API do LLM com retry e tratamento de erros"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um especialista em análise de dados empresariais. Sempre responda com JSON válido e estruturado."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"} if "gpt" in model else None
        }
        
        # Remover response_format se não suportado
        if "deepseek" in model.lower():
            payload.pop("response_format", None)
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(api_url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Erro HTTP (tentativa {attempt + 1}): {e.response.status_code}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Backoff exponencial
                
            except Exception as e:
                logger.error(f"Erro na API (tentativa {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def _parse_llm_response(self, response: str, model_type: str) -> Optional[CompanyEnrichmentResult]:
        """Parseia resposta do LLM e converte para resultado estruturado"""
        try:
            # Limpar resposta
            json_str = response.strip()
            
            # Remover markdown se presente
            if json_str.startswith('```json'):
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif json_str.startswith('```'):
                json_str = json_str.split('```')[1].split('```')[0].strip()
            
            # Parsear JSON
            data = json.loads(json_str)
            
            # Converter para resultado estruturado
            result = CompanyEnrichmentResult(
                name=data.get('name'),
                description=data.get('description'),
                industry=data.get('industry'),
                size=data.get('size'),
                founded=data.get('founded'),
                headquarters=data.get('headquarters'),
                country=data.get('country'),
                region=data.get('region'),
                city=data.get('city'),
                products_services=data.get('products_services'),
                company_values=data.get('company_values'),
                employee_count=self._parse_employee_count(data.get('employee_count')),
                revenue=data.get('revenue'),
                website=data.get('website'),
                social_media=data.get('social_media'),
                extraction_method=f"llm_{model_type}"
            )
            
            # Calcular score de confiança
            result.confidence_score = self._calculate_confidence_score(result)
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao parsear JSON: {e}")
            logger.debug(f"Resposta recebida: {response}")
            return None
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return None
    
    def _parse_employee_count(self, value: Any) -> Optional[int]:
        """Converte valor de contagem de funcionários para inteiro"""
        if value is None:
            return None
        
        try:
            if isinstance(value, int):
                return value
            elif isinstance(value, str):
                # Remover caracteres não numéricos
                numbers = re.sub(r'[^0-9]', '', value)
                return int(numbers) if numbers else None
        except (ValueError, TypeError):
            pass
        
        return None
    
    async def _post_process_result(self, result: CompanyEnrichmentResult, domain: str) -> CompanyEnrichmentResult:
        """Pós-processa e valida resultado"""
        # Validar e limpar campos
        if result.name:
            result.name = result.name.strip()[:200]
        
        if result.description:
            result.description = result.description.strip()[:2000]
        
        if result.founded:
            # Validar ano
            year_match = re.search(r'(19|20)\d{2}', str(result.founded))
            if year_match:
                year = int(year_match.group())
                result.founded = str(year) if 1800 <= year <= 2024 else None
            else:
                result.founded = None
        
        # Validar tamanho da empresa
        if result.size and result.size not in ['small', 'medium', 'large', 'enterprise']:
            result.size = None
        
        # Garantir que website inclua o domínio se não especificado
        if not result.website:
            result.website = f"https://{domain}"
        
        # Validar URLs de redes sociais
        if result.social_media:
            validated_social = {}
            for platform, url in result.social_media.items():
                if url and self._is_valid_url(url):
                    validated_social[platform] = url
            result.social_media = validated_social if validated_social else None
        
        return result
    
    def _is_valid_url(self, url: str) -> bool:
        """Valida se uma string é uma URL válida"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
        except Exception:
            return False
    
    def _calculate_confidence_score(self, result: CompanyEnrichmentResult) -> float:
        """Calcula score de confiança baseado na completude dos dados"""
        # Pesos dos campos
        field_weights = {
            'name': 0.20,
            'description': 0.15,
            'industry': 0.12,
            'size': 0.08,
            'founded': 0.08,
            'headquarters': 0.10,
            'country': 0.05,
            'products_services': 0.10,
            'employee_count': 0.07,
            'website': 0.05
        }
        
        total_score = 0.0
        
        for field, weight in field_weights.items():
            value = getattr(result, field, None)
            if value:
                if isinstance(value, list) and len(value) > 0:
                    total_score += weight
                elif isinstance(value, str) and len(value.strip()) > 0:
                    total_score += weight
                elif isinstance(value, (int, float)) and value > 0:
                    total_score += weight
        
        return round(total_score * 100, 2)
    
    async def enrich_missing_linkedin_data(self, existing_data: Dict[str, Any], html_content: str, domain: str) -> Dict[str, Any]:
        """Enriquece dados quando LinkedIn não está disponível"""
        try:
            # Identificar campos faltantes
            missing_fields = []
            important_fields = ['company_name', 'description', 'industry', 'employee_count', 'headquarters']
            
            for field in important_fields:
                if not existing_data.get(field):
                    missing_fields.append(field)
            
            if not missing_fields:
                return existing_data
            
            # Extrair dados usando LLM
            enrichment_result = await self.extract_company_info_from_html(html_content, domain, existing_data)
            
            # Mesclar dados
            enriched_data = existing_data.copy()
            
            field_mapping = {
                'company_name': 'name',
                'description': 'description',
                'industry': 'industry',
                'employee_count': 'employee_count',
                'headquarters': 'headquarters',
                'founded': 'founded'
            }
            
            for existing_field, result_field in field_mapping.items():
                if existing_field in missing_fields:
                    value = getattr(enrichment_result, result_field, None)
                    if value:
                        enriched_data[existing_field] = value
            
            # Adicionar informações de enriquecimento
            enriched_data['llm_enrichment'] = {
                'confidence_score': enrichment_result.confidence_score,
                'fields_enriched': [f for f in missing_fields if enriched_data.get(f)],
                'processing_time': enrichment_result.processing_time
            }
            
            return enriched_data
            
        except Exception as e:
            logger.error(f"Erro no enriquecimento de dados: {e}")
            return existing_data