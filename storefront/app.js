document.addEventListener('DOMContentLoaded', () => {
    let products = [];
    let activeCategory = 'Todos';
    
    const productsGrid = document.getElementById('products-grid');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const productCount = document.getElementById('product-count');
    const categoryTabsContainer = document.getElementById('category-tabs');
    const currentCategoryTitle = document.getElementById('current-category-title');
    
    // Elementos do Modal
    const modal = document.getElementById('product-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalImg = document.getElementById('modal-product-img');
    const modalCode = document.getElementById('modal-product-code');
    const modalCategory = document.getElementById('modal-product-category');
    const modalTitle = document.getElementById('modal-product-title');
    const modalOldPrice = document.getElementById('modal-product-old-price');
    const modalPrice = document.getElementById('modal-product-price');
    const modalDesc = document.getElementById('modal-product-desc');
    const modalBuyLink = document.getElementById('modal-buy-link');

    // Carrega os dados do arquivo JSON
    async function loadProducts() {
        try {
            const response = await fetch('products.json?t=' + new Date().getTime());
            if (!response.ok) throw new Error('Não foi possível carregar os produtos.');
            products = await response.json();
            
            // Inverte a ordem para mostrar os mais novos primeiro
            products.reverse();
            
            // Renderiza abas de categorias e produtos
            renderCategoryTabs();
            filterAndRender();
        } catch (error) {
            console.error(error);
            productsGrid.innerHTML = `
                <div class="empty-state">
                    <p>Nenhuma oferta cadastrada no momento. Adicione produtos pelo painel de automação!</p>
                </div>
            `;
        }
    }

    // Renderiza botões de categoria dinamicamente
    function renderCategoryTabs() {
        categoryTabsContainer.innerHTML = '';
        
        // Coleta todas as categorias únicas presentes nos produtos
        const uniqueCategories = ['Todos'];
        products.forEach(p => {
            if (p.category && !uniqueCategories.includes(p.category)) {
                uniqueCategories.push(p.category);
            }
        });

        uniqueCategories.forEach(cat => {
            const btn = document.createElement('button');
            btn.className = `category-tab ${activeCategory === cat ? 'active' : ''}`;
            btn.textContent = cat;
            btn.addEventListener('click', () => {
                activeCategory = cat;
                
                // Atualiza classe ativa dos botões
                document.querySelectorAll('.category-tab').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                filterAndRender();
            });
            categoryTabsContainer.appendChild(btn);
        });
    }

    // Lógica Combinada de Filtro & Busca
    function filterAndRender() {
        const query = searchInput.value.toLowerCase().trim();
        
        // Filtra por Categoria e por Busca (Nome ou Código da Oferta)
        const filtered = products.filter(product => {
            const matchesCategory = activeCategory === 'Todos' || product.category === activeCategory;
            
            const productName = product.productName ? product.productName.toLowerCase() : '';
            const productCode = product.code ? product.code.toLowerCase() : '';
            // Também permite buscar apenas pelo número digitado (ex: "03" encontra "#03")
            const numberQuery = query.startsWith('#') ? query : '#' + query;

            const matchesSearch = query === '' || 
                                  productName.includes(query) || 
                                  productCode.includes(query) ||
                                  productCode.includes(numberQuery);
                                  
            return matchesCategory && matchesSearch;
        });

        // Atualiza título da seção
        currentCategoryTitle.textContent = activeCategory === 'Todos' ? '🔥 Todas as Ofertas' : `Nicho: ${activeCategory}`;
        renderProducts(filtered);
    }

    // Renderiza a lista de produtos filtrados
    function renderProducts(items) {
        productsGrid.innerHTML = '';
        productCount.textContent = `${items.length} produto${items.length !== 1 ? 's' : ''}`;
        
        if (items.length === 0) {
            productsGrid.innerHTML = `
                <div class="empty-state">
                    <p>Nenhum produto encontrado para esta busca.</p>
                </div>
            `;
            return;
        }

        items.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card';
            
            // Tratamento de preços para exibição
            const price = parseFloat(product.priceMin || product.price || 0);
            const oldPrice = parseFloat(product.priceOriginal || (price * 1.35));
            
            const formattedPrice = price.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            const formattedOldPrice = oldPrice.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

            // Imagem (se for caminho local, aponta para images/)
            let imgSrc = product.imageUrl || '';
            if (product.localImageName) {
                imgSrc = 'images/' + product.localImageName;
            }

            const code = product.code || '#--';
            const category = product.category || 'Outros';

            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img src="${imgSrc}" alt="${product.productName}" loading="lazy">
                </div>
                <div class="card-body">
                    <div class="card-tags">
                        <span class="product-code-badge">${code}</span>
                        <span class="product-category-badge">${category}</span>
                    </div>
                    <h3 class="product-title">${product.productName}</h3>
                    <div class="card-footer">
                        <div class="price-container">
                            <span class="old-price">${formattedOldPrice}</span>
                            <span class="new-price">${formattedPrice}</span>
                        </div>
                        <button class="btn-card-buy">Detalhes</button>
                    </div>
                </div>
            `;

            // Abre o modal ao clicar no card
            card.addEventListener('click', () => openModal(product));
            productsGrid.appendChild(card);
        });
    }

    // Modal de Detalhes
    function openModal(product) {
        const price = parseFloat(product.priceMin || product.price || 0);
        const oldPrice = parseFloat(product.priceOriginal || (price * 1.35));
        
        let imgSrc = product.imageUrl || '';
        if (product.localImageName) {
            imgSrc = 'images/' + product.localImageName;
        }

        modalImg.src = imgSrc;
        modalCode.textContent = product.code || '#--';
        modalCategory.textContent = product.category || 'Outros';
        modalTitle.textContent = product.productName;
        
        modalOldPrice.textContent = oldPrice.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        modalPrice.textContent = price.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
        
        modalDesc.textContent = product.description || 'Confira todos os detalhes do produto, cores, tamanhos e avaliações completas diretamente na página oficial da Shopee clicando no botão abaixo!';
        modalBuyLink.href = product.offerLink || product.productLink || '#';
        
        modal.classList.add('active');
    }

    function closeModal() {
        modal.classList.remove('active');
    }

    // Eventos de Fechamento do Modal
    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    searchInput.addEventListener('input', filterAndRender);
    searchBtn.addEventListener('click', filterAndRender);

    // Inicializa
    loadProducts();
});
