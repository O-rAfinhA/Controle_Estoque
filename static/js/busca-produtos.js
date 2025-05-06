// Funcionalidade de busca para a página de produtos
document.addEventListener('DOMContentLoaded', function() {
    const formBusca = document.getElementById('formBuscaProdutos');
    const inputProduto = document.getElementById('searchProduto');
    const inputCliente = document.getElementById('searchCliente');
    const resultadoBusca = document.getElementById('resultadoBusca');
    const contadorResultados = document.getElementById('contadorResultados');
    const filtrosAplicados = document.getElementById('filtrosAplicados');
    const produtoBadge = document.getElementById('produtoBadge');
    const clienteBadge = document.getElementById('clienteBadge');
    const btnLimparFiltros = document.getElementById('limparFiltros');

    if (formBusca) {
        formBusca.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const termoProduto = inputProduto.value.toLowerCase().trim();
            const termoCliente = inputCliente.value.toLowerCase().trim();
            
            filtrarProdutos(termoProduto, termoCliente);
        });
    }
    
    if (btnLimparFiltros) {
        btnLimparFiltros.addEventListener('click', function() {
            if (inputProduto) inputProduto.value = '';
            if (inputCliente) inputCliente.value = '';
            filtrarProdutos('', '');
        });
    }
    
    function filtrarProdutos(termoProduto, termoCliente) {
        const tabela = document.getElementById('tabelaProdutos');
        if (!tabela) return;
        
        const linhas = tabela.querySelectorAll('tbody tr');
        let matchCount = 0;
        
        // Filtrar linhas
        linhas.forEach(function(linha) {
            const celulaProduto = linha.querySelector('td:nth-child(1)');
            const celulaCliente = linha.querySelector('td:nth-child(2)');
            
            if (!celulaProduto || !celulaCliente) return;
            
            const textoProduto = celulaProduto.textContent.toLowerCase();
            const textoCliente = celulaCliente.textContent.toLowerCase();
            
            const matchProduto = termoProduto === '' || textoProduto.includes(termoProduto);
            const matchCliente = termoCliente === '' || textoCliente.includes(termoCliente);
            
            if (matchProduto && matchCliente) {
                linha.style.display = '';
                matchCount++;
            } else {
                linha.style.display = 'none';
            }
        });
        
        // Atualizar interface
        if (resultadoBusca) {
            resultadoBusca.style.display = 'flex';
            
            if (contadorResultados) {
                contadorResultados.textContent = matchCount;
            }
            
            const temFiltros = termoProduto !== '' || termoCliente !== '';
            
            if (filtrosAplicados) {
                filtrosAplicados.style.display = temFiltros ? 'block' : 'none';
            }
            
            if (produtoBadge) {
                if (termoProduto !== '') {
                    produtoBadge.textContent = `Produto: "${termoProduto}"`;
                    produtoBadge.style.display = 'inline-block';
                } else {
                    produtoBadge.style.display = 'none';
                }
            }
            
            if (clienteBadge) {
                if (termoCliente !== '') {
                    clienteBadge.textContent = `Cliente: "${termoCliente}"`;
                    clienteBadge.style.display = 'inline-block';
                } else {
                    clienteBadge.style.display = 'none';
                }
            }
        }
    }
    
    // ================ FUNCIONALIDADE DE EDIÇÃO DE PRODUTOS ================
    
    // Selecionando elementos do DOM
    const editarBtns = document.querySelectorAll('.edit-produto');
    const editarProdutoModal = document.getElementById('editarProdutoModal');
    const formEditarProduto = document.getElementById('form-editar-produto');
    const btnSalvarEdicao = document.getElementById('btnSalvarEdicaoProduto');
    const editModalAlertContainer = document.getElementById('modal-edit-alert-container');
    
    // Dados para edição
    let editComponentesLista = [];
    let editComponenteSelecionado = null;
    
    // Configuração do modal de edição
    if (editarProdutoModal) {
        // Limpar dados quando o modal é fechado
        editarProdutoModal.addEventListener('hidden.bs.modal', function() {
            if (formEditarProduto) formEditarProduto.reset();
            if (editModalAlertContainer) editModalAlertContainer.innerHTML = '';
            editComponentesLista = [];
            atualizarListaComponentesEdicao();
            editComponenteSelecionado = null;
        });
    }
    
    // Event listeners para os botões de editar produto
    if (editarBtns && editarBtns.length > 0) {
        editarBtns.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                const produtoId = this.getAttribute('data-produto-id');
                carregarDadosProduto(produtoId);
            });
        });
    }
    
    // Função para carregar os dados do produto para edição
    function carregarDadosProduto(produtoId) {
        // Mostrar loading
        if (editModalAlertContainer) {
            editModalAlertContainer.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                        <div>Carregando dados do produto...</div>
                    </div>
                </div>
            `;
        }
        
        // Fazer requisição para obter dados do produto
        fetch(`/api/produto/${produtoId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Erro ao carregar dados do produto: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Dados do produto carregados:', data);
                
                // Limpar alertas
                if (editModalAlertContainer) editModalAlertContainer.innerHTML = '';
                
                // Preencher o formulário com os dados do produto
                document.getElementById('edit-produto-id').value = data.id;
                document.getElementById('edit-nome').value = data.nome;
                document.getElementById('edit-descricao').value = data.descricao || '';
                
                // Configurar action do formulário
                formEditarProduto.action = `/produtos/editar/${data.id}`;
                
                // Carregar componentes do produto
                editComponentesLista = [];
                if (data.componentes && data.componentes.length > 0) {
                    data.componentes.forEach(comp => {
                        editComponentesLista.push({
                            codigo: comp.codigo,
                            nome: comp.nome,
                            quantidade: comp.quantidade
                        });
                    });
                }
                
                // Atualizar lista de componentes na interface
                atualizarListaComponentesEdicao();
                
                // Abrir o modal
                const modal = new bootstrap.Modal(document.getElementById('editarProdutoModal'));
                modal.show();
            })
            .catch(error => {
                console.error('Erro ao carregar produto:', error);
                
                // Exibir mensagem de erro
                if (editModalAlertContainer) {
                    editModalAlertContainer.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-exclamation-circle me-2"></i>
                                <div>Erro ao carregar dados do produto. Por favor, tente novamente.</div>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
                        </div>
                    `;
                }
            });
    }
    
    // Função para atualizar a lista de componentes no modal de edição
    function atualizarListaComponentesEdicao() {
        const tbody = document.getElementById('edit-componentes-lista');
        const semComponentesMsg = document.getElementById('edit-sem-componentes');
        
        if (!tbody || !semComponentesMsg) return;
        
        // Limpa a tabela
        tbody.innerHTML = '';
        
        // Atualiza o JSON hidden field
        const jsonField = document.getElementById('edit-componentes-json');
        if (jsonField) {
            jsonField.value = JSON.stringify(editComponentesLista);
        }
        
        // Mostra/esconde a mensagem "sem componentes"
        if (editComponentesLista.length === 0) {
            semComponentesMsg.style.display = 'block';
            return;
        }
        
        semComponentesMsg.style.display = 'none';
        
        // Adiciona os componentes na tabela
        editComponentesLista.forEach((componente, index) => {
            const tr = document.createElement('tr');
            
            tr.innerHTML = `
                <td>${componente.codigo}</td>
                <td>${componente.nome}</td>
                <td>${componente.quantidade}</td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger remover-componente-edit" data-index="${index}">
                        <i class="fas fa-trash"></i> Remover
                    </button>
                </td>
            `;
            
            tbody.appendChild(tr);
        });
        
        // Adiciona evento aos botões de remover
        document.querySelectorAll('#edit-componentes-lista .remover-componente-edit').forEach(btn => {
            btn.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                removerComponenteEdicao(index);
            });
        });
    }
    
    // Função para remover um componente da lista de edição
    function removerComponenteEdicao(index) {
        editComponentesLista.splice(index, 1);
        atualizarListaComponentesEdicao();
    }
    
    // Cliente Search Functionality para o modal de edição
    const editClienteInput = document.getElementById('edit-descricao');
    const editClienteSuggestions = document.getElementById('edit-cliente-suggestions');
    let editDebounceTimer;

    if (editClienteInput && editClienteSuggestions) {
        // Add input event listener with debounce
        editClienteInput.addEventListener('input', function() {
            clearTimeout(editDebounceTimer);
            const inputValue = this.value.trim();
            
            // Clear suggestions if input is empty
            if (inputValue.length < 2) {
                editClienteSuggestions.innerHTML = '';
                editClienteSuggestions.classList.add('d-none');
                return;
            }
            
            // Debounce to avoid too many requests
            editDebounceTimer = setTimeout(() => {
                fetch(`/api/search-clientes?termo=${encodeURIComponent(inputValue)}`)
                    .then(response => response.json())
                    .then(data => {
                        editClienteSuggestions.innerHTML = '';
                        
                        if (data.length > 0) {
                            data.forEach(cliente => {
                                const div = document.createElement('div');
                                div.className = 'p-2 cliente-suggestion';
                                div.textContent = cliente;
                                div.style.cursor = 'pointer';
                                div.style.borderBottom = '1px solid #eee';
                                
                                // Highlight the match
                                const regex = new RegExp(`(${inputValue})`, 'gi');
                                div.innerHTML = cliente.replace(regex, '<strong>$1</strong>');
                                
                                // Click to select
                                div.addEventListener('click', function() {
                                    editClienteInput.value = cliente;
                                    editClienteSuggestions.classList.add('d-none');
                                });
                                
                                editClienteSuggestions.appendChild(div);
                            });
                            
                            editClienteSuggestions.classList.remove('d-none');
                        } else {
                            editClienteSuggestions.classList.add('d-none');
                        }
                    })
                    .catch(error => console.error('Erro ao buscar clientes:', error));
            }, 300);
        });
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (!editClienteInput.contains(e.target) && !editClienteSuggestions.contains(e.target)) {
                editClienteSuggestions.classList.add('d-none');
            }
        });
    }

    // Componente Search Functionality para o modal de edição
    const editComponenteInput = document.getElementById('edit-componente-search');
    const editComponenteSuggestions = document.getElementById('edit-componente-suggestions');
    const editQuantidadeComponenteInput = document.getElementById('edit-quantidade-componente');
    const editAdicionarComponenteBtn = document.getElementById('edit-adicionar-componente');
    let editDebounceTimerComponente;

    if (editComponenteInput && editComponenteSuggestions) {
        // Add input event listener with debounce
        editComponenteInput.addEventListener('input', function() {
            clearTimeout(editDebounceTimerComponente);
            const inputValue = this.value.trim();
            editComponenteSelecionado = null;
            
            // Clear suggestions if input is empty
            if (inputValue.length < 2) {
                editComponenteSuggestions.innerHTML = '';
                editComponenteSuggestions.classList.add('d-none');
                return;
            }
            
            // Debounce to avoid too many requests
            editDebounceTimerComponente = setTimeout(() => {
                fetch(`/api/search-componentes?termo=${encodeURIComponent(inputValue)}`)
                    .then(response => response.json())
                    .then(data => {
                        editComponenteSuggestions.innerHTML = '';
                        
                        if (data.length > 0) {
                            data.forEach(componente => {
                                const div = document.createElement('div');
                                div.className = 'p-2 cliente-suggestion';
                                div.textContent = `${componente.nome} (${componente.codigo})`;
                                div.setAttribute('data-codigo', componente.codigo);
                                div.setAttribute('data-nome', componente.nome);
                                div.style.cursor = 'pointer';
                                div.style.borderBottom = '1px solid #eee';
                                
                                // Highlight the match
                                const displayText = `${componente.nome} (${componente.codigo})`;
                                const regex = new RegExp(`(${inputValue})`, 'gi');
                                div.innerHTML = displayText.replace(regex, '<strong>$1</strong>');
                                
                                // Click to select
                                div.addEventListener('click', function() {
                                    editComponenteInput.value = componente.nome;
                                    editComponenteSelecionado = componente.codigo;
                                    editComponenteSuggestions.classList.add('d-none');
                                });
                                
                                editComponenteSuggestions.appendChild(div);
                            });
                            
                            editComponenteSuggestions.classList.remove('d-none');
                        } else {
                            editComponenteSuggestions.classList.add('d-none');
                        }
                    })
                    .catch(error => console.error('Erro ao buscar componentes:', error));
            }, 300);
        });
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (!editComponenteInput.contains(e.target) && !editComponenteSuggestions.contains(e.target)) {
                editComponenteSuggestions.classList.add('d-none');
            }
        });
    }
    
    // Implementação do botão para adicionar componente no modal de edição
    if (editAdicionarComponenteBtn) {
        editAdicionarComponenteBtn.addEventListener('click', function() {
            if (editComponenteSelecionado) {
                const quantidade = parseInt(editQuantidadeComponenteInput.value) || 1;
                
                if (quantidade < 1) {
                    alert('A quantidade deve ser pelo menos 1.');
                    return;
                }
                
                // Verificar se já existe na lista
                const componenteExistente = editComponentesLista.findIndex(c => c.codigo === editComponenteSelecionado);
                
                if (componenteExistente >= 0) {
                    // Atualiza a quantidade se já existir
                    editComponentesLista[componenteExistente].quantidade = quantidade;
                } else {
                    // Adiciona novo componente
                    editComponentesLista.push({
                        codigo: editComponenteSelecionado,
                        nome: editComponenteInput.value,
                        quantidade: quantidade
                    });
                }
                
                // Resetar campos
                editComponenteInput.value = '';
                editComponenteSelecionado = null;
                editQuantidadeComponenteInput.value = '1';
                
                // Atualizar a tabela
                atualizarListaComponentesEdicao();
            } else {
                alert('Por favor, selecione um componente.');
            }
        });
    }
    
    // Adicionar Enter para o campo de quantidade de componente no modal de edição
    if (editQuantidadeComponenteInput) {
        editQuantidadeComponenteInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                editAdicionarComponenteBtn.click();
            }
        });
    }
    
    // Adicionar Enter para o campo de busca de componente no modal de edição
    if (editComponenteInput) {
        editComponenteInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && editComponenteSelecionado) {
                event.preventDefault();
                editAdicionarComponenteBtn.click();
            }
        });
    }
    
    // Evento do botão salvar no modal de edição
    if (btnSalvarEdicao) {
        btnSalvarEdicao.addEventListener('click', function() {
            salvarEdicaoProduto();
        });
    }
    
    // Adicionar listener para tecla Enter no modal de edição de produtos
    if (editarProdutoModal) {
        editarProdutoModal.addEventListener('keydown', function(event) {
            // Verificar se a tecla pressionada é Enter e se não está em um textarea
            if (event.key === 'Enter' && event.target.tagName !== 'TEXTAREA') {
                // Impedir o comportamento padrão do Enter (que poderia enviar o formulário diretamente)
                event.preventDefault();
                // Chamar a função para salvar o produto
                salvarEdicaoProduto();
            }
        });
    }
    
    // Função para salvar a edição do produto
    function salvarEdicaoProduto() {
        const form = document.getElementById('form-editar-produto');
        const nome = document.getElementById('edit-nome').value.trim();
        const produtoId = document.getElementById('edit-produto-id').value;
        
        if (!form || !nome || !produtoId) {
            alert('Dados incompletos. Por favor, preencha todos os campos obrigatórios.');
            return;
        }
        
        // Validar se tem componentes
        if (editComponentesLista.length === 0) {
            if (editModalAlertContainer) {
                editModalAlertContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            <div>Adicione pelo menos um componente ao produto.</div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
                    </div>
                `;
            }
            return;
        }
        
        // Atualizar o valor do campo oculto com a lista de componentes em JSON
        document.getElementById('edit-componentes-json').value = JSON.stringify(editComponentesLista);
        
        // Criar FormData com os dados do formulário
        const formData = new FormData(form);
        
        // Adicionar flag para identificar que é um produto editado via modal
        formData.append('from_modal', 'true');
        
        // Mostrar loading
        if (editModalAlertContainer) {
            editModalAlertContainer.innerHTML = `
                <div class="alert alert-info">
                    <div class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                        <div>Salvando alterações...</div>
                    </div>
                </div>
            `;
        }
        
        // Enviar o formulário via AJAX
        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            console.log("Resposta do servidor:", response.status, response.statusText);
            return response.text().then(html => {
                return { 
                    redirected: response.redirected, 
                    url: response.url, 
                    html: html,
                    status: response.status
                };
            });
        })
        .then(data => {
            // Verificar se o redirecionamento foi para a página de sucesso
            if (data.status === 302 || data.redirected) {
                // Se houve redirecionamento, considera como sucesso
                sessionStorage.setItem('product_edited', 'true');
                window.location.href = data.url || '/produtos';
                return;
            }
            
            // Verificar se há mensagens de erro na resposta HTML
            const containsError = data.html.includes('já existe') || 
                                 data.html.includes('danger') || 
                                 data.html.includes('alert-danger');
            
            if (containsError) {
                // Extrair mensagem de erro
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = data.html;
                const errorAlerts = tempDiv.querySelectorAll('.alert-danger');
                let mensagemErro = "Ocorreu um erro ao editar o produto.";
                
                if (errorAlerts.length > 0) {
                    const textoErro = errorAlerts[0].textContent.trim();
                    if (textoErro) {
                        mensagemErro = textoErro;
                    }
                }
                
                // Exibir mensagem de erro
                if (editModalAlertContainer) {
                    editModalAlertContainer.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            <div class="d-flex align-items-center">
                                <i class="fas fa-exclamation-circle me-2"></i>
                                <div>${mensagemErro}</div>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
                        </div>
                    `;
                }
                
                // Focar no campo de nome para facilitar a correção
                document.getElementById('edit-nome').focus();
            } else {
                // Sucesso sem redirecionamento explícito
                sessionStorage.setItem('product_edited', 'true');
                window.location.href = '/produtos';
            }
        })
        .catch(error => {
            console.error('Erro ao editar produto:', error);
            
            // Exibir mensagem de erro
            if (editModalAlertContainer) {
                editModalAlertContainer.innerHTML = `
                    <div class="alert alert-danger alert-dismissible fade show" role="alert">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            <div>Erro ao processar sua solicitação. Por favor, tente novamente.</div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
                    </div>
                `;
            }
        });
    }

    // Adicionar validação ao campo de nome do produto
    const nomeInput = document.getElementById('edit-nome');
    if (nomeInput) {
        nomeInput.addEventListener('blur', function() {
            const nome = this.value.trim();
            const modalAlertContainer = document.getElementById('modal-alert-container');
            
            // Limpar alertas anteriores relacionados ao nome
            const alertasAnteriores = modalAlertContainer.querySelectorAll('.alert-nome');
            alertasAnteriores.forEach(alerta => alerta.remove());
            
            // Se o nome estiver vazio, não validar
            if (!nome) return;
            
            // Verificar se o nome do produto já existe
            console.log(`Verificando nome do produto: '${nome}'`);
            
            fetch(`/api/check_product_name?nome=${encodeURIComponent(nome)}`)
                .then(response => {
                    console.log('Status da resposta:', response.status);
                    if (!response.ok) {
                        throw new Error(`Erro na verificação do nome do produto: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Resposta da API:', data);
                    
                    if (!data.valid) {
                        // Nome de produto já existe, mostrar popup de erro em vez do alerta interno
                        console.log('Nome de produto não disponível:', data.message);
                        
                        // Criar o popup de erro
                        const errorPopup = document.createElement('div');
                        errorPopup.style.position = 'fixed';
                        errorPopup.style.top = '0';
                        errorPopup.style.left = '0';
                        errorPopup.style.width = '100%';
                        errorPopup.style.height = '100%';
                        errorPopup.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
                        errorPopup.style.display = 'flex';
                        errorPopup.style.justifyContent = 'center';
                        errorPopup.style.alignItems = 'center';
                        errorPopup.style.zIndex = '9999';
                        
                        const errorContent = document.createElement('div');
                        errorContent.style.backgroundColor = '#212529';
                        errorContent.style.color = 'white';
                        errorContent.style.padding = '20px';
                        errorContent.style.borderRadius = '5px';
                        errorContent.style.maxWidth = '400px';
                        errorContent.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.3)';
                        
                        const errorTitle = document.createElement('div');
                        errorTitle.style.fontSize = '18px';
                        errorTitle.style.marginBottom = '10px';
                        errorTitle.textContent = '127.0.0.1:5000 diz';
                        
                        const errorMessage = document.createElement('div');
                        errorMessage.style.marginBottom = '20px';
                        errorMessage.textContent = 'Erro: Nome de produto já existe no sistema.';
                        
                        const errorButton = document.createElement('button');
                        errorButton.className = 'btn btn-primary';
                        errorButton.style.display = 'block';
                        errorButton.style.margin = '0 auto';
                        errorButton.style.backgroundColor = '#2e59d9';
                        errorButton.style.border = 'none';
                        errorButton.textContent = 'OK';
                        errorButton.addEventListener('click', function() {
                            document.body.removeChild(errorPopup);
                            document.getElementById('edit-nome').focus(); // Focar de volta no campo
                        });
                        
                        errorContent.appendChild(errorTitle);
                        errorContent.appendChild(errorMessage);
                        errorContent.appendChild(errorButton);
                        errorPopup.appendChild(errorContent);
                        
                        document.body.appendChild(errorPopup);
                    }
                })
                .catch(error => {
                    console.error('Erro ao verificar nome do produto:', error);
                });
        });
    }
}); 