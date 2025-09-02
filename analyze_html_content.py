#!/usr/bin/env python3

import os
import re
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from bs4 import BeautifulSoup

def analyze_html_content():
    """Analisa o conteúdo HTML capturado para encontrar redes sociais"""
    
    # Carregar variáveis de ambiente
    load_dotenv()
    
    try:
        # Configurar Firecrawl
        firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        if not firecrawl_api_key:
            print("❌ FIRECRAWL_API_KEY não encontrada")
            return
            
        firecrawl_app = FirecrawlApp(api_key=firecrawl_api_key)
        
        # Fazer scraping da página principal
        url = "https://rvb.com.br"
        print(f"🔍 Analisando URL: {url}")
        
        scraped_data = firecrawl_app.scrape_url(
            url,
            formats=['markdown', 'html']
        )
        
        html_content = getattr(scraped_data, 'html', '') or ''
        if not html_content:
            print("❌ Nenhum HTML capturado")
            return
            
        print(f"📄 HTML capturado: {len(html_content)} caracteres")
        
        # Salvar HTML completo
        with open('rvb_html_complete.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("💾 HTML completo salvo em 'rvb_html_complete.html'")
        
        # Análise detalhada
        print("\n" + "="*50)
        print("🔍 ANÁLISE DETALHADA DO HTML")
        print("="*50)
        
        # 1. Buscar por padrões mais amplos
        social_keywords = ['instagram', 'linkedin', 'facebook', 'whatsapp', 'twitter', 'youtube', 'tiktok']
        
        print("\n1️⃣ Buscando palavras-chave de redes sociais:")
        for keyword in social_keywords:
            count = html_content.lower().count(keyword)
            if count > 0:
                print(f"   - {keyword}: {count} ocorrências")
                
                # Mostrar contexto das primeiras 3 ocorrências
                start = 0
                for i in range(min(3, count)):
                    pos = html_content.lower().find(keyword, start)
                    if pos != -1:
                        context_start = max(0, pos - 50)
                        context_end = min(len(html_content), pos + len(keyword) + 50)
                        context = html_content[context_start:context_end]
                        print(f"     Contexto {i+1}: ...{context}...")
                        start = pos + 1
        
        # 2. Buscar por URLs completas
        print("\n2️⃣ Buscando URLs de redes sociais:")
        url_patterns = {
            'Instagram': r'https?://(?:www\.)?instagram\.com/[^\s"\'>]+',
            'LinkedIn': r'https?://(?:www\.)?linkedin\.com/[^\s"\'>]+',
            'Facebook': r'https?://(?:www\.)?facebook\.com/[^\s"\'>]+',
            'WhatsApp': r'https?://(?:wa\.me/|api\.whatsapp\.com/)[^\s"\'>]+',
            'Twitter/X': r'https?://(?:www\.)?(twitter\.com|x\.com)/[^\s"\'>]+',
            'YouTube': r'https?://(?:www\.)?youtube\.com/[^\s"\'>]+'
        }
        
        for platform, pattern in url_patterns.items():
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                print(f"   - {platform}: {len(matches)} URLs encontradas")
                for match in matches[:3]:  # Primeiras 3
                    print(f"     * {match}")
        
        # 3. Analisar elementos específicos
        print("\n3️⃣ Analisando elementos HTML específicos:")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Links
        all_links = soup.find_all('a', href=True)
        print(f"   - Total de links <a>: {len(all_links)}")
        
        social_links = []
        for link in all_links:
            href = link.get('href', '').lower()
            if any(social in href for social in social_keywords):
                social_links.append(link.get('href'))
        
        if social_links:
            print(f"   - Links sociais encontrados: {len(social_links)}")
            for link in social_links[:5]:
                print(f"     * {link}")
        else:
            print("   - Nenhum link social encontrado")
        
        # Scripts e dados estruturados
        scripts = soup.find_all('script')
        print(f"   - Total de scripts: {len(scripts)}")
        
        for i, script in enumerate(scripts[:10]):  # Primeiros 10 scripts
            script_content = script.get_text() or ''
            if any(social in script_content.lower() for social in social_keywords):
                print(f"     Script {i+1} contém redes sociais:")
                for keyword in social_keywords:
                    if keyword in script_content.lower():
                        print(f"       - {keyword}")
        
        # 4. Buscar em atributos específicos
        print("\n4️⃣ Buscando em atributos específicos:")
        
        # data-* attributes
        elements_with_data = soup.find_all(attrs=lambda x: x and any(attr.startswith('data-') for attr in x.keys()))
        print(f"   - Elementos com atributos data-*: {len(elements_with_data)}")
        
        for elem in elements_with_data[:20]:  # Primeiros 20
            for attr, value in elem.attrs.items():
                if attr.startswith('data-') and isinstance(value, str):
                    if any(social in value.lower() for social in social_keywords):
                        print(f"     * {attr}=\"{value}\"")
        
        # class attributes
        elements_with_social_classes = soup.find_all(class_=lambda x: x and any(social in ' '.join(x).lower() for social in social_keywords))
        if elements_with_social_classes:
            print(f"   - Elementos com classes sociais: {len(elements_with_social_classes)}")
            for elem in elements_with_social_classes[:5]:
                print(f"     * {elem.get('class')}")
        
        print("\n✅ Análise completa! Verifique o arquivo 'rvb_html_complete.html' para mais detalhes.")
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_html_content()