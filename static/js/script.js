// Adicione este script à sua página ou inclua-o no arquivo script.js

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
    
    // Função para mostrar um contador de itens visíveis/total
    function setupItemCounter() {
        const tabelas = document.querySelectorAll('.table-responsive');
        
        tabelas.forEach(tabela => {
            const totalRows = tabela.querySelectorAll('tbody tr').length;
            const visibleRows = tabela.querySelectorAll('tbody tr:not(.d-none)').length;
            
            // Se houver um contador associado a esta tabela
            const contador = tabela.parentElement.querySelector('.item-counter');
            if (contador && visibleRows < totalRows) {
                contador.textContent = `Mostrando ${visibleRows} de ${totalRows} itens`;
                contador.classList.remove('d-none');
            }
        });
    }
    
    // Função para alternar entre ver 5 itens e ver todos
    function setupToggleViewButton() {
        const btnVerTodos = document.querySelectorAll('.btn-ver-todos');
        
        btnVerTodos.forEach(btn => {
            btn.addEventListener('click', function(e) {
                // Se não estivermos redirecionando para uma nova página
                if (this.getAttribute('href') === '#') {
                    e.preventDefault();
                    
                    const tabela = document.querySelector(this.dataset.target);
                    const rows = tabela.querySelectorAll('tbody tr');
                    
                    // Se estamos mostrando todos os itens
                    if (this.dataset.state === 'todos') {
                        // Esconder itens além dos primeiros 5
                        rows.forEach((row, index) => {
                            if (index >= 5) {
                                row.classList.add('d-none');
                            }
                        });
                        
                        this.dataset.state = 'poucos';
                        this.innerHTML = '<i class="fas fa-eye me-1"></i> Ver todos os itens';
                    } else {
                        // Mostrar todos os itens
                        rows.forEach(row => {
                            row.classList.remove('d-none');
                        });
                        
                        this.dataset.state = 'todos';
                        this.innerHTML = '<i class="fas fa-eye-slash me-1"></i> Ver menos itens';
                    }
                    
                    // Atualizar contador
                    setupItemCounter();
                }
            });
        });
    }
    
    // Executar as funções
    highlightNewItems();
    enhanceScrollExperience();
    setupItemCounter();
    setupToggleViewButton();
    
    // Inicializar paginações nas tabelas
    document.querySelectorAll('[id$="paginacao"]').forEach(paginacao => {
        const tabelaId = paginacao.id.replace('paginacao', 'Table');
        const tabela = document.getElementById(tabelaId);
        if (tabela) {
            const linhas = tabela.querySelectorAll('tbody tr');
            inicializarPaginacao(linhas, paginacao, 10);
        }
    });
});

/**
 * Inicializa a paginação para qualquer tabela
 * @param {NodeList} linhas - Lista de linhas da tabela
 * @param {HTMLElement} paginacao - Elemento de paginação
 * @param {Number} itemsPorPagina - Quantidade de itens por página
 * @returns {Object} Objeto com métodos de controle da paginação
 */
function inicializarPaginacao(linhas, paginacao, itemsPorPagina = 10) {
    if (!paginacao) return;
    
    let paginaAtual = 1;
    
    // Função para mostrar as linhas da página atual
    function mostrarLinhas() {
        // Ocultar todas as linhas
        linhas.forEach(linha => {
            linha.style.display = 'none';
        });
        
        // Calcular índices das linhas a serem exibidas
        const inicio = (paginaAtual - 1) * itemsPorPagina;
        const fim = Math.min(inicio + itemsPorPagina, linhas.length);
        
        // Mostrar apenas as linhas da página atual
        for (let i = inicio; i < fim; i++) {
            if (i < linhas.length) {
                linhas[i].style.display = '';
            }
        }
        
        // Atualizar a paginação
        atualizarPaginacao(linhas.length);
    }
    
    // Função para atualizar os controles de paginação
    function atualizarPaginacao(totalItens) {
        const totalPaginas = Math.ceil(totalItens / itemsPorPagina);
        
        // Limpar paginação atual
        paginacao.innerHTML = '';
        
        // Não mostrar paginação se tiver apenas uma página
        if (totalPaginas <= 1) {
            return;
        }
        
        // Botão Anterior
        const itemAnterior = document.createElement('li');
        itemAnterior.className = `page-item ${paginaAtual === 1 ? 'disabled' : ''}`;
        
        const linkAnterior = document.createElement('a');
        linkAnterior.className = 'page-link';
        linkAnterior.href = '#';
        linkAnterior.setAttribute('aria-label', 'Anterior');
        linkAnterior.innerHTML = '&laquo;';
        linkAnterior.addEventListener('click', (e) => {
            e.preventDefault();
            if (paginaAtual > 1) {
                paginaAtual--;
                mostrarLinhas();
            }
        });
        
        itemAnterior.appendChild(linkAnterior);
        paginacao.appendChild(itemAnterior);
        
        // Números das páginas - mostrar todas as páginas ou limitar com elipses
        const maxPaginasVisiveis = 5;
        
        if (totalPaginas <= maxPaginasVisiveis) {
            // Se tiver poucas páginas, mostrar todas
            for (let i = 1; i <= totalPaginas; i++) {
                adicionarPagina(i);
            }
        } else {
            // Caso contrário, mostrar um intervalo com elipses
            // Sempre mostrar primeira página
            adicionarPagina(1);
            
            // Calcular intervalo em torno da página atual
            let inicio = Math.max(2, paginaAtual - 1);
            let fim = Math.min(totalPaginas - 1, paginaAtual + 1);
            
            // Ajustar para mostrar sempre 3 páginas
            if (inicio === 2) fim = Math.min(4, totalPaginas - 1);
            if (fim === totalPaginas - 1) inicio = Math.max(2, totalPaginas - 3);
            
            // Adicionar elipse antes do intervalo se necessário
            if (inicio > 2) {
                const itemElipse = document.createElement('li');
                itemElipse.className = 'page-item disabled';
                const linkElipse = document.createElement('a');
                linkElipse.className = 'page-link';
                linkElipse.href = '#';
                linkElipse.textContent = '...';
                itemElipse.appendChild(linkElipse);
                paginacao.appendChild(itemElipse);
            }
            
            // Adicionar páginas do intervalo
            for (let i = inicio; i <= fim; i++) {
                adicionarPagina(i);
            }
            
            // Adicionar elipse depois do intervalo se necessário
            if (fim < totalPaginas - 1) {
                const itemElipse = document.createElement('li');
                itemElipse.className = 'page-item disabled';
                const linkElipse = document.createElement('a');
                linkElipse.className = 'page-link';
                linkElipse.href = '#';
                linkElipse.textContent = '...';
                itemElipse.appendChild(linkElipse);
                paginacao.appendChild(itemElipse);
            }
            
            // Sempre mostrar última página
            adicionarPagina(totalPaginas);
        }
        
        // Botão Próximo
        const itemProximo = document.createElement('li');
        itemProximo.className = `page-item ${paginaAtual === totalPaginas || totalPaginas === 0 ? 'disabled' : ''}`;
        
        const linkProximo = document.createElement('a');
        linkProximo.className = 'page-link';
        linkProximo.href = '#';
        linkProximo.setAttribute('aria-label', 'Próximo');
        linkProximo.innerHTML = '&raquo;';
        linkProximo.addEventListener('click', (e) => {
            e.preventDefault();
            if (paginaAtual < totalPaginas) {
                paginaAtual++;
                mostrarLinhas();
            }
        });
        
        itemProximo.appendChild(linkProximo);
        paginacao.appendChild(itemProximo);
    }
    
    // Função auxiliar para adicionar botão de página
    function adicionarPagina(numero) {
        const item = document.createElement('li');
        item.className = `page-item ${numero === paginaAtual ? 'active' : ''}`;
        
        const link = document.createElement('a');
        link.className = 'page-link';
        link.href = '#';
        link.textContent = numero;
        link.addEventListener('click', (e) => {
            e.preventDefault();
            paginaAtual = numero;
            mostrarLinhas();
        });
        
        item.appendChild(link);
        paginacao.appendChild(item);
    }
    
    // Inicializar a paginação
    mostrarLinhas();
    
    // Interface pública
    return {
        atualizarPagina: mostrarLinhas,
        irParaPagina: function(pagina) {
            if (pagina >= 1 && pagina <= Math.ceil(linhas.length / itemsPorPagina)) {
                paginaAtual = pagina;
                mostrarLinhas();
            }
        }
    };
}