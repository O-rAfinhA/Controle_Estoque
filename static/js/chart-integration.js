/**
 * Chart Integration for Estoque Management System
 * Este arquivo contém funções para criar e atualizar gráficos do dashboard
 * Requer Chart.js e o arquivo common.js
 */

// Gráficos do Dashboard
const EstoqueDashboard = {
    // Armazena instâncias de gráficos para atualização posterior
    charts: {},
    
    /**
     * Inicializa os gráficos do dashboard
     */
    initialize: function() {
        // Carrega Chart.js dinamicamente se não estiver carregado
        if (typeof Chart === 'undefined') {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
            script.integrity = 'sha256-+8RZJLOWj7T2UHOLzaIskY84nhXNrOaI3yYA0au9G0Y=';
            script.crossOrigin = 'anonymous';
            script.onload = () => this.createDashboardCharts();
            document.head.appendChild(script);
            
            // Adicionar CSS para gráficos
            const style = document.createElement('style');
            style.textContent = `
                .chart-container {
                    position: relative;
                    height: 300px;
                    margin-bottom: 20px;
                }
                .chart-info {
                    position: absolute;
                    bottom: 10px;
                    right: 10px;
                    font-size: 12px;
                    color: #6c757d;
                }
                .chart-title {
                    font-size: 1.1rem;
                    font-weight: 600;
                    margin-bottom: 15px;
                    color: #343a40;
                }
                @media (max-width: 768px) {
                    .chart-container {
                        height: 250px;
                    }
                }
            `;
            document.head.appendChild(style);
        } else {
            this.createDashboardCharts();
        }
    },
    
    /**
     * Cria os gráficos do dashboard
     */
    createDashboardCharts: function() {
        this.createInventoryStatusChart();
        this.createInventoryMovementChart();
        this.createTopComponentsChart();
        this.createSupplierPerformanceChart();
    },
    
    /**
     * Cria gráfico de status do estoque (Crítico/Baixo/Normal)
     */
    createInventoryStatusChart: function() {
        const chartContainer = document.getElementById('inventory-status-chart');
        if (!chartContainer) return;
        
        // Dados obtidos via AJAX
        this.fetchData('/api/inventory-status', (data) => {
            const canvas = document.createElement('canvas');
            canvas.id = 'inventory-status-canvas';
            chartContainer.appendChild(canvas);
            
            const chartData = {
                labels: ['Crítico', 'Baixo', 'Normal'],
                datasets: [{
                    data: [
                        data.critical || 0,
                        data.low || 0,
                        data.normal || 0
                    ],
                    backgroundColor: ['#e74a3b', '#f6c23e', '#1cc88a'],
                    borderWidth: 1
                }]
            };
            
            this.charts.inventoryStatus = ChartUtils.createPieChart('inventory-status-canvas', chartData, {
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            });
            
            // Adicionar texto de total
            const totalItems = (data.critical || 0) + (data.low || 0) + (data.normal || 0);
            const infoElement = document.createElement('div');
            infoElement.className = 'chart-info';
            infoElement.textContent = `Total: ${totalItems} itens`;
            chartContainer.appendChild(infoElement);
        });
    },
    
    /**
     * Cria gráfico de movimentações (Entradas vs Saídas)
     */
    createInventoryMovementChart: function() {
        const chartContainer = document.getElementById('inventory-movement-chart');
        if (!chartContainer) return;
        
        // Dados obtidos via AJAX
        this.fetchData('/api/inventory-movement', (data) => {
            const canvas = document.createElement('canvas');
            canvas.id = 'inventory-movement-canvas';
            chartContainer.appendChild(canvas);
            
            const labels = data.periods || [];
            const chartData = {
                labels: labels,
                datasets: [
                    {
                        label: 'Entradas',
                        data: data.in || [],
                        borderColor: '#1cc88a',
                        backgroundColor: 'rgba(28, 200, 138, 0.2)',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Saídas',
                        data: data.out || [],
                        borderColor: '#e74a3b',
                        backgroundColor: 'rgba(231, 74, 59, 0.2)',
                        tension: 0.4,
                        fill: true
                    }
                ]
            };
            
            this.charts.inventoryMovement = ChartUtils.createLineChart('inventory-movement-canvas', chartData);
        });
    },
    
    /**
     * Cria gráfico dos componentes mais utilizados
     */
    createTopComponentsChart: function() {
        const chartContainer = document.getElementById('top-components-chart');
        if (!chartContainer) return;
        
        // Dados obtidos via AJAX
        this.fetchData('/api/top-components', (data) => {
            const canvas = document.createElement('canvas');
            canvas.id = 'top-components-canvas';
            chartContainer.appendChild(canvas);
            
            const chartData = {
                labels: data.map(item => item.name) || [],
                datasets: [{
                    label: 'Quantidade Utilizada',
                    data: data.map(item => item.quantity) || [],
                    backgroundColor: ChartUtils.generateColors(data.length),
                    borderWidth: 1
                }]
            };
            
            this.charts.topComponents = ChartUtils.createBarChart('top-components-canvas', chartData);
        });
    },
    
    /**
     * Cria gráfico de desempenho de fornecedores
     */
    createSupplierPerformanceChart: function() {
        const chartContainer = document.getElementById('supplier-performance-chart');
        if (!chartContainer) return;
        
        // Dados obtidos via AJAX
        this.fetchData('/api/supplier-performance', (data) => {
            const canvas = document.createElement('canvas');
            canvas.id = 'supplier-performance-canvas';
            chartContainer.appendChild(canvas);
            
            const chartData = {
                labels: data.map(item => item.name) || [],
                datasets: [{
                    label: 'Pontuação',
                    data: data.map(item => item.score) || [],
                    backgroundColor: data.map(item => item.score >= 85 ? '#1cc88a' : '#e74a3b'),
                    borderWidth: 1
                }]
            };
            
            this.charts.supplierPerformance = ChartUtils.createBarChart('supplier-performance-canvas', chartData, {
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Pontuação (%)'
                        }
                    }
                }
            });
        });
    },
    
    /**
     * Busca dados para os gráficos via AJAX
     * @param {string} url - URL da API
     * @param {Function} callback - Função a ser chamada com os dados
     */
    fetchData: function(url, callback) {
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao buscar dados');
                }
                return response.json();
            })
            .then(data => {
                callback(data);
            })
            .catch(error => {
                console.error('Erro ao carregar dados do gráfico:', error);
                // Mostrar mensagem de erro no container do gráfico
                const errorElement = document.createElement('div');
                errorElement.className = 'alert alert-danger';
                errorElement.textContent = 'Não foi possível carregar os dados do gráfico.';
                
                // Adicionar botão para tentar novamente
                const retryButton = document.createElement('button');
                retryButton.className = 'btn btn-sm btn-outline-danger mt-2';
                retryButton.textContent = 'Tentar Novamente';
                retryButton.onclick = () => {
                    errorElement.remove();
                    this.fetchData(url, callback);
                };
                
                errorElement.appendChild(retryButton);
                const chartContainer = document.querySelector(url.includes('status') ? '#inventory-status-chart' :
                                                  url.includes('movement') ? '#inventory-movement-chart' :
                                                  url.includes('components') ? '#top-components-chart' :
                                                  '#supplier-performance-chart');
                
                if (chartContainer) {
                    chartContainer.innerHTML = '';
                    chartContainer.appendChild(errorElement);
                }
            });
    },
    
    /**
     * Atualiza os dados dos gráficos
     */
    refreshCharts: function() {
        // Destruir gráficos existentes
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        
        // Limpar os containers
        ['inventory-status-chart', 'inventory-movement-chart', 
         'top-components-chart', 'supplier-performance-chart'].forEach(id => {
            const container = document.getElementById(id);
            if (container) container.innerHTML = '';
        });
        
        // Recriar os gráficos
        this.createDashboardCharts();
    }
};

// Inicializar gráficos quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Verificar se estamos na página do dashboard
    if (document.getElementById('dashboard-charts-container')) {
        EstoqueDashboard.initialize();
        
        // Adicionar botão de atualização
        const refreshButton = document.getElementById('refresh-charts');
        if (refreshButton) {
            refreshButton.addEventListener('click', function() {
                EstoqueDashboard.refreshCharts();
            });
        }
    }
}); 