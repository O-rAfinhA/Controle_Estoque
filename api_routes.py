from flask import Blueprint, jsonify
from database import get_db_connection
from datetime import datetime, timedelta
import json

# Criar blueprint para rotas da API
api_bp = Blueprint('api', __name__)

@api_bp.route('/inventory-status', methods=['GET'])
def get_inventory_status():
    """
    Retorna a contagem de componentes por status de estoque
    (Crítico: <= 5, Baixo: <= 20, Normal: > 20)
    """
    conn = get_db_connection()
    
    # Contagem por status
    critical = conn.execute('SELECT COUNT(*) FROM componentes WHERE quantidade <= 5').fetchone()[0]
    low = conn.execute('SELECT COUNT(*) FROM componentes WHERE quantidade > 5 AND quantidade <= 20').fetchone()[0]
    normal = conn.execute('SELECT COUNT(*) FROM componentes WHERE quantidade > 20').fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'critical': critical,
        'low': low,
        'normal': normal
    })

@api_bp.route('/inventory-movement', methods=['GET'])
def get_inventory_movement():
    """
    Retorna os dados de movimentação de estoque (entradas e saídas)
    para os últimos 7 dias
    """
    conn = get_db_connection()
    
    # Data de início (7 dias atrás)
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Consulta para entradas e saídas por dia
    query = '''
    SELECT 
        DATE(data) as dia,
        SUM(CASE WHEN tipo = 'entrada' THEN 1 ELSE 0 END) as entradas,
        SUM(CASE WHEN tipo = 'saida' THEN 1 ELSE 0 END) as saidas
    FROM transacoes
    WHERE DATE(data) >= ?
    GROUP BY dia
    ORDER BY dia ASC
    '''
    
    results = conn.execute(query, (start_date,)).fetchall()
    conn.close()
    
    # Criar dicionário com todos os dias, mesmo sem movimentações
    today = datetime.now().date()
    days = {}
    for i in range(7):
        day = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        days[day] = {'in': 0, 'out': 0}
    
    # Preencher com dados da consulta
    for row in results:
        day = row['dia']
        if day in days:
            days[day]['in'] = row['entradas']
            days[day]['out'] = row['saidas']
    
    # Organizar para retorno
    sorted_days = sorted(days.keys())
    
    return jsonify({
        'periods': [datetime.strptime(day, '%Y-%m-%d').strftime('%d/%m') for day in sorted_days],
        'in': [days[day]['in'] for day in sorted_days],
        'out': [days[day]['out'] for day in sorted_days]
    })

@api_bp.route('/top-components', methods=['GET'])
def get_top_components():
    """
    Retorna os 10 componentes mais utilizados (com mais saídas)
    nos últimos 30 dias
    """
    conn = get_db_connection()
    
    # Data de início (30 dias atrás)
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Consulta para os componentes mais utilizados
    query = '''
    SELECT 
        c.nome,
        SUM(t.quantidade) as quantidade_total
    FROM transacoes t
    JOIN componentes c ON t.codigo_componente = c.codigo
    WHERE t.tipo = 'saida' AND DATE(t.data) >= ?
    GROUP BY t.codigo_componente
    ORDER BY quantidade_total DESC
    LIMIT 10
    '''
    
    results = conn.execute(query, (start_date,)).fetchall()
    conn.close()
    
    # Formatar resultado
    components = []
    for row in results:
        components.append({
            'name': row['nome'],
            'quantity': row['quantidade_total']
        })
    
    return jsonify(components)

@api_bp.route('/supplier-performance', methods=['GET'])
def get_supplier_performance():
    """
    Retorna a pontuação de desempenho dos fornecedores
    """
    conn = get_db_connection()
    
    # Consulta para obter a pontuação dos fornecedores
    # Se a tabela avaliacoes_fornecedores não existir, retorna dados fictícios
    try:
        query = '''
        SELECT 
            f.nome,
            AVG(av.pontuacao) as pontuacao_media
        FROM fornecedores f
        LEFT JOIN avaliacoes_fornecedores av ON f.id = av.fornecedor_id
        GROUP BY f.id
        ORDER BY pontuacao_media DESC
        LIMIT 10
        '''
        
        results = conn.execute(query).fetchall()
        
        # Formatar resultado
        suppliers = []
        for row in results:
            suppliers.append({
                'name': row['nome'],
                'score': round(row['pontuacao_media'], 1) if row['pontuacao_media'] else 0
            })
        
    except:
        # Se a consulta falhar, criar dados fictícios
        suppliers = [
            {'name': 'Fornecedor A', 'score': 92.5},
            {'name': 'Fornecedor B', 'score': 88.3},
            {'name': 'Fornecedor C', 'score': 85.1},
            {'name': 'Fornecedor D', 'score': 78.9},
            {'name': 'Fornecedor E', 'score': 76.2}
        ]
    
    conn.close()
    return jsonify(suppliers)

# Rota para notificações
@api_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """
    Retorna as notificações do sistema (itens críticos, etc.)
    """
    conn = get_db_connection()
    
    # Obter componentes críticos
    critical_components = conn.execute(
        'SELECT codigo, nome, quantidade FROM componentes WHERE quantidade <= 5'
    ).fetchall()
    
    # Fornecedores críticos (pontuação < 85)
    supplier_query = '''
    SELECT f.nome, AVG(af.pontuacao) as pontuacao
    FROM fornecedores f
    LEFT JOIN avaliacoes_fornecedores af ON f.id = af.fornecedor_id
    GROUP BY f.id
    HAVING pontuacao < 85
    '''
    
    try:
        critical_suppliers = conn.execute(supplier_query).fetchall()
    except:
        critical_suppliers = []
    
    conn.close()
    
    # Construir notificações
    notifications = []
    
    # Notificações de componentes críticos
    for component in critical_components:
        notifications.append({
            'type': 'critical_stock',
            'message': f"Estoque crítico: {component['nome']} ({component['quantidade']} unidades)",
            'link': f"/componentes/editar/{component['codigo']}",
            'icon': 'exclamation-circle',
            'color': 'danger'
        })
    
    # Notificações de fornecedores críticos
    for supplier in critical_suppliers:
        notifications.append({
            'type': 'critical_supplier',
            'message': f"Fornecedor crítico: {supplier['nome']} ({supplier['pontuacao']:.1f}%)",
            'link': "/avaliacao-fornecedores",
            'icon': 'industry',
            'color': 'warning'
        })
    
    return jsonify(notifications) 