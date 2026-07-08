import os
import re
import time
import hashlib
import json
import logging
import urllib.parse
import httpx
import asyncio
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopee_api")

class ShopeeAffiliateAPI:
    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv("SHOPEE_APP_ID")
        self.app_secret = os.getenv("SHOPEE_APP_SECRET")
        self.graphql_url = "https://open-api.affiliate.shopee.com.br/graphql"
        
        if not self.app_id or not self.app_secret:
            logger.warning("SHOPEE_APP_ID ou SHOPEE_APP_SECRET não encontrados no arquivo .env!")

    def resolve_url(self, url: str) -> str:
        """Resolve links encurtados da Shopee (como s.shopee.com.br, shope.ee) para obter a URL completa."""
        url = url.strip()
        if not url:
            return ""
        if "shopee.com.br" in url and "product" in url:
            return url
            
        logger.info(f"Resolvendo redirecionamento para o link: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        try:
            # Tenta HEAD primeiro por performance
            with httpx.Client(follow_redirects=True, headers=headers, timeout=10.0) as client:
                resp = client.head(url)
                resolved = str(resp.url)
                logger.info(f"Link resolvido via HEAD: {resolved}")
                return resolved
        except Exception as e:
            logger.warning(f"Falha ao resolver URL via HEAD: {e}. Tentando via GET...")
            try:
                with httpx.Client(follow_redirects=True, headers=headers, timeout=10.0) as client:
                    resp = client.get(url)
                    resolved = str(resp.url)
                    logger.info(f"Link resolvido via GET: {resolved}")
                    return resolved
            except Exception as e2:
                logger.error(f"Erro ao resolver link: {e2}")
                return url

    def extract_ids(self, url: str) -> Tuple[Optional[int], Optional[int]]:
        """Extrai o shop_id e o item_id da URL resolvida da Shopee."""
        # Padrão 1: i.SHOPID.ITEMID
        match = re.search(r"i\.(\d+)\.(\d+)", url)
        if match:
            return int(match.group(1)), int(match.group(2))
            
        # Padrão 2: /product/SHOPID/ITEMID
        match = re.search(r"/product/(\d+)/(\d+)", url)
        if match:
            return int(match.group(1)), int(match.group(2))
            
        # Padrão 3: /shop_name/SHOPID/ITEMID
        parsed = urllib.parse.urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 3:
            if path_parts[-2].isdigit() and path_parts[-1].isdigit():
                return int(path_parts[-2]), int(path_parts[-1])
                
        return None, None

    def _generate_signature(self, payload_str: str, timestamp: int) -> str:
        """Gera a assinatura digital necessária para a autenticação na API da Shopee."""
        signature_str = f"{self.app_id}{timestamp}{payload_str}{self.app_secret}"
        return hashlib.sha256(signature_str.encode("utf-8")).hexdigest()

    def _send_graphql_request(self, payload: dict) -> dict:
        """Envia uma requisição POST autenticada para o endpoint GraphQL da Shopee."""
        if not self.app_id or not self.app_secret:
            raise ValueError("Credenciais da API da Shopee ausentes no .env.")

        payload_str = json.dumps(payload, separators=(',', ':'))
        timestamp = int(time.time())
        signature = self._generate_signature(payload_str, timestamp)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={self.app_id},Timestamp={timestamp},Signature={signature}"
        }
        
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(self.graphql_url, data=payload_str, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Erro HTTP {resp.status_code} na API da Shopee: {resp.text}")
            
            res_json = resp.json()
            if "errors" in res_json:
                raise RuntimeError(f"Erros na resposta GraphQL: {res_json['errors']}")
                
            return res_json

    def get_product_offer(self, item_id: int) -> Optional[dict]:
        """Consulta os dados do produto usando o endpoint productOfferV2 (API de Afiliados)."""
        logger.info(f"Consultando API do produto para o ID: {item_id}")
        query = """
        query {
          productOfferV2(itemId: %d) {
            nodes {
              itemId
              productName
              productLink
              offerLink
              price
              priceMin
              priceMax
              commissionRate
              shopId
              shopName
              imageUrl
            }
          }
        }
        """ % item_id

        payload = {"query": query}
        try:
            result = self._send_graphql_request(payload)
            nodes = result.get("data", {}).get("productOfferV2", {}).get("nodes", [])
            if nodes:
                return nodes[0]
            logger.warning(f"Nenhum nó retornado para o itemId: {item_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar productOfferV2: {e}")
            return None

    def generate_affiliate_link(self, original_url: str) -> Optional[str]:
        """Gera um link de afiliado caso o produto não seja retornado pelo productOfferV2."""
        logger.info(f"Gerando link de afiliado curto via API: {original_url}")
        query = """
        mutation {
          generateShortLink(input: {
            originUrl: "%s"
          }) {
            shortLink
          }
        }
        """ % original_url

        payload = {"query": query}
        try:
            result = self._send_graphql_request(payload)
            return result.get("data", {}).get("generateShortLink", {}).get("shortLink")
        except Exception as e:
            logger.error(f"Erro ao gerar link de afiliado curto: {e}")
            return None

    def save_cookies(self, raw_cookies: str) -> bool:
        """Salva cookies (JSON ou texto bruto) no perfil do Playwright para contornar captchas e login."""
        import json
        cookies_list = []
        raw_cookies = raw_cookies.strip()
        if not raw_cookies:
            return False
            
        try:
            # Tenta decodificar como array/objeto JSON
            parsed = json.loads(raw_cookies)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        cookies_list.append({
                            "name": item["name"],
                            "value": item["value"],
                            "domain": item.get("domain", ".shopee.com.br"),
                            "path": item.get("path", "/")
                        })
            elif isinstance(parsed, dict):
                for name, value in parsed.items():
                    cookies_list.append({
                        "name": name,
                        "value": str(value),
                        "domain": ".shopee.com.br",
                        "path": "/"
                    })
        except Exception:
            # Fallback para parsing de cabeçalho Cookie do HTTP (chave=valor;)
            for item in raw_cookies.split(";"):
                item = item.strip()
                if "=" in item:
                    parts = item.split("=", 1)
                    name = parts[0].strip()
                    value = parts[1].strip()
                    if name and value:
                        cookies_list.append({
                            "name": name,
                            "value": value,
                            "domain": ".shopee.com.br",
                            "path": "/"
                        })

        if not cookies_list:
            logger.warning("Nenhum cookie válido pôde ser extraído do texto informado.")
            return False
            
        profile_dir = os.path.abspath(os.path.join(os.getcwd(), ".chrome_profile"))
        os.makedirs(profile_dir, exist_ok=True)
        cookies_file = os.path.join(profile_dir, "cookies.json")
        try:
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies_list, f, indent=4)
            logger.info(f"Salvos {len(cookies_list)} cookies em: {cookies_file}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo de cookies: {e}")
            return False

    async def run_headed_login(self) -> bool:
        """Abre o navegador em modo visível (headed) para o usuário fazer login ou resolver captchas na Shopee."""
        from playwright.async_api import async_playwright
        profile_dir = os.path.abspath(os.path.join(os.getcwd(), ".chrome_profile"))
        os.makedirs(profile_dir, exist_ok=True)
        
        logger.info("Iniciando navegador com interface gráfica para login...")
        async with async_playwright() as p:
            channels = [None, "chrome", "msedge"]
            context = None
            for channel in channels:
                try:
                    context = await p.chromium.launch_persistent_context(
                        profile_dir,
                        headless=False,
                        channel=channel,
                        viewport={"width": 1280, "height": 800},
                        locale="pt-BR",
                        ignore_default_args=["--enable-automation", "--no-sandbox"],
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-infobars"
                        ]
                    )
                    break
                except Exception as e:
                    logger.warning(f"Falha ao iniciar canal {channel} em modo visível: {e}")
                    
            if not context:
                logger.error("Não foi possível abrir o navegador.")
                return False
                
            page = context.pages[0] if context.pages else await context.new_page()
            await page.add_init_script("delete navigator.__proto__.webdriver")
            await page.goto("https://shopee.com.br/buyer/login", wait_until="domcontentloaded", timeout=60000)
            
            # Aguarda o fechamento da página
            future = asyncio.Future()
            page.on("close", lambda p: future.set_result(True))
            logger.info("Aguardando o usuário fechar a janela do navegador após fazer login...")
            await future
            await context.close()
            logger.info("Navegador fechado. Cookies e sessão salvos com sucesso!")
            return True

    async def scrape_media_with_playwright(self, shop_id: int, item_id: int, headless: bool = True) -> Tuple[List[str], str]:
        """Método de raspagem em background (via Playwright) usando perfil persistente para extrair imagens e vídeos."""
        from playwright.async_api import async_playwright
        profile_dir = os.path.abspath(os.path.join(os.getcwd(), ".chrome_profile"))
        os.makedirs(profile_dir, exist_ok=True)
        
        target_url = f"https://shopee.com.br/product/{shop_id}/{item_id}"
        logger.info(f"Iniciando navegador (headless={headless}) para extrair mídias de: {target_url}")
        
        images = []
        video_url = ""
        api_responses = []
        video_requests = []
        
        async def handle_response(response):
            if "api/v4/item/get" in response.url:
                try:
                    json_data = await response.json()
                    if json_data.get("data"):
                        api_responses.append(json_data["data"])
                        logger.info("Captured api/v4/item/get network response.")
                except Exception:
                    pass
            content_type = response.headers.get("content-type", "")
            if "video/" in content_type or ".mp4" in response.url.split("?")[0]:
                video_requests.append(response.url)
                logger.info(f"Captured video file URL: {response.url}")

        async with async_playwright() as p:
            channels = [None, "chrome", "msedge"]
            context = None
            
            for channel in browser_channels if 'browser_channels' in locals() else channels:
                try:
                    context = await p.chromium.launch_persistent_context(
                        profile_dir,
                        headless=headless,
                        channel=channel,
                        viewport={"width": 1280, "height": 800},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        locale="pt-BR",
                        ignore_default_args=["--enable-automation", "--no-sandbox"],
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--disable-infobars"
                        ]
                    )
                    break
                except Exception as b_err:
                    logger.warning(f"Falha ao iniciar canal {channel} em modo persistente headless: {b_err}")
            
            if not context:
                logger.error("Não foi possível iniciar nenhum canal de navegador do Playwright em modo headless.")
                return [], ""
                
            # Tenta carregar cookies manuais do cookies.json
            cookies_file = os.path.join(profile_dir, "cookies.json")
            if os.path.exists(cookies_file):
                try:
                    with open(cookies_file, "r", encoding="utf-8") as f:
                        cookies_list = json.load(f)
                    await context.add_cookies(cookies_list)
                    logger.info("Cookies personalizados carregados com sucesso no contexto.")
                except Exception as ce:
                    logger.error(f"Erro ao injetar cookies personalizados no contexto: {ce}")
                
            page = context.pages[0] if context.pages else await context.new_page()
            await page.add_init_script("delete navigator.__proto__.webdriver")
            page.on("response", handle_response)
            
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2.0)
                
                # Tenta fechar o seletor de idioma
                try:
                    lang_btn = await page.query_selector("button:has-text('Português')") or await page.query_selector("*:has-text('Português (BR)')")
                    if lang_btn:
                        await lang_btn.click()
                        logger.info("Botão de idioma 'Português' clicado.")
                        await asyncio.sleep(1.5)
                except Exception as e:
                    logger.debug(f"Erro ao clicar no botão de idioma: {e}")

                # Tenta aceitar todos os cookies
                try:
                    cookie_btn = await page.query_selector("button:has-text('todos os cookies')") or await page.query_selector("button:has-text('Aceitar')")
                    if cookie_btn:
                        await cookie_btn.click()
                        logger.info("Botão de cookies clicado.")
                        await asyncio.sleep(1.0)
                except Exception as e:
                    logger.debug(f"Erro ao aceitar cookies: {e}")
                
                # Scroll para baixo para carregar os elementos dinâmicos
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(4.0)
                
                # Captura screenshot para diagnóstico
                await page.screenshot(path="shopee_debug_screenshot.png")
                logger.info("Salva screenshot de diagnóstico em shopee_debug_screenshot.png")
                
                # Se capturou resposta da API v4
                if api_responses:
                    item_info = api_responses[0]
                    img_ids = item_info.get("images", [])
                    images = [f"https://down-br-sg.img.soso.com/file/{img_id}" for img_id in img_ids]
                    
                    video_info = item_info.get("video_info_list", [])
                    if video_info and isinstance(video_info, list):
                        for vid_entry in video_info:
                            if vid_entry.get("video_url"):
                                video_url = vid_entry.get("video_url")
                                break
                            formats = vid_entry.get("formats", [])
                            for fmt in formats:
                                if fmt.get("url"):
                                    video_url = fmt.get("url")
                                    break
                
                # Se não capturou o vídeo via rede, tenta por requisições farejadas
                if not video_url and video_requests:
                    video_url = video_requests[0]
                    
                # Fallback de DOM para Imagens
                if not images:
                    logger.info("Tentando fallback de DOM para imagens...")
                    img_elements = await page.query_selector_all("img")
                    for img in img_elements:
                        src = await img.get_attribute("src")
                        if src and ("file/" in src or "img.soso.com" in src) and src not in images:
                            if src.startswith("//"):
                                src = f"https:{src}"
                            images.append(src)
                    images = images[:9]
                    
                # Fallback de DOM para Vídeo
                if not video_url:
                    logger.info("Tentando fallback de DOM para vídeo...")
                    video_el = await page.query_selector("video")
                    if video_el:
                        src = await video_el.get_attribute("src")
                        if src and not src.startswith("blob:"):
                            video_url = src
                            
            except Exception as page_err:
                logger.error(f"Erro durante automação da página: {page_err}")
            finally:
                await context.close()
                
        return images, video_url

if __name__ == "__main__":
    # Teste rápido
    api = ShopeeAffiliateAPI()
    url = "https://shopee.com.br/product/919160869/58210693755"
    shop_id, item_id = api.extract_ids(url)
    print("IDs:", shop_id, item_id)
    if item_id:
        info = api.get_product_offer(item_id)
        print("API Info:", json.dumps(info, indent=2, ensure_ascii=False))
        
        async def run_test():
            images, video = await api.scrape_media_with_playwright(shop_id, item_id, headless=False)
            print("Images found:", len(images))
            print("Video URL:", video)
        
        asyncio.run(run_test())
