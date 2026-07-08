import os
import logging
from typing import Optional

logger = logging.getLogger("shopee_generator")

def get_short_title(title: str) -> str:
    """Simplifica títulos longos da Shopee para ficarem mais atraentes no Instagram."""
    if not title:
        return "Achadinho Incrível"
    
    # Remove termos comuns de spam e SEO
    terms_to_remove = [
        "atacado", "revenda", "promocao", "promoção", "barato", "imperdível",
        "frete grátis", "frete gratis", "oferta", "original", "novo", "2026", "2025"
    ]
    
    cleaned = title.lower()
    for term in terms_to_remove:
        cleaned = cleaned.replace(term, "")
        
    # Divide em palavras e pega as primeiras 6 palavras
    words = [w.capitalize() for w in cleaned.split() if w.strip()]
    if len(words) > 6:
        return " ".join(words[:6]) + "..."
    return " ".join(words)

def generate_instagram_legend(
    product_data: dict,
    dest_dir: str,
    raw_scraped_data: Optional[dict] = None
) -> str:
    """
    Gera o arquivo legenda_instagram.txt na pasta do produto.
    Usa um template persuasivo com formatação de preços e CTA.
    """
    # Coleta de dados
    long_title = product_data.get("productName") or product_data.get("titulo") or "Produto Shopee"
    short_title = get_short_title(long_title)
    
    # Preços
    price_min = product_data.get("priceMin") or product_data.get("price") or "0.00"
    price_max = product_data.get("priceMax") or product_data.get("price") or "0.00"
    
    # Formata preço com desconto
    preco_desconto = f"{float(price_min):.2f}".replace(".", ",") if price_min else "0,00"
    
    # Preço original (se não tiver na API, tentamos pegar do scraping ou estimar)
    preco_original_raw = None
    if raw_scraped_data and "api_data" in raw_scraped_data:
        # Tenta ler do scraping da API v4
        api_v4_data = raw_scraped_data["api_data"]
        price_before = api_v4_data.get("price_before")
        if price_before and price_before > 0:
            preco_original_raw = f"{price_before / 100000:.2f}"
            
    if not preco_original_raw:
        # Se não houver preço original estruturado, assumimos um acréscimo fictício de 30% como âncora de marketing
        try:
            val_desconto = float(price_min)
            val_original = val_desconto * 1.35
            preco_original_raw = f"{val_original:.2f}"
        except Exception:
            preco_original_raw = "0.00"
            
    preco_original = preco_original_raw.replace(".", ",")
    
    # Resumo da descrição (tenta extrair da API v4 raspada)
    description = ""
    if raw_scraped_data and "api_data" in raw_scraped_data:
        description = raw_scraped_data["api_data"].get("description", "")
        
    if not description:
        description = "Clique no link para ver todos os detalhes técnicos, cores e avaliações de outros compradores na página da Shopee!"
        
    # Limita a descrição em aproximadamente 3 linhas limpas
    desc_lines = [line.strip() for line in description.split("\n") if line.strip()]
    desc_summary = "\n".join(desc_lines[:3])
    if len(desc_summary) > 150:
        desc_summary = desc_summary[:147] + "..."

    # Link de afiliado
    link_afiliado = product_data.get("offerLink") or product_data.get("productLink") or ""
    item_id = product_data.get("itemId") or "000"

    # Monta a legenda baseado no template solicitado
    legend = f"""✨ {short_title} ✨

💖 Por apenas: R$ {preco_desconto} (De: R$ {preco_original})!

📝 Detalhes do Produto:
{desc_summary}

🚀 COMO COMPRAR:
1️⃣ Comente "QUERO" que te envio o link no Direct!
2️⃣ Ou clique no link da nossa BIO (Produto no Story / Destaque {item_id})!

🔗 Seu Link de Afiliado (Para copiar rápido): 
{link_afiliado}

📦 Frete Grátis disponível aplicando o cupom no app!

#shopee #achadinhos #shopeebrazil #promocao #achadinhosdashopee #ofertas #utilidades"""

    # Grava o arquivo local
    dest_path = os.path.join(dest_dir, "legenda_instagram.txt")
    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(legend)
        logger.info(f"Legenda gerada em: {dest_path}")
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo de legenda: {e}")

    return legend
