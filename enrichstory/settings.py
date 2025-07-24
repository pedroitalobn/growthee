BOT_NAME = 'enrichstory'

SPIDER_MODULES = ['enrichstory.spiders']
NEWSPIDER_MODULE = 'enrichstory.spiders'

# Configurações de crawling
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = 1  # Reduzido para 1 segundo
CONCURRENT_REQUESTS = 8  # Aumentado para 8

# Configurações do Tor
TOR_ENABLED = False  # Desabilitado temporariamente
TOR_PROXY_SETTINGS = {
    'http': 'http://127.0.0.1:8118',  # Privoxy
    'https': 'http://127.0.0.1:8118'
}

# Middleware para rotação de IP
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
    'enrichstory.middlewares.TorProxyMiddleware': 100,
}
