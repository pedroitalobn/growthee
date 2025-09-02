# Firecrawl Client e Integração

Este documento descreve a implementação do cliente Firecrawl e sua integração com o serviço de enriquecimento de empresas.

## Visão Geral

O cliente Firecrawl (`FirecrawlApp`) foi implementado para fornecer duas funcionalidades principais:

1. **Scraping de URLs** - Extração de conteúdo HTML e Markdown de páginas web
2. **Extração de dados estruturados** - Extração de informações específicas usando schemas JSON

## Arquivos Principais

- `api/firecrawl_client.py` - Implementação do cliente Firecrawl
- `api/services.py` - Integração com o serviço de enriquecimento
- `schemas/` - Schemas JSON para extração estruturada
- `scripts/` - Scripts para testes manuais
- `tests/` - Testes automatizados

## Como Usar

### Configuração

1. Configure a API key do Firecrawl no arquivo `.env`:

```
FIRECRAWL_API_KEY=sua_api_key_aqui
```

2. Ou passe a API key diretamente ao instanciar o cliente:

```python
from api.firecrawl_client import FirecrawlApp

firecrawl = FirecrawlApp(api_key="sua_api_key_aqui")
```

### Scraping Básico

```python
result = firecrawl.scrape_url("https://exemplo.com")
html_content = result["html"]
markdown_content = result["markdown"]
```

### Extração Estruturada

```python
# Definir schema
schema = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "linkedin_url": {"type": "string"}
    }
}

# Extrair dados estruturados
result = firecrawl.extract_structured_data("https://exemplo.com", schema)
company_name = result.get("company_name")
linkedin_url = result.get("linkedin_url")
```

## Scripts de Teste

### Teste Manual

O script `scripts/test_firecrawl.py` permite testar o cliente Firecrawl manualmente:

```bash
# Scraping básico
python scripts/test_firecrawl.py --url "https://exemplo.com" --output results/resultado.json

# Extração estruturada
python scripts/test_firecrawl.py --url "https://exemplo.com" --schema schemas/company_schema.json --output results/empresa.json
```

### Testes de Integração

Execute os testes de integração com:

```bash
bash scripts/run_integration_tests.sh
```

Ou diretamente com:

```bash
python -m unittest tests/test_firecrawl_integration.py
```

## Schemas Disponíveis

- `schemas/company_schema.json` - Extração de informações completas de empresas
- `schemas/linkedin_schema.json` - Extração apenas de URLs do LinkedIn

## Integração com o Serviço de Enriquecimento

O cliente Firecrawl está integrado ao serviço de enriquecimento em `api/services.py`. Os principais métodos que utilizam o cliente são:

- `_scrape_with_firecrawl` - Método base para scraping e extração estruturada
- `_find_linkedin_on_website_firecrawl` - Extração de URLs do LinkedIn de sites
- `_enrich_company_with_website` - Enriquecimento de dados de empresas a partir de seus sites

## Notas de Implementação

- O cliente suporta tanto a extração de conteúdo HTML/Markdown quanto a extração estruturada baseada em schemas
- A extração estruturada utiliza LLMs para interpretar o conteúdo da página e extrair dados específicos
- O cliente inclui tratamento de erros e logging para facilitar a depuração
- Os parâmetros padrão foram otimizados para extração de dados de empresas