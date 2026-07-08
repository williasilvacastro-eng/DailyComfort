import asyncio
import os
import json
import logging
from api_shopee import ShopeeAffiliateAPI
import downloader
import generator_copy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_test")

async def test_pipeline():
    logger.info("=== INICIANDO TESTE DE INTEGRAÇÃO PONTA A PONTA ===")
    
    # Instancia a API
    api = ShopeeAffiliateAPI()
    
    # URL de teste do produto (Camiseta Brasil)
    url = "https://shopee.com.br/product/919160869/58210693755"
    logger.info(f"1. Processando link do produto: {url}")
    
    # Resolve URL e extrai IDs
    resolved_url = api.resolve_url(url)
    shop_id, item_id = api.extract_ids(resolved_url)
    logger.info(f"IDs extraídos: Shop ID={shop_id}, Item ID={item_id}")
    
    if not item_id:
        logger.error("Erro: Não foi possível extrair os IDs do produto.")
        return
        
    # Busca oferta na API de Afiliados
    logger.info("2. Consultando API Oficial de Afiliados...")
    product_offer = api.get_product_offer(item_id)
    if not product_offer:
        logger.warning("Aviso: Produto não retornado na API de Afiliados. Criando objeto parcial para o teste.")
        product_offer = {
            "itemId": item_id,
            "shopId": shop_id,
            "productName": "Camiseta Brasil 10 T-shirt",
            "productLink": resolved_url,
            "offerLink": url,
            "priceMin": "29.99",
            "priceMax": "32.99",
            "imageUrl": "https://cf.shopee.com.br/file/br-11134207-820l6-mo8o9z7j1lvkcc"
        }
        
    logger.info(f"Dados obtidos - Nome: {product_offer['productName']}, Preço Min: {product_offer.get('priceMin')}, Link Afiliado: {product_offer.get('offerLink')}")
    
    # Executa a raspagem de mídia usando Playwright (headless=True)
    logger.info("3. Executando raspagem de mídia secundária via Playwright...")
    # Para o teste em sandbox, vamos usar headless=True
    images, video_url = await api.scrape_media_with_playwright(shop_id, item_id, headless=True)
    logger.info(f"Mídias encontradas: {len(images)} imagens, Vídeo={bool(video_url)}")
    
    # Executa o download estruturado das mídias
    logger.info("4. Fazendo download estruturado das mídias...")
    download_results = await downloader.download_product_media(
        product_offer, 
        images, 
        video_url,
        output_base_dir="Shopee_Posts_Teste"
    )
    logger.info(f"Arquivos salvos na pasta: {download_results['pasta_destino']}")
    logger.info(f"Imagens locais salvas: {len(download_results['imagens_locais'])}")
    logger.info(f"Vídeo local salvo: {download_results['video_local']}")
    
    # Gera a legenda personalizada
    logger.info("5. Gerando a legenda do Instagram...")
    dest_dir = download_results["pasta_destino"]
    
    raw_data = None
    try:
        with open(download_results["dados_brutos"], "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception:
        pass
        
    legend = generator_copy.generate_instagram_legend(product_offer, dest_dir, raw_data)
    
    # 6. Salva na vitrine
    logger.info("6. Salvando produto na vitrine web local...")
    import shutil
    try:
        storefront_dir = os.path.abspath(os.path.join(os.getcwd(), "storefront"))
        images_dir = os.path.join(storefront_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        
        local_images = download_results.get("imagens_locais", [])
        local_image_name = ""
        if local_images:
            main_img_path = local_images[0]
            ext = os.path.splitext(main_img_path)[1] or ".jpg"
            local_image_name = f"{item_id}{ext}"
            shutil.copy2(main_img_path, os.path.join(images_dir, local_image_name))
            
        product_entry = {
            "itemId": int(item_id) if str(item_id).isdigit() else item_id,
            "productName": product_offer.get("productName", "Produto"),
            "productLink": product_offer.get("productLink", ""),
            "offerLink": product_offer.get("offerLink", ""),
            "priceMin": float(product_offer.get("priceMin", 0)),
            "priceOriginal": float(product_offer.get("priceMin", 0)) * 1.35,
            "imageUrl": product_offer.get("imageUrl", ""),
            "localImageName": local_image_name,
            "description": "Produto de teste da vitrine."
        }
        
        json_path = os.path.join(storefront_dir, "products.json")
        products_list = []
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                products_list = json.load(f)
                
        exists = False
        for idx, p in enumerate(products_list):
            if p.get("itemId") == product_entry["itemId"]:
                products_list[idx] = product_entry
                exists = True
                break
        if not exists:
            products_list.append(product_entry)
            
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(products_list, f, indent=4, ensure_ascii=False)
        logger.info("✅ Produto adicionado ao products.json da vitrine!")
    except Exception as se:
        logger.error(f"Erro ao salvar na vitrine durante teste: {se}")

    # Validação dos entregáveis
    logger.info("\n=== VERIFICAÇÃO DE ENTREGÁVEIS ===")
    legenda_path = os.path.join(dest_dir, "legenda_instagram.txt")
    if os.path.exists(legenda_path):
        logger.info(f"✅ Arquivo legenda_instagram.txt criado com sucesso!")
        with open(legenda_path, "r", encoding="utf-8") as lf:
            logger.info("Conteúdo da legenda gerada:\n" + "-"*40 + "\n" + lf.read() + "\n" + "-"*40)
    else:
        logger.error("❌ Erro: Arquivo legenda_instagram.txt NÃO foi encontrado.")
        
    dados_brutos_path = os.path.join(dest_dir, "dados_brutos.json")
    if os.path.exists(dados_brutos_path):
        logger.info(f"✅ Arquivo dados_brutos.json criado com sucesso!")
    else:
        logger.error("❌ Erro: Arquivo dados_brutos.json NÃO foi encontrado.")
        
    web_json_path = os.path.join(os.getcwd(), "storefront", "products.json")
    if os.path.exists(web_json_path):
        logger.info(f"✅ Arquivo storefront/products.json atualizado com sucesso!")
    else:
        logger.error("❌ Erro: Arquivo storefront/products.json NÃO foi encontrado.")
        
    logger.info("=== TESTE DE INTEGRAÇÃO PONTA A PONTA CONCLUÍDO ===")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
