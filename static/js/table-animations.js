document.addEventListener('DOMContentLoaded', function() {
    // Função para destacar novos itens
    function highlightNewItems() {
        // Se houver um parâmetro 'novo' na URL, encontrar e destacar o elemento
        const urlParams = new URLSearchParams(window.location.search);
        const novoItem = urlParams.get('novo');
        
        if (novoItem) {
            // Encontrar o elemento com o ID correspondente
            const elemento = document.getElementById(`item-${novoItem}`);
            
            if (elemento) {
                // Adicionar a classe de destaque
                elemento.classList.add('highlight-new-row');
                
                // Rolar até o elemento
                elemento.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }
    
    // Função para melhorar a experiência de rolagem
    function enhanceScrollExperience() {
        const tabelas = document.querySelectorAll('.table-responsive');
        
        tabelas.forEach(tabela => {
            // Adicionar sombra na parte superior ao rolar
            tabela.addEventListener('scroll', function() {
                const thead = this.querySelector('thead');
                
                if (this.scrollTop > 0) {
                    thead.classList.add('shadow-sm');
                } else {
                    thead.classList.remove('shadow-sm');
                }
            });
        });
    }
    
    // Executar as funções
    highlightNewItems();
    enhanceScrollExperience();
}); 