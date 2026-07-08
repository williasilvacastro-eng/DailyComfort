document.addEventListener('DOMContentLoaded', () => {
    let products = [];
    const productsGrid = document.getElementById('products-grid');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const productCount = document.getElementById('product-count');
    
    // Elementos do Modal
    const modal = document.getElementById('product-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalImg = document.getElementById('modal-product-img');
    const modalId = document.getElementById('modal-product-id');
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
            
            renderProducts(products);
        } catch (error) {
            console.error(error);
            productsGrid.innerHTML = `
                <div class="empty-state">
                    <p>Nenhuma oferta cadastrada no momento. Adicione produtos pelo painel de automação!</p>
                </div>
            `;
        }
    }

    // Renderiza a lista de produtos na vitrine
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
            const oldPrice = parseFloat(product.priceOriginal || (price * 1.35)); // Estima 35% a mais se não houver original
            
            const formattedPrice = price.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            const formattedOldPrice = oldPrice.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

            // Imagem (se for caminho local, aponta para images/)
            let imgSrc = product.imageUrl || '';
            if (product.localImageName) {
                imgSrc = 'images/' + product.localImageName;
            }

            card.innerHTML = `
                <div class="card-img-wrapper">
                    <img src="${imgSrc}" alt="${product.productName}" loading="lazy">
                </div>
                <div class="card-body">
                    <span class="product-id-badge">COD: ${product.itemId}</span>
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
        modalId.textContent = `PRODUTO ID: ${product.itemId}`;
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

    // Busca e Filtros
    function filterProducts() {
        const query = searchInput.value.toLowerCase().strip ? searchInput.value.toLowerCase().strip() : searchInput.value.toLowerCase().trim();
        const filtered = products.filter(p => 
            p.productName.toLowerCase().includes(query) || 
            p.itemId.toString().includes(query)
        );
        renderProducts(filtered);
    }

    searchInput.addEventListener('input', filterProducts);
    searchBtn.addEventListener('click', filterProducts);

    // Inicializa
    loadProducts();
});
