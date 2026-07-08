import os
import re
import json
import logging
import asyncio
import httpx
from typing import List, Optional, Callable

logger = logging.getLogger("shopee_downloader")

def clean_filename(text: str) -> str:
    """Limpa um texto para torná-lo um nome de pasta/arquivo válido no Windows."""
    if not text:
        return "produto_sem_nome"
    # Remove caracteres inválidos: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "", text)
    # Remove espaços duplos e limita o tamanho do caminho
    return cleaned.strip()[:60]

async def download_file(url: str, dest_path: str, client: httpx.AsyncClient) -> bool:
    """Baixa um único arquivo de forma assíncrona."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://shopee.com.br/"
    }
    try:
        async with client.stream("GET", url, headers=headers, timeout=30.0) as response:
            if response.status_code == 200:
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=16384):
                        f.write(chunk)
                logger.info(f"Sucesso ao baixar: {dest_path}")
                return True
            else:
                logger.error(f"Erro HTTP {response.status_code} ao baixar {url}")
                return False
    except Exception as e:
        logger.error(f"Exceção ao baixar {url}: {e}")
        return False

async def download_product_media(
    product_data: dict,
    images: List[str],
    video_url: str,
    output_base_dir: str = "Shopee_Posts",
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> dict:
    """
    Cria uma pasta estruturada local e baixa concorrentemente todas as mídias do produto.
    Salva também o arquivo dados_brutos.json.
    """
    item_id = product_data.get("itemId") or product_data.get("id") or "sem_id"
    product_name = product_data.get("productName") or product_data.get("titulo") or "produto"
    
    # Define o nome da pasta de saída
    clean_name = clean_filename(product_name)
    folder_name = f"{item_id} - {clean_name}"
    target_dir = os.path.join(output_base_dir, folder_name)
    os.makedirs(target_dir, exist_ok=True)
    
    # Salva dados_brutos.json contendo a resposta combinada
    dados_brutos_path = os.path.join(target_dir, "dados_brutos.json")
    try:
        with open(dados_brutos_path, "w", encoding="utf-8") as f:
            json.dump({
                "api_data": product_data,
                "scraped_images": images,
                "scraped_video": video_url
            }, f, indent=4, ensure_ascii=False)
        logger.info(f"Dados brutos salvos em: {dados_brutos_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar dados brutos: {e}")

    # Monta a lista de downloads
    download_tasks = []
    
    # Imagens
    downloaded_images = []
    # Usar a imagem principal da API se a lista de imagens raspadas estiver vazia
    if not images and product_data.get("imageUrl"):
        images = [product_data.get("imageUrl")]
        
    for idx, img_url in enumerate(images):
        ext = ".jpg"
        if ".png" in img_url.lower():
            ext = ".png"
        elif ".webp" in img_url.lower():
            ext = ".webp"
            
        file_name = f"{idx+1:02d}_detalhe{ext}" if idx > 0 else f"01_capa{ext}"
        dest_path = os.path.join(target_dir, file_name)
        download_tasks.append((img_url, dest_path, "image", file_name))

    # Vídeo
    video_path = ""
    if video_url:
        video_file_name = "00_video_reels.mp4"
        dest_video_path = os.path.join(target_dir, video_file_name)
        download_tasks.append((video_url, dest_video_path, "video", video_file_name))
        
    total_files = len(download_tasks)
    downloaded_count = 0
    
    # Inicia os downloads simultâneos
    if download_tasks:
        if progress_callback:
            progress_callback(0, total_files, f"Iniciando download de {total_files} mídias...")
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Baixa em lote concorrentemente
            tasks = [download_file(url, path, client) for url, path, _, _ in download_tasks]
            results = await asyncio.gather(*tasks)
            
            # Processa os resultados
            for success, (url, path, file_type, file_name) in zip(results, download_tasks):
                if success:
                    downloaded_count += 1
                    if file_type == "image":
                        downloaded_images.append(path)
                    elif file_type == "video":
                        video_path = path
                        
                if progress_callback:
                    progress_callback(
                        downloaded_count,
                        total_files,
                        f"Baixado: {file_name} ({downloaded_count}/{total_files})"
                    )

    # Ordena as imagens salvas
    downloaded_images.sort()
    
    # Atualiza o dicionário de resultados
    result_data = {
        "pasta_destino": target_dir,
        "imagens_locais": downloaded_images,
        "video_local": video_path,
        "dados_brutos": dados_brutos_path
    }
    
    return result_data
