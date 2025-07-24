import scrapy
from ..items import CompanyItem, EmployeeItem
from urllib.parse import urlparse
from scrapy import signals

class LinkedinSpider(scrapy.Spider):
    name = 'linkedin'
    allowed_domains = ['linkedin.com']
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'DOWNLOAD_TIMEOUT': 30,
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'COOKIES_ENABLED': False
    }
    
    def __init__(self, *args, **kwargs):
        super(LinkedinSpider, self).__init__(*args, **kwargs)
        self.start_urls = kwargs.get('start_urls', [])
        self.company_data = kwargs.get('company_data', {})
        self.company_name = self.company_data.get('name', '')
        import os
        from dotenv import load_dotenv
        load_dotenv()
        self.brave_token = os.getenv('BRAVE_SEARCH_TOKEN')
        self.found_data = False
    
    def start_requests(self):
        if not self.company_name and not self.start_urls:
            self.logger.error("Neither company name nor start URLs provided")
            return
    
        # Se temos URLs diretas, use-as primeiro
        if self.start_urls:
            for url in self.start_urls:
                self.logger.info(f"Starting request for direct URL: {url}")
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_company,
                    meta={'handle_httpstatus_list': [404, 403]},
                    errback=self.handle_error,
                    dont_filter=True
                )
            return
    
        # Se não temos URLs diretas mas temos nome da empresa, use a API do Brave
        # Adicionar import no topo
        import time
        import asyncio
    
        # Modificar a seção de requisição para a API do Brave
        if self.company_name and self.brave_token:
            self.logger.info(f"Searching for company {self.company_name} using Brave Search")
            import requests
            
            try:
                # Rate limiting simples para o spider
                time.sleep(1)  # Aguardar 1 segundo entre requisições
                
                # Adicionando timeout de 5 segundos para a API do Brave
                response = requests.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "x-subscription-token": self.brave_token
                    },
                    params={
                        "q": f'"{self.company_name}" site:linkedin.com/company'
                    },
                    timeout=5  # 5 segundos de timeout
                )
                
                if response.status_code == 429:
                    self.logger.warning("Rate limited by Brave API, skipping search")
                    return
                    
                data = response.json()
                
                # Procura pelo primeiro resultado que contenha /company/ na URL
                company_url = None
                for result in response.get('web', {}).get('results', []):
                    url = result.get('url', '')
                    if '/company/' in url:
                        company_url = url
                        break
                
                if company_url:
                    self.logger.info(f"Found company URL via Brave Search: {company_url}")
                    # Retornando imediatamente o resultado
                    self.found_data = True
                    yield CompanyItem(
                        name=self.company_name,
                        linkedin_url=company_url
                    )
                else:
                    self.logger.error("No LinkedIn company page found in Brave Search results")
                    yield CompanyItem(name=self.company_name, error="No company page found")
                    
            except requests.Timeout:
                self.logger.error("Timeout during Brave Search API request")
                yield CompanyItem(name=self.company_name, error="Brave Search API timeout")
            except Exception as e:
                self.logger.error(f"Error during Brave Search API request: {str(e)}")
                yield CompanyItem(name=self.company_name, error=str(e))
    
    
        self.logger.error(f"Request failed: {failure.value}")
        yield CompanyItem(name="Error", error=str(failure.value))
    
    def parse_search_results(self, response):
        self.logger.info(f"Parsing search results from {response.url}")
        if response.status in [404, 403]:
            self.logger.error(f'Error accessing {response.url}: {response.status}')
            yield CompanyItem(name="Error", error=f"HTTP {response.status}")
            return
        
        company_url = response.css('a.company-result-card__link::attr(href)').get()
        if company_url:
            self.logger.info(f"Found company URL: {company_url}")
            yield scrapy.Request(
                url=response.urljoin(company_url),
                callback=self.parse_company,
                cookies=self.cookies,
                meta={'handle_httpstatus_list': [404, 403]},
                errback=self.handle_error,
                dont_filter=True
            )
        else:
            self.logger.error("No company URL found in search results")
            yield CompanyItem(name="Error", error="No company found in search results")
    
    def parse_company(self, response):
        self.logger.info(f"Parsing company page: {response.url}")
        if response.status in [404, 403]:
            self.logger.error(f'Error accessing {response.url}: {response.status}')
            yield CompanyItem(name="Error", error=f"HTTP {response.status}")
            return
        
        company = CompanyItem()
        company['linkedin_url'] = response.url
        company['name'] = (
            response.css('.org-top-card-summary__title::text').get() or
            response.css('.organization-outlet__name::text').get() or
            response.css('h1::text').get() or
            "Unknown Company"
        ).strip()
        
        company['description'] = (
            response.css('.org-about-us-organization-description__text::text').get() or
            response.css('.description__text::text').get() or
            ""
        ).strip()
        
        company['industry'] = (
            response.css('.org-about-company-module__industry::text').get() or
            response.css('.company-industries::text').get() or
            ""
        ).strip()
        
        company['size'] = (
            response.css('.org-about-company-module__company-size-definition-text::text').get() or
            response.css('.staff-count-range::text').get() or
            ""
        ).strip()
        
        website = (
            response.css('.org-about-company-module__company-page-url a::attr(href)').get() or
            response.css('a.link-website::attr(href)').get()
        )
        if website:
            parsed_url = urlparse(website)
            company['website'] = f"https://{parsed_url.netloc}"
        
        self.logger.info(f"Extracted company data: {company}")
        self.found_data = True
        yield company
    
    def closed(self, reason):
        if not self.found_data:
            self.logger.error(f"Spider closed without finding data: {reason}")
            return CompanyItem(name="Error", error=f"No data found: {reason}")