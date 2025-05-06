import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import io
import base64
from datetime import datetime, timedelta
from database import get_db_connection
from fornecedores_utils import (
    calcular_avaliacoes, calcular_ranking_fornecedores, 
    format_currency, format_status
)

matplotlib.use('Agg')  # Use non-interactive backend for server environments

def get_estoque_stats():
    """Obtém estatísticas sobre o estoque de componentes"""
    conn = get_db_connection()
    
    try:
        # Total de componentes
        total = conn.execute('SELECT COUNT(*) as count FROM componentes').fetchone()['count']
        
        # Componentes por nível de estoque
        critico = conn.execute('SELECT COUNT(*) as count FROM componentes WHERE quantidade < 100').fetchone()['count']
        baixo = conn.execute('SELECT COUNT(*) as count FROM componentes WHERE quantidade >= 100 AND quantidade < 300').fetchone()['count']
        normal = conn.execute('SELECT COUNT(*) as count FROM componentes WHERE quantidade >= 300').fetchone()['count']
        
        # Componentes críticos (todos)
        componentes_criticos = conn.execute(
            'SELECT codigo, nome, quantidade FROM componentes WHERE quantidade < 100 ORDER BY quantidade ASC'
        ).fetchall()
        
        # Componentes com estoque baixo (todos)
        componentes_baixo = conn.execute(
            'SELECT codigo, nome, quantidade FROM componentes WHERE quantidade >= 100 AND quantidade < 300 ORDER BY quantidade ASC'
        ).fetchall()
        
        # Componentes com estoque normal (todos)
        componentes_normal = conn.execute(
            'SELECT codigo, nome, quantidade FROM componentes WHERE quantidade >= 300 ORDER BY quantidade DESC'
        ).fetchall()
        
        # Valor total do estoque (definido como 0, já que não há coluna valor na tabela)
        valor_total = 0
        
        conn.close()
        
        return {
            'total': total,
            'critico': critico,
            'baixo': baixo,
            'normal': normal,
            'componentes_criticos': [dict(c) for c in componentes_criticos],
            'componentes_baixo': [dict(c) for c in componentes_baixo],
            'componentes_normal': [dict(c) for c in componentes_normal],
            'valor_total': valor_total
        }
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao obter estatísticas de estoque: {str(e)}")

def get_fornecedores_stats():
    """Obtém estatísticas sobre os fornecedores"""
    try:
        # Calcular avaliações
        avaliacoes = calcular_avaliacoes()
        
        if not avaliacoes:
            return {
                'total': 0,
                'criticos': 0,
                'bons': 0,
                'media_score': 0,
                'top_5': [],
                'bottom_5': []
            }
        
        # Total de fornecedores
        total = len(avaliacoes)
        
        # Fornecedores críticos e bons
        criticos = len([a for a in avaliacoes if a['scoreFinal'] < 85])
        bons = total - criticos
        
        # Média de score
        media_score = sum(a['scoreFinal'] for a in avaliacoes) / total if total > 0 else 0
        
        # Top 5 fornecedores
        top_5 = sorted(avaliacoes, key=lambda x: x['scoreFinal'], reverse=True)[:5]
        
        # Bottom 5 fornecedores
        bottom_5 = sorted(avaliacoes, key=lambda x: x['scoreFinal'])[:5]
        
        return {
            'total': total,
            'criticos': criticos,
            'bons': bons,
            'media_score': round(media_score, 1),
            'top_5': top_5,
            'bottom_5': bottom_5
        }
    
    except Exception as e:
        raise Exception(f"Erro ao obter estatísticas de fornecedores: {str(e)}")

def get_producao_stats():
    """Obtém estatísticas sobre a produção de produtos"""
    conn = get_db_connection()
    
    try:
        # Total de produtos cadastrados
        total_produtos = conn.execute('SELECT COUNT(*) as count FROM produtos').fetchone()['count']
        
        # Total de produções registradas
        total_producoes = conn.execute('SELECT COUNT(*) as count FROM producoes').fetchone()['count']
        
        # Produções nos últimos 30 dias
        data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        producoes_recentes = conn.execute(f"SELECT COUNT(*) as count FROM producoes WHERE data >= '{data_limite}'").fetchone()['count']
        
        # Produtos mais produzidos
        produtos_mais_produzidos = conn.execute('''
            SELECT p.id, p.nome, COUNT(pr.id) as total
            FROM produtos p
            LEFT JOIN producoes pr ON p.id = pr.produto_id
            GROUP BY p.id
            HAVING total > 0
            ORDER BY total DESC
            LIMIT 10
        ''').fetchall()
        
        # Status de produção
        status_producao = conn.execute('''
            SELECT status, COUNT(*) as total
            FROM producoes
            GROUP BY status
            ORDER BY total DESC
        ''').fetchall()
        
        conn.close()
        
        return {
            'total_produtos': total_produtos,
            'total_producoes': total_producoes,
            'producoes_recentes': producoes_recentes,
            'produtos_mais_produzidos': [dict(p) for p in produtos_mais_produzidos],
            'status_producao': [dict(s) for s in status_producao]
        }
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao obter estatísticas de produção: {str(e)}")

def get_transacoes_recentes(dias=7, limite=10):
    """Obtém as transações recentes de componentes"""
    conn = get_db_connection()
    
    try:
        # Data limite
        data_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        # Buscar transações recentes
        transacoes = conn.execute(f'''
            SELECT t.id, t.tipo, t.quantidade, t.data, t.codigo_componente,
                   c.nome as componente,
                   u.nome as usuario, u.id as usuario_id
            FROM transacoes t
            JOIN componentes c ON t.codigo_componente = c.codigo
            LEFT JOIN usuarios u ON t.usuario_id = u.id
            WHERE t.data >= '{data_limite}'
            ORDER BY t.data DESC
            LIMIT {limite}
        ''').fetchall()
        
        # Converter a lista de Row para lista de dicionários
        transacoes_list = []
        for t in transacoes:
            # Converter Row para dict
            t_dict = dict(t)
            
            # Formatar a data se necessário
            if isinstance(t_dict['data'], str):
                try:
                    # Tentativa de formatar a data
                    data_obj = datetime.strptime(t_dict['data'], '%Y-%m-%d %H:%M:%S')
                    t_dict['data_formatada'] = data_obj.strftime('%d/%m/%Y %H:%M')
                except:
                    t_dict['data_formatada'] = t_dict['data']
            else:
                t_dict['data_formatada'] = t_dict['data']
            
            transacoes_list.append(t_dict)
        
        conn.close()
        return transacoes_list
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao obter transações recentes: {str(e)}")

def gerar_grafico_estoque():
    """Gera um gráfico de distribuição de estoque e retorna como base64"""
    try:
        stats = get_estoque_stats()
        
        # Criar dados para o gráfico
        categorias = ['Crítico', 'Baixo', 'Normal']
        valores = [stats['critico'], stats['baixo'], stats['normal']]
        cores = ['#dc3545', '#ffc107', '#28a745']
        
        # Criar figura
        plt.figure(figsize=(8, 5))
        plt.bar(categorias, valores, color=cores)
        plt.title('Distribuição de Estoque por Nível')
        plt.ylabel('Quantidade de Componentes')
        plt.grid(axis='y', alpha=0.3)
        
        # Adicionar valores nas barras
        for i, v in enumerate(valores):
            plt.text(i, v + 0.5, str(v), ha='center')
        
        # Salvar em buffer
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Converter para base64
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return img_str
    
    except Exception as e:
        raise Exception(f"Erro ao gerar gráfico de estoque: {str(e)}")

def consultar_componente(codigo_ou_nome):
    """Consulta um componente específico por código ou nome"""
    conn = get_db_connection()
    
    try:
        # Tentar buscar pelo código exato
        componente = conn.execute(
            'SELECT * FROM componentes WHERE codigo = ?', 
            (codigo_ou_nome,)
        ).fetchone()
        
        # Se não encontrar, buscar pelo nome (busca parcial case-insensitive)
        if not componente:
            componente = conn.execute(
                'SELECT * FROM componentes WHERE UPPER(nome) LIKE UPPER(?)', 
                (f'%{codigo_ou_nome}%',)
            ).fetchone()
        
        if not componente:
            conn.close()
            return None
        
        # Converter para dicionário
        componente_dict = dict(componente)
        
        # Buscar produtos que usam este componente
        produtos = conn.execute('''
            SELECT p.id, p.nome, cp.quantidade
            FROM componentes_produto cp
            JOIN produtos p ON cp.produto_id = p.id
            WHERE cp.codigo_componente = ?
        ''', (componente_dict['codigo'],)).fetchall()
        
        # Buscar histórico de transações (últimas 10)
        transacoes = conn.execute('''
            SELECT t.tipo, t.quantidade, t.data, 
                   u.nome as usuario, u.id as usuario_id,
                   (SELECT COUNT(*) FROM transacoes WHERE codigo_componente = t.codigo_componente) as total_transacoes
            FROM transacoes t
            LEFT JOIN usuarios u ON t.usuario_id = u.id
            WHERE t.codigo_componente = ?
            ORDER BY t.data DESC
            LIMIT 10
        ''', (componente_dict['codigo'],)).fetchall()
        
        # Obter informações estatísticas
        estatisticas = conn.execute('''
            SELECT 
                SUM(CASE WHEN tipo = 'entrada' THEN quantidade ELSE 0 END) as total_entradas,
                SUM(CASE WHEN tipo = 'saida' THEN quantidade ELSE 0 END) as total_saidas,
                COUNT(DISTINCT usuario_id) as total_usuarios,
                MAX(data) as ultima_transacao
            FROM transacoes
            WHERE codigo_componente = ?
        ''', (componente_dict['codigo'],)).fetchone()
        
        conn.close()
        
        # Processar transações
        transacoes_formatadas = []
        for t in transacoes:
            t_dict = dict(t)
            # Formatar data se for string
            if isinstance(t_dict['data'], str):
                try:
                    data_obj = datetime.strptime(t_dict['data'], '%Y-%m-%d %H:%M:%S')
                    t_dict['data_formatada'] = data_obj.strftime('%d/%m/%Y %H:%M')
                except:
                    t_dict['data_formatada'] = t_dict['data']
            else:
                t_dict['data_formatada'] = t_dict['data']
                
            # Garantir que o usuário tenha um valor
            if not t_dict['usuario']:
                t_dict['usuario'] = 'Sistema'
                
            transacoes_formatadas.append(t_dict)
        
        # Adicionar informações extras
        componente_dict['produtos'] = [dict(p) for p in produtos]
        componente_dict['transacoes'] = transacoes_formatadas
        componente_dict['status'] = 'crítico' if componente_dict['quantidade'] < 100 else ('baixo' if componente_dict['quantidade'] < 300 else 'normal')
        
        # Adicionar estatísticas
        if estatisticas:
            estatisticas_dict = dict(estatisticas)
            componente_dict['total_entradas'] = estatisticas_dict['total_entradas'] or 0
            componente_dict['total_saidas'] = estatisticas_dict['total_saidas'] or 0
            componente_dict['total_usuarios'] = estatisticas_dict['total_usuarios'] or 0
            componente_dict['ultima_transacao'] = estatisticas_dict['ultima_transacao']
            componente_dict['total_transacoes'] = transacoes[0]['total_transacoes'] if transacoes else 0
        
        return componente_dict
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao consultar componente: {str(e)}")

def consultar_produto(nome_ou_id):
    """Consulta um produto específico por nome ou ID"""
    conn = get_db_connection()
    
    try:
        # Verificar se é um ID numérico
        is_id = str(nome_ou_id).isdigit()
        
        # Tentar buscar pelo ID
        if is_id:
            produto = conn.execute(
                'SELECT * FROM produtos WHERE id = ?', 
                (nome_ou_id,)
            ).fetchone()
        else:
            # Buscar pelo nome (busca parcial case-insensitive)
            produto = conn.execute(
                'SELECT * FROM produtos WHERE UPPER(nome) LIKE UPPER(?)', 
                (f'%{nome_ou_id}%',)
            ).fetchone()
        
        if not produto:
            conn.close()
            return None
        
        # Converter para dicionário
        produto_dict = dict(produto)
        
        # Buscar componentes do produto
        componentes = conn.execute('''
            SELECT cp.quantidade, c.codigo, c.nome, c.quantidade as estoque
            FROM componentes_produto cp
            JOIN componentes c ON cp.codigo_componente = c.codigo
            WHERE cp.produto_id = ?
        ''', (produto_dict['id'],)).fetchall()
        
        # Buscar produções do produto
        producoes = conn.execute('''
            SELECT id, quantidade, data, 
                   (SELECT nome FROM usuarios WHERE id = p.usuario_id) as usuario
            FROM producoes p
            WHERE produto_id = ?
            ORDER BY data DESC
            LIMIT 5
        ''', (produto_dict['id'],)).fetchall()
        
        conn.close()
        
        # Adicionar informações extras
        produto_dict['componentes'] = [dict(c) for c in componentes]
        produto_dict['producoes'] = [dict(p) for p in producoes]
        
        # Verificar disponibilidade para produção
        disponivel = True
        for comp in produto_dict['componentes']:
            if comp['estoque'] < comp['quantidade']:
                disponivel = False
                break
        
        produto_dict['disponivel_producao'] = disponivel
        
        return produto_dict
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao consultar produto: {str(e)}")

def consultar_fornecedor(nome_ou_id):
    """Consulta um fornecedor específico por nome ou ID"""
    conn = get_db_connection()
    
    try:
        # Verificar se é um ID numérico
        is_id = str(nome_ou_id).isdigit()
        
        # Tentar buscar pelo ID
        if is_id:
            fornecedor = conn.execute(
                'SELECT * FROM fornecedores WHERE id = ?', 
                (nome_ou_id,)
            ).fetchone()
        else:
            # Buscar pelo nome (busca parcial case-insensitive)
            fornecedor = conn.execute(
                'SELECT * FROM fornecedores WHERE UPPER(nome) LIKE UPPER(?)', 
                (f'%{nome_ou_id}%',)
            ).fetchone()
        
        if not fornecedor:
            conn.close()
            return None
        
        # Converter para dicionário
        fornecedor_dict = dict(fornecedor)
        
        # Buscar recebimentos do fornecedor (removendo a coluna valor que não existe)
        recebimentos = conn.execute('''
            SELECT id, data_recebimento, data_prevista, dias_atraso, 
                   pc, nf, quantidade, status
            FROM recebimentos
            WHERE fornecedor_id = ?
            ORDER BY data_recebimento DESC
            LIMIT 10
        ''', (fornecedor_dict['id'],)).fetchall()
        
        # Formatar recebimentos
        recebimentos_formatados = []
        for r in recebimentos:
            r_dict = dict(r)
            r_dict['status_formatado'] = format_status(r_dict['status'])
            # Não formatamos mais o valor pois a coluna não existe
            recebimentos_formatados.append(r_dict)
        
        # Buscar avaliação do fornecedor
        avaliacoes = calcular_avaliacoes()
        avaliacao = next((a for a in avaliacoes if a['id'] == fornecedor_dict['id']), None)
        
        conn.close()
        
        # Adicionar informações extras
        fornecedor_dict['recebimentos'] = recebimentos_formatados
        fornecedor_dict['avaliacao'] = avaliacao
        
        return fornecedor_dict
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao consultar fornecedor: {str(e)}")

def get_system_context_data():
    """Coleta informações completas do sistema para fornecer contexto ao modelo de IA"""
    try:
        conn = get_db_connection()
        
        # Informações de estoque
        estoque_stats = get_estoque_stats()
        
        # Informações de fornecedores
        fornecedores_stats = get_fornecedores_stats()
        
        # Informações de produção
        producao_stats = get_producao_stats()
        
        # Transações recentes
        transacoes = get_transacoes_recentes(dias=7, limite=5)
        
        # Clientes (extraídos dos produtos)
        clientes = conn.execute('SELECT DISTINCT descricao as cliente FROM produtos WHERE descricao IS NOT NULL AND descricao != "" ORDER BY descricao').fetchall()
        clientes_lista = [c['cliente'] for c in clientes]
        
        # Produtos mais recentes
        produtos_recentes = conn.execute('''
            SELECT p.id, p.nome, p.descricao as cliente, 
                   (SELECT COUNT(*) FROM producoes WHERE produto_id = p.id) as total_producoes
            FROM produtos p
            ORDER BY p.id DESC
            LIMIT 10
        ''').fetchall()
        
        # Produções recentes
        producoes_recentes = conn.execute('''
            SELECT p.id, pr.nome as produto, pr.descricao as cliente, p.quantidade, 
                   p.data, p.status, u.nome as usuario
            FROM producoes p
            JOIN produtos pr ON p.produto_id = pr.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            ORDER BY p.data DESC
            LIMIT 10
        ''').fetchall()
        
        conn.close()
        
        return {
            'estoque': estoque_stats,
            'fornecedores': fornecedores_stats,
            'producao': producao_stats,
            'transacoes': transacoes,
            'clientes': clientes_lista,
            'produtos_recentes': [dict(p) for p in produtos_recentes],
            'producoes_recentes': [dict(p) for p in producoes_recentes],
            'data_atualizacao': datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        }
    
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        raise Exception(f"Erro ao coletar dados do sistema: {str(e)}")

def format_system_context(context_data):
    """Formata os dados do contexto do sistema para envio à API OpenAI"""
    try:
        # Estoque
        estoque = context_data['estoque']
        
        # Fornecedores
        fornecedores = context_data['fornecedores']
        
        # Produção
        producao = context_data['producao']
        
        # Clientes
        clientes = context_data['clientes']
        
        # Produtos recentes
        produtos_recentes = context_data['produtos_recentes']
        
        # Produções recentes
        producoes_recentes = context_data['producoes_recentes']
        
        # Transações recentes
        transacoes = context_data['transacoes']
        
        # Data de atualização
        data_atualizacao = context_data['data_atualizacao']
        
        # Formatar texto do sistema
        system_context = f"""
Você é um assistente de IA simpático e descontraído, seu nome é Jarvis integrado ao sistema de gestão de estoque. Responda às perguntas com base
nas informações mais recentes do sistema, usando um tom informal, amigável e às vezes com gírias, mas ainda sendo profissional.
Dados atualizados em: {data_atualizacao}.

DADOS ATUAIS DO SISTEMA:

ESTOQUE:
- Total de componentes: {estoque['total']}
- Componentes em estado crítico (<100 unidades): {estoque['critico']}
- Componentes em estado baixo (100-299 unidades): {estoque['baixo']}
- Componentes em estado normal (≥300 unidades): {estoque['normal']}

Componentes com estoque crítico:
"""
        
        # Adicionar componentes críticos
        for comp in estoque['componentes_criticos']:
            system_context += f"- {comp['nome']} (Código: {comp['codigo']}): {comp['quantidade']} unidades\n"
        
        # Adicionar componentes com estoque baixo
        system_context += f"\nComponentes com estoque baixo:\n"
        for comp in estoque['componentes_baixo']:
            system_context += f"- {comp['nome']} (Código: {comp['codigo']}): {comp['quantidade']} unidades\n"
        
        # Adicionar componentes com estoque normal
        system_context += f"\nComponentes com estoque normal:\n"
        for comp in estoque['componentes_normal']:
            system_context += f"- {comp['nome']} (Código: {comp['codigo']}): {comp['quantidade']} unidades\n"
        
        system_context += f"""
TRANSAÇÕES RECENTES:
"""
        # Adicionar transações recentes com detalhes completos
        if transacoes:
            for t in transacoes:
                tipo = "ENTRADA" if t['tipo'] == "entrada" else "SAÍDA"
                usuario = t.get('usuario', 'Sistema')
                usuario_id = f" (ID: {t['usuario_id']})" if t.get('usuario_id') else ""
                data_formatada = t.get('data_formatada', t['data'])
                system_context += f"- {tipo}: {t['componente']} (Cód: {t['codigo_componente']}) - Qtd: {t['quantidade']} unidades\n"
                system_context += f"  Data/Hora: {data_formatada} - Responsável: {usuario}{usuario_id}\n"
        else:
            system_context += "- Nenhuma transação recente registrada.\n"
        
        system_context += f"""
FORNECEDORES:
- Total de fornecedores: {fornecedores['total']}
- Fornecedores com bom desempenho (≥85%): {fornecedores['bons']}
- Fornecedores críticos (<85%): {fornecedores['criticos']}
- Média geral de desempenho: {fornecedores['media_score']}%

Melhores fornecedores:
"""
        
        # Adicionar melhores fornecedores
        for i, f in enumerate(fornecedores['top_5'], 1):
            system_context += f"- {i}. {f['nome']}: {f['scoreFinal']}% (Qualidade: {f['percentualAprovacao']}%, Pontualidade: {f['percentualPontualidade']}%)\n"
        
        system_context += f"""
PRODUÇÃO:
- Total de produtos cadastrados: {producao['total_produtos']}
- Total de produções registradas: {producao['total_producoes']}
- Produções nos últimos 30 dias: {producao['producoes_recentes']}

Produtos mais produzidos:
"""
        
        # Adicionar produtos mais produzidos
        for p in producao['produtos_mais_produzidos']:
            system_context += f"- {p['nome']}: {p['total']} produções\n"
        
        # Adicionar informações sobre clientes
        system_context += f"\nCLIENTES:\nAtualmente temos {len(clientes)} clientes cadastrados, incluindo:\n"
        for cliente in clientes:
            system_context += f"- {cliente}\n"
        
        # Adicionar informações sobre produtos recentes
        system_context += f"\nPRODUTOS MAIS RECENTES:\n"
        for produto in produtos_recentes:
            cliente_info = f" (Cliente: {produto['cliente']})" if produto['cliente'] else ""
            system_context += f"- {produto['nome']}{cliente_info} - {produto['total_producoes']} produções\n"
        
        # Adicionar informações sobre produções recentes com todos os detalhes
        system_context += f"\nPRODUÇÕES MAIS RECENTES:\n"
        for producao in producoes_recentes:
            data = producao.get('data', '')
            if isinstance(data, str) and ' ' in data:
                data_formatada = data  # Manter data e hora completas
            else:
                data_formatada = data
            responsavel = producao.get('usuario', 'Sistema')
            cliente = f" - Cliente: {producao['cliente']}" if producao.get('cliente') else ""
            status = f" - Status: {producao['status']}" if producao.get('status') else ""
            system_context += f"- Produto: {producao['produto']} - Qtd: {producao['quantidade']}\n"
            system_context += f"  Data/Hora: {data_formatada} - Responsável: {responsavel}{cliente}{status}\n"
        
        system_context += """
INSTRUÇÕES DE PERSONALIDADE E ESTILO:
- Responda sempre em português do Brasil, com um tom amigável e descontraído.
- Use gírias leves e expressões coloquiais quando apropriado ("E aí", "Beleza", "Opa", "Tranquilo", etc.).
- Evite formalismos excessivos, seja mais conversacional e próximo ao usuário.
- Demonstre entusiasmo quando apropriado.
- Mantenha suas respostas claras e úteis, mesmo sendo casual.
- Trate o usuário como um colega de trabalho com quem você já tem certa familiaridade.
- IMPORTANTE: Quando o usuário perguntar sobre transações ou produções, sempre inclua informações sobre data/hora e o usuário responsável.
- Seja detalhista ao informar sobre transações, fornecendo todas as informações disponíveis.
- IMPORTANTE: Quando o usuário perguntar sobre componentes de um produto, liste TODOS os componentes necessários para produzir o produto, incluindo quantidades e informações sobre disponibilidade em estoque.
- Quando o usuário pedir informações sobre produtos, sempre inclua os componentes necessários para sua produção.

Lembre-se: o objetivo do sistema é gerenciar o estoque de componentes e auxiliar na produção de produtos.
"""
        
        return system_context
    
    except Exception as e:
        raise Exception(f"Erro ao formatar contexto do sistema: {str(e)}")

# Funções para consultas mais avançadas
def analisar_tendencias_estoque(dias=30):
    """Analisa tendências de estoque nos últimos dias"""
    conn = get_db_connection()
    
    try:
        # Data limite
        data_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        # Buscar todas as transações no período
        transacoes = conn.execute(f'''
            SELECT codigo_componente, tipo, quantidade, date(data) as data
            FROM transacoes
            WHERE data >= '{data_limite}'
            ORDER BY data ASC
        ''').fetchall()
        
        if not transacoes:
            conn.close()
            return {
                'status': 'empty',
                'message': f'Não há transações nos últimos {dias} dias.'
            }
        
        # Converter para DataFrame
        df = pd.DataFrame([dict(t) for t in transacoes])
        
        # Agrupar por data e tipo
        entradas_diarias = df[df['tipo'] == 'entrada'].groupby('data')['quantidade'].sum()
        saidas_diarias = df[df['tipo'] == 'saida'].groupby('data')['quantidade'].sum()
        
        # Calcular saldo líquido
        datas = sorted(list(set(entradas_diarias.index) | set(saidas_diarias.index)))
        saldo_liquido = []
        
        for data in datas:
            entrada = entradas_diarias.get(data, 0)
            saida = saidas_diarias.get(data, 0)
            saldo_liquido.append({
                'data': data,
                'entrada': int(entrada),
                'saida': int(saida),
                'saldo': int(entrada - saida)
            })
        
        # Calcular métricas
        total_entradas = int(df[df['tipo'] == 'entrada']['quantidade'].sum())
        total_saidas = int(df[df['tipo'] == 'saida']['quantidade'].sum())
        saldo_geral = total_entradas - total_saidas
        
        # Componentes mais movimentados
        movimentacao_por_componente = df.groupby('codigo_componente')['quantidade'].sum().sort_values(ascending=False)
        
        # Buscar nomes dos componentes
        top_componentes = []
        for codigo in movimentacao_por_componente.index[:5]:
            componente = conn.execute('SELECT nome FROM componentes WHERE codigo = ?', (codigo,)).fetchone()
            if componente:
                nome = componente['nome']
                entrada = int(df[(df['codigo_componente'] == codigo) & (df['tipo'] == 'entrada')]['quantidade'].sum())
                saida = int(df[(df['codigo_componente'] == codigo) & (df['tipo'] == 'saida')]['quantidade'].sum())
                top_componentes.append({
                    'codigo': codigo,
                    'nome': nome,
                    'entrada': entrada,
                    'saida': saida,
                    'total': entrada + saida
                })
        
        conn.close()
        
        return {
            'status': 'success',
            'periodo': {
                'inicio': datas[0],
                'fim': datas[-1],
                'dias': len(datas)
            },
            'totais': {
                'entradas': total_entradas,
                'saidas': total_saidas,
                'saldo': saldo_geral
            },
            'diario': saldo_liquido,
            'top_componentes': top_componentes
        }
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao analisar tendências de estoque: {str(e)}")

def analisar_desempenho_fornecedores(dias=90):
    """Analisa o desempenho dos fornecedores nos últimos dias"""
    conn = get_db_connection()
    
    try:
        # Data limite
        data_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        # Buscar recebimentos no período
        recebimentos = conn.execute(f'''
            SELECT r.*, f.nome as fornecedor_nome
            FROM recebimentos r
            JOIN fornecedores f ON r.fornecedor_id = f.id
            WHERE r.data_recebimento >= '{data_limite}'
            ORDER BY r.data_recebimento ASC
        ''').fetchall()
        
        if not recebimentos:
            conn.close()
            return {
                'status': 'empty',
                'message': f'Não há recebimentos nos últimos {dias} dias.'
            }
        
        # Converter para lista de dicionários
        recebimentos_lista = [dict(r) for r in recebimentos]
        
        # Agrupar por fornecedor
        fornecedores = {}
        for r in recebimentos_lista:
            fornecedor_id = r['fornecedor_id']
            if fornecedor_id not in fornecedores:
                fornecedores[fornecedor_id] = {
                    'id': fornecedor_id,
                    'nome': r['fornecedor_nome'],
                    'recebimentos': [],
                    'total': 0,
                    'no_prazo': 0,
                    'aprovado': 0,
                    'condicional': 0,
                    'rejeitado': 0
                }
            
            fornecedores[fornecedor_id]['recebimentos'].append(r)
            fornecedores[fornecedor_id]['total'] += 1
            
            # Contabilizar pontualidade
            if r['dias_atraso'] <= 0:
                fornecedores[fornecedor_id]['no_prazo'] += 1
            
            # Contabilizar qualidade
            if r['status'] == 'aprovado':
                fornecedores[fornecedor_id]['aprovado'] += 1
            elif r['status'] == 'ac':
                fornecedores[fornecedor_id]['condicional'] += 1
            elif r['status'] == 'rejeitado':
                fornecedores[fornecedor_id]['rejeitado'] += 1
        
        # Calcular métricas para cada fornecedor
        for f_id, f in fornecedores.items():
            f['pontualidade'] = round((f['no_prazo'] / f['total']) * 100, 1) if f['total'] > 0 else 0
            f['qualidade'] = round((f['aprovado'] / f['total']) * 100, 1) if f['total'] > 0 else 0
            f['score'] = round((f['pontualidade'] * 0.4) + (f['qualidade'] * 0.6), 1)
            f['status'] = 'BOM' if f['score'] >= 85 else 'CRÍTICO'
        
        # Ordenar por score
        fornecedores_lista = list(fornecedores.values())
        fornecedores_lista.sort(key=lambda x: x['score'], reverse=True)
        
        # Métricas gerais
        total_recebimentos = len(recebimentos_lista)
        total_fornecedores = len(fornecedores_lista)
        fornecedores_criticos = sum(1 for f in fornecedores_lista if f['score'] < 85)
        media_score = round(sum(f['score'] for f in fornecedores_lista) / total_fornecedores, 1) if total_fornecedores > 0 else 0
        
        conn.close()
        
        return {
            'status': 'success',
            'periodo': {
                'inicio': data_limite,
                'fim': datetime.now().strftime('%Y-%m-%d'),
                'dias': dias
            },
            'metricas': {
                'total_recebimentos': total_recebimentos,
                'total_fornecedores': total_fornecedores,
                'fornecedores_criticos': fornecedores_criticos,
                'media_score': media_score
            },
            'fornecedores': fornecedores_lista
        }
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao analisar desempenho de fornecedores: {str(e)}")

def executar_consulta_sql(query):
    """Executa uma consulta SQL diretamente no banco de dados (SOMENTE PARA CONSULTAS!)"""
    # Verificar se não é uma consulta de modificação
    query_lower = query.lower().strip()
    if (
        query_lower.startswith("insert") or 
        query_lower.startswith("update") or 
        query_lower.startswith("delete") or 
        query_lower.startswith("drop") or 
        query_lower.startswith("alter")
    ):
        raise Exception("Consultas de modificação não são permitidas por razões de segurança.")
    
    conn = get_db_connection()
    
    try:
        # Executar a consulta
        resultado = conn.execute(query).fetchall()
        conn.close()
        
        # Converter para lista de dicionários
        if resultado:
            return [dict(r) for r in resultado]
        else:
            return []
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao executar consulta SQL: {str(e)}")

def consultar_cliente(nome_cliente):
    """Consulta informações sobre um cliente específico"""
    conn = get_db_connection()
    
    try:
        # Buscar produtos do cliente
        produtos = conn.execute('''
            SELECT id, nome, 
                   (SELECT COUNT(*) FROM producoes WHERE produto_id = produtos.id) as producoes
            FROM produtos 
            WHERE UPPER(descricao) LIKE UPPER(?)
            ORDER BY nome
        ''', (f'%{nome_cliente}%',)).fetchall()
        
        if not produtos:
            conn.close()
            return None
        
        # Calcular métricas do cliente
        total_produtos = len(produtos)
        total_producoes = sum(p['producoes'] for p in produtos)
        
        # Produções recentes do cliente
        producoes_recentes = conn.execute('''
            SELECT p.id, pr.nome as produto, p.quantidade, p.data, p.status
            FROM producoes p
            JOIN produtos pr ON p.produto_id = pr.id
            WHERE UPPER(pr.descricao) LIKE UPPER(?)
            ORDER BY p.data DESC
            LIMIT 10
        ''', (f'%{nome_cliente}%',)).fetchall()
        
        # Nome exato do cliente (a partir do primeiro produto encontrado)
        nome_exato = produtos[0]['descricao'] if 'descricao' in produtos[0] else nome_cliente
        
        conn.close()
        
        return {
            'nome': nome_exato,
            'total_produtos': total_produtos,
            'total_producoes': total_producoes,
            'produtos': [dict(p) for p in produtos],
            'producoes_recentes': [dict(p) for p in producoes_recentes]
        }
    
    except Exception as e:
        conn.close()
        raise Exception(f"Erro ao consultar cliente: {str(e)}") 