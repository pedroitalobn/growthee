from playwright.async_api import async_playwright
import json
import os
import time
import random

class LinkedInAuthService:
    def __init__(self):
        self.cookies_file = 'linkedin_cookies.json'
        self.login_url = 'https://www.linkedin.com/login'
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')

    async def get_cookies(self):
        # Aumentar o tempo de validade dos cookies salvos (24 horas)
        if os.path.exists(self.cookies_file):
            file_stat = os.stat(self.cookies_file)
            # Se os cookies têm menos de 24 horas
            if (time.time() - file_stat.st_mtime) < 86400:
                with open(self.cookies_file, 'r') as f:
                    return json.load(f)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            await page.goto(self.login_url)
            # Adicionar delays aleatórios para simular comportamento humano
            await asyncio.sleep(random.uniform(1, 2))
            await page.fill('input[id="username"]', self.email)
            await asyncio.sleep(random.uniform(0.5, 1))
            await page.fill('input[id="password"]', self.password)
            await asyncio.sleep(random.uniform(0.5, 1))
            await page.click('button[type="submit"]')

            await page.wait_for_load_state('networkidle')
            cookies = await context.cookies()
            
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)

            await browser.close()
            return cookies

    def format_cookies_for_scrapy(self, cookies):
        return {cookie['name']: cookie['value'] for cookie in cookies}