import os
import sys
import time
import logging
import threading
import asyncio
import customtkinter as ctk
from tkinter import messagebox
from dotenv import load_dotenv

# Importa os módulos criados
from api_shopee import ShopeeAffiliateAPI
import downloader
import generator_copy

# Configuração de logs para exibição no console do Tkinter
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        self.text_widget.after(0, append)

class ShopeeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configurações da Janela
        self.title("Shopee Extractor & Organizer v3.0")
        self.geometry("680x600")
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        
        # Instancia a API
        self.api = ShopeeAffiliateAPI()
        
        # Estados
        self.is_extracting = False
        self.clipboard_thread = None
        self.clipboard_active = False
        self.last_clipboard_url = ""
        
        self.build_ui()
        self.setup_logging()
        self.check_env()

    def build_ui(self):
        # Título Principal
        self.title_label = ctk.CTkLabel(
            self, 
            text="Shopee Extractor & Organizer", 
            font=ctk.CTkFont(family="Inter", size=24, weight="bold")
        )
        self.title_label.pack(pady=15)

        # Container Principal
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # Input URL
        self.url_label = ctk.CTkLabel(
            self.main_frame, 
            text="Cole o link do produto da Shopee (Curto ou Completo):",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.url_label.pack(anchor="w", padx=15, pady=(15, 2))
        
        self.url_entry = ctk.CTkEntry(
            self.main_frame, 
            placeholder_text="https://shopee.com.br/... ou https://s.shopee.com.br/...",
            width=600
        )
        self.url_entry.pack(fill="x", padx=15, pady=5)

        # Categoria do Produto
        self.category_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.category_frame.pack(fill="x", padx=15, pady=(5, 2))

        self.category_label = ctk.CTkLabel(
            self.category_frame, 
            text="Categoria da vitrine:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.category_label.pack(side="left", padx=(0, 10))

        self.category_combo = ctk.CTkComboBox(
            self.category_frame, 
            values=["Casa & Cozinha", "Tecnologia", "Utilidades", "Moda", "Beleza & Saúde", "Outros"],
            width=200
        )
        self.category_combo.pack(side="left")
        self.category_combo.set("Casa & Cozinha")

        # Opções extras
        self.options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.options_frame.pack(fill="x", padx=15, pady=5)

        self.clipboard_checkbox = ctk.CTkCheckBox(
            self.options_frame, 
            text="Monitorar Área de Transferência (Auto Ctrl+C)",
            command=self.toggle_clipboard_monitor,
            font=ctk.CTkFont(size=12)
        )
        self.clipboard_checkbox.pack(side="left", pady=5)

        self.autopush_checkbox = ctk.CTkCheckBox(
            self.options_frame, 
            text="Publicar Auto no GitHub",
            font=ctk.CTkFont(size=12)
        )
        self.autopush_checkbox.pack(side="right", pady=5)
        self.autopush_checkbox.select()

        # Botões de Ação
        self.buttons_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.buttons_frame.pack(fill="x", padx=15, pady=10)

        self.extract_btn = ctk.CTkButton(
            self.buttons_frame, 
            text="Extrair e Organizar", 
            command=self.start_extraction_thread,
            fg_color="#EE4D2D",  # Cor oficial Shopee
            hover_color="#D13F21",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.extract_btn.pack(side="left", expand=True, fill="x", padx=(0, 10))

        self.login_btn = ctk.CTkButton(
            self.buttons_frame, 
            text="Fazer Login na Shopee", 
            command=self.start_login_thread,
            fg_color="#2B394A",
            hover_color="#1E2833",
            font=ctk.CTkFont(size=12),
            height=40
        )
        self.login_btn.pack(side="right", padx=(10, 0))

        self.cookie_btn = ctk.CTkButton(
            self.buttons_frame, 
            text="Importar Cookies", 
            command=self.open_cookie_import_dialog,
            fg_color="#4F5D73",
            hover_color="#3C4858",
            font=ctk.CTkFont(size=12),
            height=40
        )
        self.cookie_btn.pack(side="right", padx=(10, 0))

        # Frame de Gerenciamento da Vitrine (GitHub / Local)
        self.storefront_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.storefront_frame.pack(fill="x", padx=15, pady=(5, 10))

        self.open_storefront_btn = ctk.CTkButton(
            self.storefront_frame, 
            text="📁 Pasta da Vitrine", 
            command=self.open_storefront_folder,
            fg_color="#4F5D73",
            hover_color="#3C4858",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35
        )
        self.open_storefront_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.preview_storefront_btn = ctk.CTkButton(
            self.storefront_frame, 
            text="🌐 Ver Local", 
            command=self.preview_storefront,
            fg_color="#1F77B4",
            hover_color="#155F93",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35
        )
        self.preview_storefront_btn.pack(side="left", expand=True, fill="x", padx=5)

        self.publish_github_btn = ctk.CTkButton(
            self.storefront_frame, 
            text="🚀 GitHub Pages", 
            command=self.publish_to_github,
            fg_color="#24292E",  # Cor do GitHub
            hover_color="#1A1F22",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35
        )
        self.publish_github_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

        # Progresso
        self.progress_label = ctk.CTkLabel(
            self.main_frame, 
            text="Aguardando link...", 
            font=ctk.CTkFont(size=11, slant="italic")
        )
        self.progress_label.pack(anchor="w", padx=15, pady=(10, 2))

        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.pack(fill="x", padx=15, pady=5)
        self.progress_bar.set(0)

        # Console de Logs
        self.log_label = ctk.CTkLabel(
            self.main_frame, 
            text="Logs do Sistema:", 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.log_label.pack(anchor="w", padx=15, pady=(10, 2))

        self.log_text = ctk.CTkTextbox(self.main_frame, height=200, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def setup_logging(self):
        # Conecta os logs do python ao console CTk
        self.log_handler = TextHandler(self.log_text)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S'))
        
        # Conecta aos loggers
        for name in ["shopee_api", "shopee_downloader", "shopee_generator", "shopee_app"]:
            l = logging.getLogger(name)
            l.addHandler(self.log_handler)
            l.setLevel(logging.INFO)
            
        self.logger = logging.getLogger("shopee_app")
        self.logger.info("Sistema inicializado com sucesso.")

    def check_env(self):
        load_dotenv()
        app_id = os.getenv("SHOPEE_APP_ID")
        app_secret = os.getenv("SHOPEE_APP_SECRET")
        if not app_id or not app_secret:
            self.logger.warning("ATENÇÃO: Chaves da Shopee não configuradas no .env!")
            messagebox.showwarning(
                "Configuração Ausente", 
                "As credenciais da Shopee (App ID e Secret) não foram encontradas no arquivo .env!\nPor favor, insira-as antes de executar a extração."
            )
        else:
            self.logger.info("Chaves da API da Shopee carregadas com sucesso.")

    def update_progress(self, current, total, text):
        """Atualiza a barra de progresso e o texto com base no feedback do downloader."""
        def run_update():
            pct = current / total if total > 0 else 0
            self.progress_bar.set(pct)
            self.progress_label.configure(text=text)
        self.after(0, run_update)

    def log_message(self, message, level="info"):
        """Método auxiliar para logar mensagens a partir de threads."""
        if level == "info":
            self.logger.info(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)

    # --- Threads ---
    
    def start_login_thread(self):
        threading.Thread(target=self.run_login_flow, daemon=True).start()

    def run_login_flow(self):
        self.login_btn.configure(state="disabled")
        self.log_message("Abrindo navegador de login...")
        
        async def run_async():
            return await self.api.run_headed_login()
            
        success = asyncio.run(run_async())
        if success:
            self.log_message("Login concluído. Sessão guardada!")
        else:
            self.log_message("O navegador foi fechado ou ocorreu um erro.", "error")
            
        self.login_btn.configure(state="normal")

    def start_extraction_thread(self, url_to_use=None):
        if self.is_extracting:
            return
            
        url = url_to_use or self.url_entry.get().strip()
        if not url:
            messagebox.showerror("URL Vazia", "Por favor, insira uma URL da Shopee válida.")
            return
            
        self.is_extracting = True
        self.extract_btn.configure(state="disabled")
        self.progress_bar.set(0.05)
        self.progress_label.configure(text="Iniciando extração...")
        
        # Executa em segundo plano para não travar a GUI
        threading.Thread(target=self.run_extraction_flow, args=(url,), daemon=True).start()

    def run_extraction_flow(self, url: str):
        try:
            self.log_message(f"Processando URL: {url}")
            
            # 1. Resolve URL encurtada
            self.update_progress(1, 5, "Resolvendo URL curta da Shopee...")
            resolved_url = self.api.resolve_url(url)
            
            # 2. Extrai IDs
            shop_id, item_id = self.api.extract_ids(resolved_url)
            if not item_id:
                raise ValueError("Não foi possível extrair o ID do produto desta URL.")
                
            self.log_message(f"IDs extraídos: Shop ID={shop_id}, Item ID={item_id}")
            
            # 3. Consulta a API Oficial GraphQL
            self.update_progress(2, 5, "Consultando API Oficial de Afiliados...")
            product_offer = self.api.get_product_offer(item_id)
            
            if not product_offer:
                self.log_message("Aviso: Produto não retornado na API de Afiliados. Criando fallback...", "warning")
                # Fallback de dados parciais
                product_offer = {
                    "itemId": item_id,
                    "shopId": shop_id,
                    "productName": f"Produto {item_id}",
                    "productLink": resolved_url,
                    "offerLink": url,  # Fallback de link
                    "priceMin": "0.00",
                    "priceMax": "0.00",
                    "imageUrl": ""
                }
                
                # Tenta gerar link de afiliado pela mutation curta
                short_link = self.api.generate_affiliate_link(resolved_url)
                if short_link:
                    product_offer["offerLink"] = short_link

            # 4. Executa raspagem das mídias extras via Playwright
            self.update_progress(3, 5, "Executando scraping de mídias (Imagens e Vídeo)...")
            
            async def run_scraper():
                return await self.api.scrape_media_with_playwright(shop_id, item_id, headless=True)
                
            images, video_url = asyncio.run(run_scraper())
            self.log_message(f"Mídias encontradas: {len(images)} imagens, Vídeo={bool(video_url)}")
            
            # 5. Faz download das mídias
            self.update_progress(4, 5, "Fazendo download das mídias locais...")
            
            async def run_downloads():
                return await downloader.download_product_media(
                    product_offer, 
                    images, 
                    video_url, 
                    progress_callback=self.update_progress_from_downloader
                )
                
            download_results = asyncio.run(run_downloads())
            
            # 6. Gera legenda
            self.update_progress(5, 5, "Gerando copy do Instagram...")
            dest_dir = download_results["pasta_destino"]
            
            # Carrega dados brutos salvos no download para enriquecer a copy (como descrição da v4 se existir)
            raw_data = None
            try:
                with open(download_results["dados_brutos"], "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception:
                pass
                
            copy_text = generator_copy.generate_instagram_legend(product_offer, dest_dir, raw_data)
            
            # 7. Copia para a Vitrine Web (storefront)
            self.log_message("Salvando produto na vitrine web local...")
            self.save_to_web_storefront(product_offer, download_results, raw_data)
            
            # 8. Auto-Publicação no GitHub Pages se ativado
            if self.autopush_checkbox.get() == 1:
                self.log_message("Auto-publicação ativada. Sincronizando com o GitHub Pages...")
                self.publish_to_github()

            # Conclusão
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="Concluído!")
            self.log_message(f"✅ Sucesso total! Pasta criada em: {os.path.abspath(dest_dir)}")
            
            # Pergunta se deseja abrir a pasta
            self.after(0, lambda: self.prompt_open_folder(dest_dir))
            
        except Exception as e:
            self.log_message(f"Erro na extração: {e}", "error")
            self.progress_label.configure(text="Erro!")
            self.after(0, lambda: messagebox.showerror("Erro de Extração", str(e)))
        finally:
            self.is_extracting = False
            self.after(0, lambda: self.extract_btn.configure(state="normal"))

    def update_progress_from_downloader(self, current, total, text):
        # Transforma o progresso do downloader em porcentagem e atualiza a barra
        # Mapeia o progresso do download na faixa entre 70% e 95% do progresso geral
        base_pct = 0.65
        range_pct = 0.30
        pct = base_pct + ((current / total) * range_pct) if total > 0 else base_pct
        
        self.after(0, lambda: self.progress_bar.set(pct))
        self.after(0, lambda: self.progress_label.configure(text=text))

    def prompt_open_folder(self, path):
        if messagebox.askyesno("Extração Concluída", "Extração realizada com sucesso!\nDeseja abrir a pasta do produto?"):
            os.startfile(os.path.abspath(path))

    # --- Monitor da Área de Transferência ---

    def toggle_clipboard_monitor(self):
        if self.clipboard_checkbox.get() == 1:
            self.clipboard_active = True
            self.log_message("Monitor de Área de Transferência ativado.")
            self.clipboard_thread = threading.Thread(target=self.run_clipboard_watcher, daemon=True)
            self.clipboard_thread.start()
        else:
            self.clipboard_active = False
            self.log_message("Monitor de Área de Transferência desativado.")

    def run_clipboard_watcher(self):
        while self.clipboard_active:
            try:
                # Lê o clipboard do Tkinter com segurança
                clip_text = self.clipboard_get().strip()
                
                # Valida se é um link da Shopee
                is_shopee = (
                    "shopee.com.br" in clip_text or 
                    "shope.ee" in clip_text or 
                    "s.shopee" in clip_text
                )
                
                if is_shopee and clip_text != self.last_clipboard_url:
                    self.last_clipboard_url = clip_text
                    self.log_message(f"Detectado link da Shopee no Ctrl+C: {clip_text}")
                    # Insere o link na UI e inicia a extração automaticamente
                    self.after(0, lambda: self.url_entry.delete(0, "end"))
                    self.after(0, lambda: self.url_entry.insert(0, clip_text))
                    self.after(0, lambda: self.start_extraction_thread(clip_text))
            except Exception:
                pass
            time.sleep(1.5)

    def save_to_web_storefront(self, product_offer: dict, download_results: dict, raw_data: Optional[dict]):
        """Salva a imagem do produto e atualiza o products.json na pasta storefront com categorias e códigos sequenciais."""
        import shutil
        import json
        try:
            item_id = product_offer.get("itemId") or "000"
            storefront_dir = os.path.abspath(os.path.join(os.getcwd(), "storefront"))
            images_dir = os.path.join(storefront_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Copia a imagem principal (01_capa) para a pasta de imagens do site
            local_images = download_results.get("imagens_locais", [])
            local_image_name = ""
            if local_images:
                main_img_path = local_images[0]
                ext = os.path.splitext(main_img_path)[1] or ".jpg"
                local_image_name = f"{item_id}{ext}"
                dest_img_path = os.path.join(images_dir, local_image_name)
                shutil.copy2(main_img_path, dest_img_path)
                self.log_message(f"Imagem do site copiada: {local_image_name}")

            # Lê o arquivo JSON existente
            json_path = os.path.join(storefront_dir, "products.json")
            products_list = []
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        products_list = json.load(f)
                except Exception:
                    products_list = []

            # Verifica se já existe para obter o índice
            exists_idx = -1
            clean_item_id = int(item_id) if str(item_id).isdigit() else item_id
            for idx, p in enumerate(products_list):
                if p.get("itemId") == clean_item_id:
                    exists_idx = idx
                    break

            # Determina o código da oferta (preserva o antigo ou gera novo)
            if exists_idx >= 0:
                offer_code = products_list[exists_idx].get("code", f"#{len(products_list):02d}")
            else:
                offer_code = f"#{len(products_list) + 1:02d}"

            # Categoria da interface GUI
            category = self.category_combo.get()

            # Carrega descrição real se houver nos dados brutos
            description = ""
            if raw_data and "api_data" in raw_data:
                description = raw_data["api_data"].get("description", "")
            if not description:
                description = "Confira todos os detalhes do produto, cores, tamanhos e avaliações completas diretamente na página oficial da Shopee clicando no botão abaixo!"

            # Preço Original
            price_min = product_offer.get("priceMin") or product_offer.get("price") or "0.00"
            price_original = 0.0
            if raw_data and "api_data" in raw_data:
                api_v4_data = raw_data["api_data"]
                price_before = api_v4_data.get("price_before")
                if price_before and price_before > 0:
                    price_original = float(price_before / 100000)
            if price_original == 0.0:
                try:
                    price_original = float(price_min) * 1.35
                except Exception:
                    price_original = 0.0

            # Prepara a entrada do produto
            product_entry = {
                "itemId": clean_item_id,
                "code": offer_code,
                "category": category,
                "productName": product_offer.get("productName", "Produto"),
                "productLink": product_offer.get("productLink", ""),
                "offerLink": product_offer.get("offerLink", ""),
                "priceMin": float(price_min) if str(price_min).replace('.', '', 1).isdigit() else price_min,
                "priceOriginal": price_original,
                "imageUrl": product_offer.get("imageUrl", ""),
                "localImageName": local_image_name,
                "description": description
            }

            if exists_idx >= 0:
                products_list[exists_idx] = product_entry
                self.log_message(f"Produto {offer_code} (ID {item_id}) já existia na vitrine e foi atualizado.")
            else:
                products_list.append(product_entry)
                self.log_message(f"Novo produto {offer_code} (ID {item_id}) adicionado à vitrine web na categoria '{category}'.")

            # Grava de volta
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(products_list, f, indent=4, ensure_ascii=False)
                
            self.log_message("✅ Arquivo products.json da vitrine web atualizado!")
        except Exception as e:
            self.log_message(f"Erro ao salvar produto na vitrine web: {e}", "error")

    def open_storefront_folder(self):
        """Abre a pasta local da vitrine no Windows Explorer."""
        storefront_dir = os.path.abspath(os.path.join(os.getcwd(), "storefront"))
        os.makedirs(storefront_dir, exist_ok=True)
        os.startfile(storefront_dir)
        self.log_message("Pasta da vitrine aberta no Windows Explorer.")

    def preview_storefront(self):
        """Abre o arquivo index.html no navegador padrão."""
        index_path = os.path.abspath(os.path.join(os.getcwd(), "storefront", "index.html"))
        if os.path.exists(index_path):
            import webbrowser
            webbrowser.open(f"file:///{index_path.replace(os.sep, '/')}")
            self.log_message("Visualização local da vitrine aberta no navegador.")
        else:
            messagebox.showerror("Erro", "Arquivo index.html não encontrado na pasta storefront.")

    def publish_to_github(self):
        """Executa git add, commit e push para atualizar o GitHub Pages em segundo plano."""
        self.publish_github_btn.configure(state="disabled")
        self.log_message("Iniciando publicação no GitHub Pages...")
        
        def run_git_commands():
            import subprocess
            try:
                # Verifica se é um repositório git
                res = subprocess.run(["git", "status"], capture_output=True, text=True, cwd=os.getcwd())
                if res.returncode != 0:
                    self.log_message("Erro: Pasta local não é um repositório Git! Inicialize o repositório git primeiro.", "error")
                    self.after(0, lambda: messagebox.showerror("Erro de Git", "Esta pasta não está configurada como repositório Git.\n\nPara configurar:\n1. Crie um repositório no GitHub\n2. Execute 'git init' e configure o remote origin nesta pasta.", parent=self))
                    return

                # Executa git add
                self.log_message("Executando: git add storefront/")
                subprocess.run(["git", "add", "storefront/"], check=True, cwd=os.getcwd())
                
                # Executa git commit
                self.log_message("Executando: git commit")
                commit_msg = "Atualização automática de produtos da vitrine"
                subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, cwd=os.getcwd())
                
                # Executa git push
                self.log_message("Executando: git push origin...")
                # Tenta descobrir o branch padrão (main ou master)
                branch_res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=os.getcwd())
                branch_name = branch_res.stdout.strip() or "main"
                
                push_res = subprocess.run(["git", "push", "origin", branch_name], capture_output=True, text=True, cwd=os.getcwd())
                if push_res.returncode == 0:
                    self.log_message(f"✅ Sucesso! Modificações enviadas para a branch '{branch_name}'.")
                    self.after(0, lambda: messagebox.showinfo("Sucesso", f"Vitrine publicada com sucesso no GitHub Pages!\nAs alterações estarão online em alguns instantes.", parent=self))
                else:
                    self.log_message(f"Erro ao dar push: {push_res.stderr}", "error")
                    self.after(0, lambda: messagebox.showerror("Erro de Git Push", f"Não foi possível enviar para o GitHub:\n\n{push_res.stderr}", parent=self))
            except Exception as e:
                self.log_message(f"Exceção durante publicação Git: {e}", "error")
                self.after(0, lambda: messagebox.showerror("Erro", f"Erro inesperado no processo do Git:\n{e}", parent=self))
            finally:
                self.after(0, lambda: self.publish_github_btn.configure(state="normal"))

        # Executa em segundo plano para não travar a GUI
        threading.Thread(target=run_git_commands, daemon=True).start()

    def open_cookie_import_dialog(self):
        """Abre uma janela modal para colar os cookies da Shopee."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Importar Cookies da Shopee")
        dialog.geometry("500x400")
        dialog.transient(self)  # Define como modal temporário
        dialog.grab_set()       # Foca a interação apenas nesta janela
        
        lbl = ctk.CTkLabel(
            dialog, 
            text="Cole o JSON de cookies (ex: EditThisCookie) ou string do cabeçalho:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl.pack(pady=10, padx=15, anchor="w")
        
        textbox = ctk.CTkTextbox(dialog, height=250)
        textbox.pack(fill="both", expand=True, padx=15, pady=5)
        
        def save():
            raw_text = textbox.get("1.0", "end").strip()
            if not raw_text:
                messagebox.showerror("Erro", "O campo de cookies está vazio.", parent=dialog)
                return
            
            success = self.api.save_cookies(raw_text)
            if success:
                self.log_message("✅ Cookies importados e salvos com sucesso!")
                messagebox.showinfo("Sucesso", "Cookies da Shopee salvos com sucesso!", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("Erro", "Formato de cookies inválido. Certifique-se de que é um JSON válido ou formato 'Chave=Valor;'.", parent=dialog)
                
        btn_save = ctk.CTkButton(
            dialog, 
            text="Salvar Cookies", 
            command=save,
            fg_color="#EE4D2D",
            hover_color="#D13F21"
        )
        btn_save.pack(pady=15)

if __name__ == "__main__":
    app = ShopeeApp()
    app.mainloop()
