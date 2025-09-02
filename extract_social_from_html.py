#!/usr/bin/env python3

import json
import re
from bs4 import BeautifulSoup

def extract_social_media_from_html():
    """Extrai redes sociais do HTML capturado do site rvb.com.br"""
    
    # HTML capturado do site (truncado para o exemplo)
    html_content = '''<!DOCTYPE html><html lang="pt-BR"><head><script data-no-optimize="1">var litespeed_docref=sessionStorage.getItem("litespeed_docref");litespeed_docref&&(Object.defineProperty(document,"referrer",{get:function(){return litespeed_docref}}),sessionStorage.removeItem("litespeed_docref"));</script> <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><meta http-equiv="X-UA-Compatible" content="IE=edge" /><link rel="profile" href="http://gmpg.org/xfn/11" /><link rel="pingback" href="https://www.rvb.com.br/xmlrpc.php" /><meta name='robots' content='index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1' /><style>img:is([sizes="auto" i], [sizes^="auto," i]) { contain-intrinsic-size: 3000px 1500px }</style><title>RVB Balões Infláveis Personalizados com rapidez e qualidade</title><meta name="description" content="Quer sair na frente da concorrência e impulsionar suas vendas com infláveis personalizados? A RVB Balões é a escolha certa!" /><link rel="canonical" href="https://www.rvb.com.br/" /><meta property="og:locale" content="pt_BR" /><meta property="og:type" content="website" /><meta property="og:title" content="RVB Balões Infláveis Personalizados com rapidez e qualidade" /><meta property="og:description" content="Quer sair na frente da concorrência e impulsionar suas vendas com infláveis personalizados? A RVB Balões é a escolha certa!" /><meta property="og:url" content="https://www.rvb.com.br/" /><meta property="og:site_name" content="RVB Balões e Infláveis Promocionais" /><meta property="article:publisher" content="https://www.facebook.com/rvbbaloes" /><meta property="article:modified_time" content="2025-06-01T22:23:14+00:00" /><meta property="og:image" content="https://www.rvb.com.br/wp-content/uploads/2018/02/tenda-inflavel-promocional-3x3-metros-personalizada-com-balcao-dog-choni.jpg" /><meta name="twitter:card" content="summary_large_image" /><meta name="twitter:site" content="@rvbbaloes" /> <script type="application/ld+json" class="yoast-schema-graph">{"@context":"https://schema.org","@graph":[{"@type":"WebPage","@id":"https://www.rvb.com.br/","url":"https://www.rvb.com.br/","name":"RVB Balões Infláveis Personalizados com rapidez e qualidade","isPartOf":{"@id":"https://www.rvb.com.br/#website"},"about":{"@id":"https://www.rvb.com.br/#organization"},"primaryImageOfPage":{"@id":"https://www.rvb.com.br/#primaryimage"},"image":{"@id":"https://www.rvb.com.br/#primaryimage"},"thumbnailUrl":"https://www.rvb.com.br/wp-content/uploads/2023/06/rvb-baloes-e-inflaveis-promocionais.png","datePublished":"2016-04-18T15:01:06+00:00","dateModified":"2025-06-01T22:23:14+00:00","description":"Quer sair na frente da concorrência e impulsionar suas vendas com infláveis personalizados? A RVB Balões é a escolha certa!","breadcrumb":{"@id":"https://www.rvb.com.br/#breadcrumb"},"inLanguage":"pt-BR","potentialAction":[{"@type":"ReadAction","target":["https://www.rvb.com.br/"]}]},{"@type":"ImageObject","inLanguage":"pt-BR","@id":"https://www.rvb.com.br/#primaryimage","url":"https://www.rvb.com.br/wp-content/uploads/2023/06/rvb-baloes-e-inflaveis-promocionais.png","contentUrl":"https://www.rvb.com.br/wp-content/uploads/2023/06/rvb-baloes-e-inflaveis-promocionais.png","width":800,"height":480,"caption":"RVB balões e infláveis promocionais personalizados"},{"@type":"BreadcrumbList","@id":"https://www.rvb.com.br/#breadcrumb","itemListElement":[{"@type":"ListItem","position":1,"name":"Início"}]},{"@type":"WebSite","@id":"https://www.rvb.com.br/#website","url":"https://www.rvb.com.br/","name":"RVB Balões Infláveis Personalizados","description":"Fabricante de Infláveis Personalizados. Balões Gigantes para Propaganda.","publisher":{"@id":"https://www.rvb.com.br/#organization"},"alternateName":"RVB Infláveis Personalizados","potentialAction":[{"@type":"SearchAction","target":{"@type":"EntryPoint","urlTemplate":"https://www.rvb.com.br/?s={search_term_string}"},"query-input":{"@type":"PropertyValueSpecification","valueRequired":true,"valueName":"search_term_string"}}],"inLanguage":"pt-BR"},{"@type":"Organization","@id":"https://www.rvb.com.br/#organization","name":"RVB Balões Infláveis Personalizados","alternateName":"RVB Balões Infláveis Personalizados","url":"https://www.rvb.com.br/","logo":{"@type":"ImageObject","inLanguage":"pt-BR","@id":"https://www.rvb.com.br/#/schema/logo/image/","url":"https://www.rvb.com.br/wp-content/uploads/2023/08/cropped-Logo-RVB-Baloes-Inflaveis.png","contentUrl":"https://www.rvb.com.br/wp-content/uploads/2023/08/cropped-Logo-RVB-Baloes-Inflaveis.png","width":512,"height":512,"caption":"RVB Balões Infláveis Personalizados"},"image":{"@id":"https://www.rvb.com.br/#/schema/logo/image/"},"sameAs":["https://www.facebook.com/rvbbaloes","https://x.com/rvbbaloes","https://www.instagram.com/rvbbaloes/","https://www.youtube.com/c/rvbbaloes","https://www.linkedin.com/company/rvbbaloes/"]}]}</script>'''
    
    print("🔍 Analisando HTML do site rvb.com.br")
    print("="*50)
    
    # 1. Extrair dados estruturados JSON-LD
    print("\n1️⃣ Extraindo dados estruturados JSON-LD:")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    print(f"   - Scripts JSON-LD encontrados: {len(json_ld_scripts)}")
    
    social_media_found = []
    
    for i, script in enumerate(json_ld_scripts):
        try:
            json_data = json.loads(script.get_text())
            print(f"\n   📊 Script {i+1}:")
            
            # Função recursiva para encontrar sameAs
            def find_same_as(data, path=""):
                if isinstance(data, dict):
                    if 'sameAs' in data:
                        print(f"     ✅ Encontrado 'sameAs' em {path}:")
                        same_as = data['sameAs']
                        if isinstance(same_as, list):
                            for url in same_as:
                                print(f"       - {url}")
                                social_media_found.append(url)
                        else:
                            print(f"       - {same_as}")
                            social_media_found.append(same_as)
                    
                    for key, value in data.items():
                        find_same_as(value, f"{path}.{key}" if path else key)
                        
                elif isinstance(data, list):
                    for j, item in enumerate(data):
                        find_same_as(item, f"{path}[{j}]")
            
            find_same_as(json_data)
            
        except json.JSONDecodeError as e:
            print(f"     ❌ Erro ao decodificar JSON: {e}")
    
    # 2. Extrair de meta tags
    print("\n2️⃣ Extraindo de meta tags:")
    
    # Facebook
    fb_publisher = soup.find('meta', property='article:publisher')
    if fb_publisher:
        fb_url = fb_publisher.get('content')
        print(f"   - Facebook (article:publisher): {fb_url}")
        social_media_found.append(fb_url)
    
    # Twitter
    twitter_site = soup.find('meta', attrs={'name': 'twitter:site'})
    if twitter_site:
        twitter_handle = twitter_site.get('content')
        print(f"   - Twitter (twitter:site): {twitter_handle}")
        if twitter_handle.startswith('@'):
            twitter_url = f"https://twitter.com/{twitter_handle[1:]}"
            social_media_found.append(twitter_url)
    
    # 3. Buscar por regex em todo o HTML
    print("\n3️⃣ Buscando por regex em todo o HTML:")
    
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
            for match in set(matches):  # Remove duplicatas
                print(f"     * {match}")
                if match not in social_media_found:
                    social_media_found.append(match)
    
    # 4. Resultado final
    print("\n" + "="*50)
    print("📊 RESULTADO FINAL")
    print("="*50)
    
    if social_media_found:
        print(f"\n✅ Total de redes sociais encontradas: {len(social_media_found)}")
        
        # Organizar por plataforma
        platforms = {
            'Facebook': [],
            'Instagram': [],
            'LinkedIn': [],
            'Twitter/X': [],
            'YouTube': [],
            'WhatsApp': []
        }
        
        for url in social_media_found:
            url_lower = url.lower()
            if 'facebook.com' in url_lower:
                platforms['Facebook'].append(url)
            elif 'instagram.com' in url_lower:
                platforms['Instagram'].append(url)
            elif 'linkedin.com' in url_lower:
                platforms['LinkedIn'].append(url)
            elif 'twitter.com' in url_lower or 'x.com' in url_lower:
                platforms['Twitter/X'].append(url)
            elif 'youtube.com' in url_lower:
                platforms['YouTube'].append(url)
            elif 'wa.me' in url_lower or 'whatsapp.com' in url_lower:
                platforms['WhatsApp'].append(url)
        
        for platform, urls in platforms.items():
            if urls:
                print(f"\n🔗 {platform}:")
                for url in set(urls):  # Remove duplicatas
                    print(f"   - {url}")
    else:
        print("\n❌ Nenhuma rede social encontrada")
    
    return social_media_found

if __name__ == "__main__":
    extract_social_media_from_html()