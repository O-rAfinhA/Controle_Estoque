from database import get_db_connection
from datetime import datetime

def format_status(status):
    """Format status for display"""
    status_labels = {
        'aprovado': 'Aprovado 100%',
        'ac': 'AC (Aceito Condicionalmente)',
        'rejeitado': 'Rejeitado'
    }
    return status_labels.get(status, status)

def format_currency(value):
    """Format a value as currency"""
    if isinstance(value, (int, float)):
        return f"{value:.2f}".replace('.', ',')
    return value

def calcular_dias_atraso(data_prevista, data_recebimento):
    """Calculate delay days between expected and actual receipt dates"""
    try:
        if isinstance(data_prevista, str):
            prevista = datetime.strptime(data_prevista, '%Y-%m-%d')
        else:
            prevista = data_prevista
            
        if isinstance(data_recebimento, str):
            recebimento = datetime.strptime(data_recebimento, '%Y-%m-%d')
        else:
            recebimento = data_recebimento
            
        if recebimento > prevista:
            diff_days = (recebimento - prevista).days
            return diff_days
        return 0
    except (ValueError, TypeError) as e:
        print(f"Erro ao calcular dias de atraso: {e}")
        return 0

def get_fornecedores():
    """Get all suppliers from database"""
    conn = get_db_connection()
    fornecedores = conn.execute('SELECT * FROM fornecedores ORDER BY nome').fetchall()
    conn.close()
    return fornecedores

def get_recebimentos():
    """Get all receipts with supplier information from database"""
    conn = get_db_connection()
    recebimentos = conn.execute('''
        SELECT r.*, f.nome as fornecedor_nome 
        FROM recebimentos r
        JOIN fornecedores f ON r.fornecedor_id = f.id
        ORDER BY r.data_recebimento DESC
    ''').fetchall()
    conn.close()
    return recebimentos

def calcular_avaliacoes(recebimentos_filtrados=None):
    """Calculate supplier evaluation metrics
    
    Args:
        recebimentos_filtrados: Optional list of filtered receipts. If not provided,
                               all receipts will be fetched from the database.
    """
    conn = get_db_connection()
    fornecedores = conn.execute('SELECT * FROM fornecedores').fetchall()
    
    avaliacoes = []
    
    for fornecedor in fornecedores:
        if recebimentos_filtrados is None:
            # Buscar do banco de dados todos os recebimentos do fornecedor
            recebimentos = conn.execute('''
                SELECT * FROM recebimentos 
                WHERE fornecedor_id = ?
            ''', (fornecedor['id'],)).fetchall()
        else:
            # Filtrar os recebimentos já fornecidos para este fornecedor
            recebimentos = [r for r in recebimentos_filtrados if r['fornecedor_id'] == fornecedor['id']]
        
        if recebimentos:
            total = len(recebimentos)
            aprovado100 = len([r for r in recebimentos if r['status'] == 'aprovado'])
            acRejeitado = total - aprovado100
            emAtraso = len([r for r in recebimentos if r['dias_atraso'] > 0])
            
            percentualAprovacao = round((aprovado100 / total) * 100, 1) if total > 0 else 0
            percentualPontualidade = round(((total - emAtraso) / total) * 100, 1) if total > 0 else 0
            scoreFinal = round((percentualAprovacao + percentualPontualidade) / 2, 1)
            
            avaliacoes.append({
                'id': fornecedor['id'],
                'nome': fornecedor['nome'],
                'total': total,
                'aprovado100': aprovado100,
                'acRejeitado': acRejeitado,
                'emAtraso': emAtraso,
                'percentualAprovacao': percentualAprovacao,
                'percentualPontualidade': percentualPontualidade,
                'scoreFinal': scoreFinal
            })
    
    conn.close()
    return avaliacoes

def calcular_ranking_fornecedores():
    """Calculate supplier ranking with trends and status"""
    avaliacoes = calcular_avaliacoes()
    
    # Sort by score (highest first)
    avaliacoes.sort(key=lambda x: x['scoreFinal'], reverse=True)
    
    ranking = []
    
    for aval in avaliacoes:
        status = 'Aprovado' if aval['scoreFinal'] >= 85 else 'Em Observação' if aval['scoreFinal'] >= 70 else 'Reprovado'
        
        # Calculate trend (simplified for now)
        tendencia = calcular_tendencia(aval)
        
        ranking.append({
            'fornecedor': {
                'id': aval['id'],
                'nome': aval['nome']
            },
            'totalRecebimentos': aval['total'],
            'percPontualidade': aval['percentualPontualidade'],
            'percQualidade': aval['percentualAprovacao'],
            'scoreFinal': aval['scoreFinal'],
            'status': status,
            'tendencia': tendencia
        })
    
    return ranking

def calcular_tendencia(avaliacao):
    """Calculate trend for a supplier (simplified)"""
    # In a real implementation, we would compare with historical data
    # For now, let's use a simple algorithm based on approval rate
    
    if avaliacao['total'] < 2:
        return {
            'texto': 'Dados Insuficientes',
            'class': ''
        }
    
    # If approval rate is high, consider it as improving
    if avaliacao['percentualAprovacao'] > 85:
        return {
            'texto': 'Melhora',
            'class': 'tendencia-melhora'
        }
    
    # If punctuality is low, consider it as deteriorating
    if avaliacao['percentualPontualidade'] < 70:
        return {
            'texto': 'Piora',
            'class': 'tendencia-piora'
        }
    
    # Otherwise, consider it stable
    return {
        'texto': 'Estável',
        'class': 'tendencia-estavel'
    }

def gerar_analise_tendencias():
    """Generate trend analysis HTML content"""
    avaliacoes = calcular_avaliacoes()
    
    html = '<h4>Resumo da Análise</h4>'
    
    # Critical suppliers
    fornecedores_criticos = [a for a in avaliacoes if a['scoreFinal'] < 70]
    if fornecedores_criticos:
        html += '<h5>Fornecedores Críticos (Score &lt; 70%)</h5>'
        for f in fornecedores_criticos:
            html += f'<p><strong>{f["nome"]}</strong>: Score {f["scoreFinal"]}% - '
            html += f'Pontualidade: {f["percentualPontualidade"]}%, Qualidade: {f["percentualAprovacao"]}%</p>'
    
    # Excellent suppliers
    fornecedores_excelentes = [a for a in avaliacoes if a['scoreFinal'] >= 95]
    if fornecedores_excelentes:
        html += '<h5>Fornecedores Excelentes (Score &gt;= 95%)</h5>'
        for f in fornecedores_excelentes:
            html += f'<p><strong>{f["nome"]}</strong>: Score {f["scoreFinal"]}%</p>'
    
    # If no suppliers in either category
    if not fornecedores_criticos and not fornecedores_excelentes:
        html += '<p>Não há fornecedores em situação crítica ou excelente no momento.</p>'
    
    return html

def gerar_recomendacoes_html():
    """Generate recommendations HTML content"""
    avaliacoes = calcular_avaliacoes()
    
    html = '<h4>Recomendações de Ação</h4>'
    
    for aval in avaliacoes:
        if aval['scoreFinal'] < 70:
            html += f'''<div class="alert alert-danger">
                <h5>{aval['nome']} - Ação Urgente Necessária</h5>
                <p>Score atual: {aval['scoreFinal']}%</p>
                <ul>
                    {('<li>Estabelecer plano de melhoria para pontualidade</li>' if aval['percentualPontualidade'] < 70 else '')}
                    {('<li>Implementar programa de qualidade com o fornecedor</li>' if aval['percentualAprovacao'] < 70 else '')}
                    <li>Considerar desenvolvimento de fornecedores alternativos</li>
                    <li>Agendar reunião imediata com o fornecedor</li>
                </ul>
            </div>'''
        elif aval['scoreFinal'] < 85:
            html += f'''<div class="alert alert-warning">
                <h5>{aval['nome']} - Monitoramento Próximo</h5>
                <p>Score atual: {aval['scoreFinal']}%</p>
                <ul>
                    <li>Acompanhar mais de perto as entregas</li>
                    <li>Propor metas de melhoria</li>
                    {('<li>Revisar prazos acordados</li>' if aval['percentualPontualidade'] < 85 else '')}
                </ul>
            </div>'''
        elif aval['scoreFinal'] >= 95:
            html += f'''<div class="alert alert-success">
                <h5>{aval['nome']} - Reconhecimento</h5>
                <p>Score atual: {aval['scoreFinal']}%</p>
                <ul>
                    <li>Considerar para parcerias estratégicas</li>
                    <li>Possível candidato para aumento de volume</li>
                    <li>Avaliar programa de benefícios/premiação</li>
                </ul>
            </div>'''
    
    if not avaliacoes:
        html += '<p>Não há fornecedores registrados ou com avaliações suficientes para gerar recomendações.</p>'
    
    return html

def obter_anos_disponiveis():
    """Get available years from receipt data"""
    conn = get_db_connection()
    anos_rows = conn.execute('''
        SELECT DISTINCT strftime('%Y', data_recebimento) as ano 
        FROM recebimentos 
        ORDER BY ano DESC
    ''').fetchall()
    
    anos = [row['ano'] for row in anos_rows]
    
    # If no data, return current year
    if not anos:
        anos = [str(datetime.now().year)]
    
    conn.close()
    return anos

def gerar_filtros_periodo(anos=None):
    """Generate period filters for reporting"""
    if anos is None:
        anos = obter_anos_disponiveis()
    
    trimestres = []
    semestres = []
    
    for ano in anos:
        for i in range(1, 5):
            trimestres.append({
                'valor': f"{ano}-T{i}",
                'texto': f"{i}º Trimestre {ano}"
            })
        
        for i in range(1, 3):
            semestres.append({
                'valor': f"{ano}-S{i}",
                'texto': f"{i}º Semestre {ano}"
            })
    
    return {
        'anos': anos,
        'trimestres': trimestres,
        'semestres': semestres
    }

def filtrar_recebimentos_por_periodo(tipo_filtro, filtro_mes=None, filtro_trimestre=None, filtro_semestre=None, filtro_ano=None):
    """Filter receipts by selected period"""
    conn = get_db_connection()
    
    base_query = '''
        SELECT r.*, f.nome as fornecedor_nome 
        FROM recebimentos r
        JOIN fornecedores f ON r.fornecedor_id = f.id
    '''
    
    where_clause = ''
    params = []
    periodo_selecionado = "Todos os períodos"
    
    if tipo_filtro == 'mensal' and filtro_mes:
        where_clause = "WHERE strftime('%Y-%m', r.data_recebimento) = ?"
        params.append(filtro_mes)
        
        # Format month name for display
        try:
            ano, mes = filtro_mes.split('-')
            mes_int = int(mes)
            mes_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            periodo_selecionado = f"{mes_nomes[mes_int-1]} de {ano}"
        except:
            periodo_selecionado = filtro_mes
            
    elif tipo_filtro == 'trimestral' and filtro_trimestre:
        ano, trimestre = filtro_trimestre.split('-T')
        trimestre = int(trimestre)
        start_month = (trimestre - 1) * 3 + 1
        end_month = trimestre * 3
        
        where_clause = "WHERE strftime('%Y', r.data_recebimento) = ? AND CAST(strftime('%m', r.data_recebimento) AS INTEGER) BETWEEN ? AND ?"
        params.extend([ano, start_month, end_month])
        periodo_selecionado = f"{trimestre}º Trimestre de {ano}"
        
    elif tipo_filtro == 'semestral' and filtro_semestre:
        ano, semestre = filtro_semestre.split('-S')
        semestre = int(semestre)
        start_month = (semestre - 1) * 6 + 1
        end_month = semestre * 6
        
        where_clause = "WHERE strftime('%Y', r.data_recebimento) = ? AND CAST(strftime('%m', r.data_recebimento) AS INTEGER) BETWEEN ? AND ?"
        params.extend([ano, start_month, end_month])
        periodo_selecionado = f"{semestre}º Semestre de {ano}"
        
    elif tipo_filtro == 'anual' and filtro_ano:
        where_clause = "WHERE strftime('%Y', r.data_recebimento) = ?"
        params.append(filtro_ano)
        periodo_selecionado = f"Ano de {filtro_ano}"
    
    query = base_query + where_clause + " ORDER BY r.data_recebimento DESC"
    
    recebimentos = conn.execute(query, params).fetchall()
    conn.close()
    
    return recebimentos, periodo_selecionado

def gerar_relatorio_html(recebimentos, periodo_selecionado):
    """Generate HTML report for supplier evaluation"""
    # If no receipts, show simple message
    if not recebimentos:
        return f'''
            <div class="alert alert-info">
                <h4>Não há dados para o período selecionado: {periodo_selecionado}</h4>
                <p>Selecione outro período ou adicione recebimentos no sistema.</p>
            </div>
        '''
    
    # Count receipts by supplier
    fornecedores_map = {}
    for rec in recebimentos:
        forn_id = rec['fornecedor_id']
        if forn_id not in fornecedores_map:
            fornecedores_map[forn_id] = {
                'nome': rec['fornecedor_nome'],
                'recebimentos': [],
                'valor_total': 0,
                'quantidade_total': 0,
                'aprovados': 0,
                'atrasos': 0
            }
        
        fornecedores_map[forn_id]['recebimentos'].append(rec)
        fornecedores_map[forn_id]['valor_total'] += rec['valor']
        fornecedores_map[forn_id]['quantidade_total'] += rec['quantidade']
        
        if rec['status'] == 'aprovado':
            fornecedores_map[forn_id]['aprovados'] += 1
        
        if rec['dias_atraso'] > 0:
            fornecedores_map[forn_id]['atrasos'] += 1
    
    # Calculate total metrics
    total_recebimentos = len(recebimentos)
    total_aprovados = sum(1 for r in recebimentos if r['status'] == 'aprovado')
    total_atrasos = sum(1 for r in recebimentos if r['dias_atraso'] > 0)
    total_valor = sum(r['valor'] for r in recebimentos)
    
    percentual_aprovacao = round((total_aprovados / total_recebimentos) * 100, 1) if total_recebimentos > 0 else 0
    percentual_pontualidade = round(((total_recebimentos - total_atrasos) / total_recebimentos) * 100, 1) if total_recebimentos > 0 else 0
    
    # Build the HTML
    html = f'''
        <div class="card mb-4">
            <div class="card-body">
                <h2>Relatório Geral de Avaliação de Fornecedores</h2>
                <p>Data: {datetime.now().strftime('%d/%m/%Y')}</p>
                <p>Período: {periodo_selecionado}</p>
                
                <h3>Resumo Geral</h3>
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Total de Recebimentos</h5>
                                <p class="fs-4">{total_recebimentos}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">Valor Total</h5>
                                <p class="fs-4">R$ {format_currency(total_valor)}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">% Aprovação</h5>
                                <p class="fs-4">{percentual_aprovacao}%</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body text-center">
                                <h5 class="card-title">% Pontualidade</h5>
                                <p class="fs-4">{percentual_pontualidade}%</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <h3>Relatório Detalhado por Fornecedor</h3>
    '''
    
    # Add supplier details
    for forn_id, forn_data in fornecedores_map.items():
        total_rec = len(forn_data['recebimentos'])
        perc_aprovacao = round((forn_data['aprovados'] / total_rec) * 100, 1) if total_rec > 0 else 0
        perc_pontualidade = round(((total_rec - forn_data['atrasos']) / total_rec) * 100, 1) if total_rec > 0 else 0
        score_final = round((perc_aprovacao + perc_pontualidade) / 2, 1)
        
        status_class = 'success' if score_final >= 85 else 'warning' if score_final >= 70 else 'danger'
        
        html += f'''
            <div class="card mb-4">
                <div class="card-header bg-{status_class} text-white">
                    <h4 class="m-0">{forn_data['nome']} - Score: {score_final}%</h4>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-3">
                            <p><strong>Total de Recebimentos:</strong> {total_rec}</p>
                        </div>
                        <div class="col-md-3">
                            <p><strong>Valor Total:</strong> R$ {format_currency(forn_data['valor_total'])}</p>
                        </div>
                        <div class="col-md-3">
                            <p><strong>% Aprovação:</strong> {perc_aprovacao}%</p>
                        </div>
                        <div class="col-md-3">
                            <p><strong>% Pontualidade:</strong> {perc_pontualidade}%</p>
                        </div>
                    </div>
                    
                    <h5>Histórico de Recebimentos</h5>
                    <div class="table-responsive">
                        <table class="table table-sm table-striped">
                            <thead>
                                <tr>
                                    <th>Data</th>
                                    <th>NF</th>
                                    <th>Valor</th>
                                    <th>Status</th>
                                    <th>Dias de Atraso</th>
                                    <th>Recebido por</th>
                                </tr>
                            </thead>
                            <tbody>
        '''
        
        for rec in forn_data['recebimentos']:
            data_formatada = datetime.strptime(rec['data_recebimento'], '%Y-%m-%d').strftime('%d/%m/%Y') if isinstance(rec['data_recebimento'], str) else rec['data_recebimento'].strftime('%d/%m/%Y')
            status_text = format_status(rec['status'])
            status_row_class = 'table-success' if rec['status'] == 'aprovado' else 'table-warning' if rec['status'] == 'ac' else 'table-danger'
            atraso_class = 'text-danger fw-bold' if rec['dias_atraso'] > 0 else ''
            
            html += f'''
                                <tr class="{status_row_class}">
                                    <td>{data_formatada}</td>
                                    <td>{rec['nf']}</td>
                                    <td>R$ {format_currency(rec['valor'])}</td>
                                    <td>{status_text}</td>
                                    <td class="{atraso_class}">{rec['dias_atraso']}</td>
                                    <td>{rec['recebido_por']}</td>
                                </tr>
            '''
        
        html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        '''
    
    html += '''
            </div>
        </div>
    '''
    
    return html 