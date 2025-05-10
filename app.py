from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
import sqlite3
import os
from database import init_db, get_db_connection
import json
from datetime import datetime, timedelta
import secrets
import string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import csv
import io
from fornecedores_utils import (
    format_status, format_currency, calcular_dias_atraso, 
    get_fornecedores, get_recebimentos, calcular_avaliacoes, 
    calcular_ranking_fornecedores, gerar_analise_tendencias,
    gerar_recomendacoes_html, obter_anos_disponiveis,
    gerar_filtros_periodo, filtrar_recebimentos_por_periodo,
    gerar_relatorio_html
)
import re
from functools import cmp_to_key
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
from matplotlib.backends.backend_pdf import PdfPages
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Ajuste do fuso horário (São Paulo - UTC-3)
TIMEZONE_OFFSET = 0  # Horas de diferença para o fuso horário de São Paulo

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = 'seu_segredo_aqui'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 horas em segundos

# Inicializa o banco de dados se não existir
init_db()

# Inicializa as tabelas para o sistema de avaliação de fornecedores
def init_db_fornecedores():
    """Inicializa as tabelas necessárias para o sistema de avaliação de fornecedores"""
    conn = get_db_connection()
    
    # Cria a tabela de fornecedores
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            email TEXT,
            telefone TEXT,
            data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cria a tabela de recebimentos de materiais
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recebimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_recebimento DATE NOT NULL,
            data_prevista DATE NOT NULL,
            dias_atraso INTEGER NOT NULL,
            pc TEXT UNIQUE NOT NULL,
            nf TEXT UNIQUE NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            valor REAL NOT NULL,
            quantidade INTEGER NOT NULL,
            status TEXT NOT NULL,
            recebido_por TEXT NOT NULL,
            descricao_ocorrencia TEXT,
            acao_imediata TEXT,
            acao_corretiva TEXT,
            data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            usuario_id INTEGER,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Inicializa as tabelas de fornecedores na inicialização da aplicação
init_db_fornecedores()

# Função para verificar se o usuário está logado
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Função para verificar se o usuário é administrador
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        
        conn = get_db_connection()
        usuario = conn.execute('SELECT admin FROM usuarios WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        
        if not usuario or not usuario['admin']:
            flash('Acesso negado. Você não tem permissão para acessar esta página.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

# Adiciona as rotas necessárias para o sistema de avaliação de fornecedores
@app.route('/avaliacao-fornecedores/exportar-analise')
@login_required
def exportar_analise_desempenho():
    """Exporta a análise de desempenho dos fornecedores em formato PDF"""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from io import BytesIO
    
    # Obter parâmetros de filtro
    tipo_filtro = request.args.get('tipo_filtro', 'todos')
    filtro_mes = request.args.get('filtro_mes', '')
    filtro_trimestre = request.args.get('filtro_trimestre', '')
    filtro_semestre = request.args.get('filtro_semestre', '')
    filtro_ano = request.args.get('filtro_ano', '')
    
    # Aplicar filtro aos recebimentos
    recebimentos_filtrados, periodo_selecionado = filtrar_recebimentos_por_periodo(
        tipo_filtro, filtro_mes, filtro_trimestre, filtro_semestre, filtro_ano
    )
    
    # Se não existirem recebimentos, retorne erro
    if not recebimentos_filtrados:
        flash("Não há dados para exportar neste período.", "warning")
        return redirect(url_for('relatorios_fornecedores', 
                               tab='relatorios',
                               tipo_filtro=tipo_filtro,
                               filtro_mes=filtro_mes,
                               filtro_trimestre=filtro_trimestre,
                               filtro_semestre=filtro_semestre,
                               filtro_ano=filtro_ano))
    
    # Calcular avaliações dos fornecedores no período
    avaliacoes_periodo = calcular_avaliacoes(recebimentos_filtrados)
    
    # Criar um buffer de memória para o PDF
    buffer = BytesIO()
    
    try:
        # Configuração básica do documento
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Lista para elementos do PDF
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Título
        elements.append(Paragraph("Relatório de Fornecedores", styles['Title']))
        elements.append(Spacer(1, 12))
        
        # Informações do relatório
        elements.append(Paragraph(f"Período: {periodo_selecionado}", styles['Normal']))
        elements.append(Paragraph(f"Data de geração: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 24))
        
        # Tabela de fornecedores
        elements.append(Paragraph("Desempenho dos Fornecedores", styles['Heading2']))
        elements.append(Spacer(1, 12))
        
        # Dados da tabela
        table_data = [
            ['Fornecedor', 'Recebimentos', 'Aprovação (%)', 'Pontualidade (%)', 'Score Final', 'Status']
        ]
        
        # Preencher dados
        for avaliacao in avaliacoes_periodo:
            status = "Aprovado" if avaliacao['scoreFinal'] >= 85 else "Crítico"
            table_data.append([
                avaliacao['nome'],
                str(avaliacao['total']),
                f"{avaliacao['percentualAprovacao']:.1f}%",
                f"{avaliacao['percentualPontualidade']:.1f}%",
                f"{avaliacao['scoreFinal']:.1f}%",
                status
            ])
        
        # Criar tabela
        table = Table(table_data, repeatRows=1)
        
        # Estilo da tabela
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 1), (-2, -1), 'CENTER'),
        ])
        
        table.setStyle(table_style)
        elements.append(table)
        
        # Fornecedores críticos
        fornecedores_criticos = [a for a in avaliacoes_periodo if a['scoreFinal'] < 85]
        
        if fornecedores_criticos:
            elements.append(Spacer(1, 24))
            elements.append(Paragraph("Fornecedores Críticos", styles['Heading2']))
            elements.append(Spacer(1, 12))
            
            # Lista de fornecedores críticos
            for fornecedor in fornecedores_criticos:
                elements.append(Paragraph(f"{fornecedor['nome']} - Score: {fornecedor['scoreFinal']:.1f}%", styles['Normal']))
                elements.append(Spacer(1, 6))
        
        # Construir o documento
        doc.build(elements)
        
        # Preparar a resposta
        buffer.seek(0)
        
        # Nome do arquivo
        data_arquivo = datetime.now().strftime('%Y%m%d')
        
        return Response(
            buffer.getvalue(),
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment;filename=relatorio_fornecedores_{data_arquivo}.pdf"}
        )
        
    except Exception as e:
        # Em caso de erro, log e retornar mensagem amigável
        print(f"Erro ao gerar PDF: {str(e)}")
        flash("Ocorreu um erro ao gerar o PDF. Por favor, tente novamente.", "danger")
        return redirect(url_for('relatorios_fornecedores'))

@app.route('/avaliacao-fornecedores/gerar-recomendacoes')
@login_required
def gerar_recomendacoes():
    """Gera recomendações automatizadas para fornecedores com baixo desempenho"""
    avaliacoes = calcular_avaliacoes()
    
    # Filtrar fornecedores com score abaixo de 85
    fornecedores_baixo_desempenho = [f for f in avaliacoes if f['scoreFinal'] < 85]
    
    # Gerar recomendações HTML
    html_recomendacoes = gerar_recomendacoes_html(fornecedores_baixo_desempenho)
    
    # Passamos as recomendações para a mesma página, mas incluindo um parâmetro na URL para mostrar a aba correta
    flash('Recomendações geradas com sucesso!', 'success')
    return render_template('avaliacao_fornecedores.html',
                          fornecedores=get_fornecedores(),
                          recebimentos=get_recebimentos(),
                          avaliacoes=avaliacoes,
                          total_recebimentos=len(get_recebimentos()),
                          ranking_fornecedores=calcular_ranking_fornecedores(),
                          total_fornecedores=len(get_fornecedores()),
                          fornecedores_acima_meta=len([r for r in calcular_ranking_fornecedores() if r['scoreFinal'] >= 85]),
                          fornecedores_abaixo_meta=len([r for r in calcular_ranking_fornecedores() if r['scoreFinal'] < 85]),
                          media_geral_performance=round(sum(a['scoreFinal'] for a in avaliacoes) / len(avaliacoes) if avaliacoes else 0, 1),
                          analise_tendencias=html_recomendacoes,  # Trocamos a análise de tendências pelas recomendações
                          tab_ativa='analise-desempenho')

@app.route('/avaliacao-fornecedores/relatorios')
@login_required
def relatorios_fornecedores():
    """Página de relatórios com filtros por período"""
    # Verificar se foi uma solicitação GET com parâmetros (aplicação de filtro)
    # ou apenas carregamento inicial da página
    is_initial_load = len(request.args) == 0
    
    # Obter parâmetros de filtro
    tipo_filtro = "" if is_initial_load else request.args.get('tipo_filtro', '')
    filtro_mes = "" if is_initial_load else request.args.get('filtro_mes', '')
    filtro_trimestre = "" if is_initial_load else request.args.get('filtro_trimestre', '')
    filtro_semestre = "" if is_initial_load else request.args.get('filtro_semestre', '')
    filtro_ano = "" if is_initial_load else request.args.get('filtro_ano', '')
    apenas_criticos = False if is_initial_load else request.args.get('apenas_criticos', 'false') == 'true'
    
    # Em carregamento inicial, forçar filtro_aplicado para falso
    # Em solicitação com parâmetros, verificar se os parâmetros são válidos
    if is_initial_load:
        filtro_aplicado = False
    else:
        filtro_aplicado = bool(tipo_filtro and (filtro_mes or filtro_trimestre or filtro_semestre or filtro_ano))
    
    # Obter anos disponíveis para filtro
    anos = obter_anos_disponiveis()
    
    # Gerar filtros por período (trimestres e semestres)
    filtros = gerar_filtros_periodo(anos)
    
    # Inicializar variáveis
    recebimentos_filtrados = []
    periodo_selecionado = ""
    relatorio = None
    fornecedores_criticos = []
    acoes_corretivas = []
    
    # Carregar dados apenas se não for carregamento inicial
    # e o filtro foi aplicado corretamente
    if not is_initial_load and filtro_aplicado:
        recebimentos_filtrados, periodo_selecionado = filtrar_recebimentos_por_periodo(
            tipo_filtro, filtro_mes, filtro_trimestre, filtro_semestre, filtro_ano
        )
        
        # Gerar o relatório se houver dados filtrados específicos
        if recebimentos_filtrados and periodo_selecionado != "Todos os períodos":
            # Obter avaliações com base nos recebimentos filtrados
            avaliacoes_periodo = calcular_avaliacoes(recebimentos_filtrados)
            
            # Filtrar apenas fornecedores críticos (abaixo da meta de 85%)
            if apenas_criticos:
                # Criar lista de fornecedores críticos com detalhes dos problemas
                for avaliacao in avaliacoes_periodo:
                    if avaliacao['scoreFinal'] < 85:
                        fornecedor_id = avaliacao['id']
                        
                        # Filtrar recebimentos problemáticos desse fornecedor
                        problemas = [r for r in recebimentos_filtrados 
                                    if r['fornecedor_id'] == fornecedor_id and 
                                       r['status'] in ('ac', 'rejeitado')]
                        
                        causas = [
                            "Problemas de qualidade recorrentes",
                            "Atrasos constantes nas entregas",
                            "Falhas de comunicação"
                        ]
                        
                        recomendacoes = [
                            "Realizar reunião de alinhamento com fornecedor",
                            "Solicitar plano de ação para melhorias",
                            "Definir cronograma de acompanhamento"
                        ]
                        
                        # Adicionar fornecedor à lista de críticos
                        fornecedores_criticos.append({
                            'id': fornecedor_id,
                            'nome': avaliacao['nome'],
                            'total_recebimentos': avaliacao['total'],
                            'perc_aprovacao': avaliacao['percentualAprovacao'],
                            'perc_pontualidade': avaliacao['percentualPontualidade'],
                            'score_final': avaliacao['scoreFinal'],
                            'problemas': problemas,
                            'causas': causas,
                            'recomendacoes': recomendacoes
                        })
                
                # Criar lista de ações corretivas somente se houver fornecedores críticos
                if fornecedores_criticos:
                    for problema in [r for r in recebimentos_filtrados if r['status'] in ('ac', 'rejeitado') and r['acao_corretiva']]:
                        acoes_corretivas.append({
                            'fornecedor': problema['fornecedor_nome'],
                            'numero': problema['acao_corretiva'],
                            'data_abertura': problema['data_recebimento'],
                            'status': 'Em andamento',
                            'status_badge': 'bg-warning',
                            'eficacia': 'Em avaliação'
                        })
                    
                    relatorio = "Relatório gerado com sucesso."
            else:
                relatorio = gerar_relatorio_html(recebimentos_filtrados, periodo_selecionado)
    
    # Obter dados básicos para o resto da página
    if filtro_aplicado:
        # Carregar dados completos somente se um filtro foi aplicado
        fornecedores = get_fornecedores()
        recebimentos = get_recebimentos()
        avaliacoes = calcular_avaliacoes()
        ranking_fornecedores = calcular_ranking_fornecedores()
        total_recebimentos = len(recebimentos)
        total_fornecedores = len(fornecedores)
        fornecedores_acima_meta = len([r for r in ranking_fornecedores if r['scoreFinal'] >= 85])
        fornecedores_abaixo_meta = len([r for r in ranking_fornecedores if r['scoreFinal'] < 85])
        media_geral_performance = round(sum(a['scoreFinal'] for a in avaliacoes) / len(avaliacoes) if avaliacoes else 0, 1)
        analise_tendencias = gerar_analise_tendencias()
    else:
        # Dados mínimos necessários quando não há filtro aplicado
        fornecedores = []
        recebimentos = []
        avaliacoes = []
        ranking_fornecedores = []
        total_recebimentos = 0
        total_fornecedores = 0
        fornecedores_acima_meta = 0
        fornecedores_abaixo_meta = 0
        media_geral_performance = 0
        analise_tendencias = {}
    
    # Renderizar a nova template dedicada para relatórios
    return render_template('relatorios_fornecedores.html',
                          fornecedores=fornecedores,
                          recebimentos=recebimentos,
                          avaliacoes=avaliacoes,
                          total_recebimentos=total_recebimentos,
                          ranking_fornecedores=ranking_fornecedores,
                          total_fornecedores=total_fornecedores,
                          fornecedores_acima_meta=fornecedores_acima_meta,
                          fornecedores_abaixo_meta=fornecedores_abaixo_meta,
                          media_geral_performance=media_geral_performance,
                          analise_tendencias=analise_tendencias,
                          tab_ativa='relatorios',
                          tipo_filtro=tipo_filtro,
                          filtro_mes=filtro_mes,
                          filtro_trimestre=filtro_trimestre,
                          filtro_semestre=filtro_semestre,
                          filtro_ano=filtro_ano,
                          trimestres=filtros['trimestres'],
                          semestres=filtros['semestres'],
                          anos=anos,
                          periodo_selecionado=periodo_selecionado,
                          fornecedores_criticos=fornecedores_criticos,
                          acoes_corretivas=acoes_corretivas,
                          relatorio=relatorio,
                          filtro_aplicado=filtro_aplicado,
                          is_initial_load=is_initial_load)

@app.route('/avaliacao-fornecedores/exportar-excel')
@login_required
def exportar_excel():
    """Exportar relatório para Excel/CSV"""
    # Obter parâmetros de filtro
    tipo_filtro = request.args.get('tipo_filtro', 'todos')
    filtro_mes = request.args.get('filtro_mes', '')
    filtro_trimestre = request.args.get('filtro_trimestre', '')
    filtro_semestre = request.args.get('filtro_semestre', '')
    filtro_ano = request.args.get('filtro_ano', '')
    apenas_criticos = request.args.get('apenas_criticos', 'false') == 'true'
    
    # Aplicar filtro aos recebimentos
    recebimentos_filtrados, periodo_selecionado = filtrar_recebimentos_por_periodo(
        tipo_filtro, filtro_mes, filtro_trimestre, filtro_semestre, filtro_ano
    )
    
    # Se não existirem recebimentos, retorne erro
    if not recebimentos_filtrados:
        flash("Não há dados para exportar neste período.", "warning")
        return redirect(url_for('relatorios_fornecedores', 
                               tab='relatorios',
                               tipo_filtro=tipo_filtro,
                               filtro_mes=filtro_mes,
                               filtro_trimestre=filtro_trimestre,
                               filtro_semestre=filtro_semestre,
                               filtro_ano=filtro_ano))
    
    # Calcular avaliações dos fornecedores no período
    avaliacoes_periodo = calcular_avaliacoes(recebimentos_filtrados)
    
    # Filtrar apenas fornecedores críticos se solicitado
    if apenas_criticos:
        avaliacoes_periodo = [a for a in avaliacoes_periodo if a['scoreFinal'] < 85]
    
    # Criar buffer para o CSV
    output = io.StringIO()
    
    # Usar csv.writer com configuração para evitar problemas com caracteres especiais
    writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    # Escrever cabeçalho
    writer.writerow(['Relatório de Avaliação de Fornecedores'])
    writer.writerow(['Período:', periodo_selecionado])
    writer.writerow(['Data de exportação:', datetime.now().strftime('%d/%m/%Y')])
    writer.writerow([])
    
    if apenas_criticos:
        writer.writerow(['FORNECEDORES CRÍTICOS (Score < 85%)'])
    else:
        writer.writerow(['DESEMPENHO DOS FORNECEDORES'])
    
    writer.writerow([])
    writer.writerow(['Fornecedor', 'Total Recebimentos', 'Aprovados 100%', 'Aceitos Condicional/Rejeitados',
                    'Aprovação (%)', 'Pontualidade (%)', 'Score Final (%)', 'Status'])
    
    # Escrever dados dos fornecedores
    for avaliacao in avaliacoes_periodo:
        status = 'BOM' if avaliacao['scoreFinal'] >= 85 else 'CRÍTICO'
        
        writer.writerow([
            avaliacao['nome'],
            avaliacao['total'],
            avaliacao['aprovado100'],
            avaliacao['acRejeitado'],
            f"{avaliacao['percentualAprovacao']:.1f}",
            f"{avaliacao['percentualPontualidade']:.1f}",
            f"{avaliacao['scoreFinal']:.1f}",
            status
        ])
    
    if apenas_criticos:
        # Adicionar detalhes dos problemas para fornecedores críticos
        writer.writerow([])
        writer.writerow(['DETALHES DOS PROBLEMAS'])
        writer.writerow([])
        writer.writerow(['Fornecedor', 'Data', 'PC', 'NF', 'Status', 'Problema', 'Ação Corretiva'])
        
        for avaliacao in avaliacoes_periodo:
            fornecedor_id = avaliacao['id']
            fornecedor_nome = avaliacao['nome']
            
            # Filtrar problemas deste fornecedor
            problemas = [r for r in recebimentos_filtrados 
                        if r['fornecedor_id'] == fornecedor_id and 
                           r['status'] in ('ac', 'rejeitado')]
            
            for problema in problemas:
                data = datetime.strptime(problema['data_recebimento'], '%Y-%m-%d').strftime('%d/%m/%Y') if isinstance(problema['data_recebimento'], str) else problema['data_recebimento'].strftime('%d/%m/%Y')
                status_text = 'Aceito Condicional' if problema['status'] == 'ac' else 'Rejeitado'
                
                writer.writerow([
                    fornecedor_nome,
                    data,
                    problema['pc'],
                    problema['nf'],
                    status_text,
                    problema.get('descricao_ocorrencia', ''),
                    problema.get('acao_corretiva', '')
                ])
    
    # Obter conteúdo do CSV
    csv_content = output.getvalue().encode('utf-8-sig')  # Codificar com BOM para Excel reconhecer acentos
    
    # Data atual para nome do arquivo
    data_arquivo = datetime.now().strftime('%Y%m%d')
    
    tipo_relatorio = 'criticos' if apenas_criticos else 'completo'
    
    # Configurar a resposta com MIME type correto
    response = Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment;filename=relatorio_fornecedores_{tipo_relatorio}_{data_arquivo}.csv",
            "Content-Type": "text/csv; charset=utf-8-sig"
        }
    )
    
    return response

# Função auxiliar para verificar se é administrador (usado nos templates)
def is_admin():
    if 'user_id' not in session:
        return False
    
    conn = get_db_connection()
    usuario = conn.execute('SELECT admin FROM usuarios WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return usuario and usuario['admin'] == 1

# Context processor para disponibilizar funções e variáveis nos templates
@app.context_processor
def utility_processor():
    def now_adjusted():
        """Retorna o datetime atual ajustado para o fuso horário de São Paulo"""
        return datetime.now() + timedelta(hours=TIMEZONE_OFFSET +3)
    
    return {
        'is_admin': is_admin,  # Passando a função, não o resultado
        'now': now_adjusted()
    }

# Filtro para formatação de data e hora
@app.template_filter('formatdatetime')
def format_datetime(value, format='%d/%m/%Y às %H:%Mh'):
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            # Converte a string para objeto datetime
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            # Ajuste para o fuso horário de São Paulo
            value = value + timedelta(hours=TIMEZONE_OFFSET)
        except ValueError:
            return value
    return value.strftime(format)

# Filter for formatting status
@app.template_filter('format_status')
def status_filter(status):
    return format_status(status)

# Filter for formatting currency
@app.template_filter('format_currency')
def currency_filter(value):
    return format_currency(value)

# Função auxiliar para gerar token
def gerar_token(tamanho=32):
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,)).fetchone()
        
        if usuario and check_password_hash(usuario['senha'], senha):
            # Verifica se o usuário está aprovado
            # Verificamos primeiro se a coluna existe no objeto Row
            try:
                status = usuario['status']
                if status != 'aprovado':
                    flash('Sua conta está pendente de aprovação pelo administrador.', 'warning')
                    conn.close()
                    return render_template('login.html')
            except (IndexError, KeyError):
                # Se a coluna não existir, consideramos o usuário como aprovado (compatibilidade)
                pass
            
            # Armazena informações do usuário na sessão
            session['user_id'] = usuario['id']
            session['user_name'] = usuario['nome']
            
            # Verificamos se o campo admin existe
            try:
                is_admin_user = bool(usuario['admin'])
            except (IndexError, KeyError):
                is_admin_user = False
                
            session['is_admin'] = is_admin_user
            
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha incorretos!', 'danger')
        
        conn.close()
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro de usuário"""
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']
        
        # Validações básicas
        if not nome or not senha:
            flash('Todos os campos são obrigatórios!', 'danger')
            return render_template('register.html')
        
        if senha != confirmar_senha:
            flash('As senhas não coincidem!', 'danger')
            return render_template('register.html')
        
        # Verifica se o nome de usuário já está em uso
        conn = get_db_connection()
        usuario_existente = conn.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,)).fetchone()
        
        if usuario_existente:
            conn.close()
            flash('Este nome de usuário já está em uso!', 'danger')
            return render_template('register.html')
        
        # Verifica se é o primeiro usuário (será administrador e aprovado automaticamente)
        usuarios_count = conn.execute('SELECT COUNT(*) as count FROM usuarios').fetchone()
        primeiro_usuario = usuarios_count['count'] == 0
        
        # Define o status e admin baseado em ser o primeiro usuário ou não
        status = 'aprovado' if primeiro_usuario else 'pendente'
        admin = 1 if primeiro_usuario else 0
        
        # Cria o novo usuário
        senha_hash = generate_password_hash(senha)
        try:
            conn.execute(
                'INSERT INTO usuarios (nome, senha, status, admin) VALUES (?, ?, ?, ?)',
                (nome, senha_hash, status, admin)
            )
            conn.commit()
            
            if primeiro_usuario:
                flash('Conta de administrador criada com sucesso! Você pode fazer login agora.', 'success')
            else:
                flash('Conta criada com sucesso! Aguarde a aprovação do administrador para poder acessar o sistema.', 'success')
        except Exception as e:
            flash(f'Erro ao criar conta: {str(e)}', 'danger')
            
        conn.close()
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Encerra a sessão do usuário"""
    session.clear()
    flash('Você saiu do sistema!', 'info')
    return redirect(url_for('login'))

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    """Página para solicitar redefinição de senha"""
    if request.method == 'POST':
        nome = request.form['nome']
        
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE nome = ?', (nome,)).fetchone()
        
        if not usuario:
            conn.close()
            flash('Usuário não encontrado!', 'danger')
            return render_template('esqueci_senha.html')
        
        # Verifica se o usuário é um administrador
        if usuario['admin'] == 1:
            conn.close()
            flash('Não é possível redefinir a senha de administradores por este meio. Entre em contato com o suporte técnico.', 'danger')
            return render_template('esqueci_senha.html')
        
        # Verifica se já existe uma solicitação pendente para este usuário
        solicitacao_existente = conn.execute(
            'SELECT * FROM solicitacoes_senha WHERE usuario_id = ? AND status = "pendente"', 
            (usuario['id'],)
        ).fetchone()
        
        if solicitacao_existente:
            conn.close()
            flash('Já existe uma solicitação de redefinição de senha pendente para este usuário.', 'warning')
            return render_template('esqueci_senha.html')
        
        # Gera um token único
        token = gerar_token()
        
        # Registra a solicitação
        try:
            conn.execute(
                'INSERT INTO solicitacoes_senha (usuario_id, token, data_solicitacao) VALUES (?, ?, datetime("now", "localtime"))',
                (usuario['id'], token)
            )
            conn.commit()
            flash('Solicitação de redefinição de senha enviada. Aguarde a aprovação do administrador.', 'success')
        except Exception as e:
            flash(f'Erro ao solicitar redefinição: {str(e)}', 'danger')
        
        conn.close()
        return redirect(url_for('login'))
    
    return render_template('esqueci_senha.html')

@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    """Página para redefinir a senha após aprovação"""
    conn = get_db_connection()
    solicitacao = conn.execute(
        'SELECT s.*, u.nome, u.admin FROM solicitacoes_senha s JOIN usuarios u ON s.usuario_id = u.id WHERE s.token = ? AND s.status = "aprovado"',
        (token,)
    ).fetchone()
    
    if not solicitacao:
        conn.close()
        flash('Token inválido ou expirado!', 'danger')
        return redirect(url_for('login'))
    
    # Verificação adicional de segurança - não permitir para administradores
    if solicitacao['admin'] == 1:
        conn.execute('UPDATE solicitacoes_senha SET status = "rejeitado" WHERE id = ?', (solicitacao['id'],))
        conn.commit()
        conn.close()
        flash('Redefinição de senha para contas de administrador não é permitida por questões de segurança.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        senha = request.form['senha']
        confirmar_senha = request.form['confirmar_senha']
        
        if not senha:
            flash('A senha é obrigatória!', 'danger')
            return render_template('redefinir_senha.html', token=token, nome_usuario=solicitacao['nome'])
        
        if senha != confirmar_senha:
            flash('As senhas não coincidem!', 'danger')
            return render_template('redefinir_senha.html', token=token, nome_usuario=solicitacao['nome'])
        
        # Atualiza a senha
        senha_hash = generate_password_hash(senha)
        try:
            conn.execute('UPDATE usuarios SET senha = ? WHERE id = ?', (senha_hash, solicitacao['usuario_id']))
            conn.execute('UPDATE solicitacoes_senha SET status = "concluido" WHERE id = ?', (solicitacao['id'],))
            conn.commit()
            flash('Senha redefinida com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao redefinir senha: {str(e)}', 'danger')
            
        conn.close()
        return redirect(url_for('login'))
    
    conn.close()
    return render_template('redefinir_senha.html', token=token, nome_usuario=solicitacao['nome'])

@app.route('/admin/usuarios-pendentes')
@admin_required
def admin_usuarios_pendentes():
    """Painel de administrador para aprovar novos usuários"""
    conn = get_db_connection()
    usuarios_pendentes = conn.execute('SELECT * FROM usuarios WHERE status = "pendente" ORDER BY data_registro').fetchall()
    conn.close()
    
    return render_template('admin_usuarios_pendentes.html', usuarios=usuarios_pendentes)

@app.route('/admin/aprovar-usuario/<int:id>', methods=['POST'])
@admin_required
def admin_aprovar_usuario(id):
    """Aprova um usuário pendente"""
    conn = get_db_connection()
    conn.execute('UPDATE usuarios SET status = "aprovado" WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Usuário aprovado com sucesso!', 'success')
    return redirect(url_for('admin_usuarios_pendentes'))

@app.route('/admin/rejeitar-usuario/<int:id>', methods=['POST'])
@admin_required
def admin_rejeitar_usuario(id):
    """Rejeita um usuário pendente"""
    conn = get_db_connection()
    conn.execute('DELETE FROM usuarios WHERE id = ? AND status = "pendente"', (id,))
    conn.commit()
    conn.close()
    
    flash('Usuário rejeitado com sucesso!', 'success')
    return redirect(url_for('admin_usuarios_pendentes'))

@app.route('/admin/solicitacoes-senha')
@admin_required
def admin_solicitacoes_senha():
    """Painel de administrador para aprovar solicitações de redefinição de senha"""
    conn = get_db_connection()
    solicitacoes = conn.execute('''
        SELECT s.*, u.nome, u.admin
        FROM solicitacoes_senha s 
        JOIN usuarios u ON s.usuario_id = u.id 
        WHERE s.status = "pendente" AND u.admin = 0
        ORDER BY s.data_solicitacao
    ''').fetchall()
    conn.close()
    
    return render_template('admin_solicitacoes_senha.html', solicitacoes=solicitacoes)

@app.route('/admin/aprovar-solicitacao/<int:id>', methods=['POST'])
@admin_required
def admin_aprovar_solicitacao(id):
    """Aprova uma solicitação de redefinição de senha"""
    conn = get_db_connection()
    
    # Verificar se a solicitação é para um usuário administrador
    solicitacao = conn.execute('''
        SELECT s.*, u.nome, u.admin 
        FROM solicitacoes_senha s 
        JOIN usuarios u ON s.usuario_id = u.id 
        WHERE s.id = ?
    ''', (id,)).fetchone()
    
    if not solicitacao:
        conn.close()
        flash('Solicitação não encontrada!', 'danger')
        return redirect(url_for('admin_solicitacoes_senha'))
    
    # Verificar se o usuário é um administrador
    if solicitacao['admin'] == 1:
        conn.execute('UPDATE solicitacoes_senha SET status = "rejeitado" WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        flash('Solicitações de redefinição de senha para administradores não são permitidas por questões de segurança.', 'danger')
        return redirect(url_for('admin_solicitacoes_senha'))
    
    # Se não for administrador, prosseguir com a aprovação normal
    conn.execute('UPDATE solicitacoes_senha SET status = "aprovado" WHERE id = ?', (id,))
    conn.commit()
    
    link = url_for('redefinir_senha', token=solicitacao['token'], _external=True)
    flash(f'Solicitação aprovada! Link para redefinição: {link}', 'success')
    
    conn.close()
    return redirect(url_for('admin_solicitacoes_senha'))

@app.route('/admin/rejeitar-solicitacao/<int:id>', methods=['POST'])
@admin_required
def admin_rejeitar_solicitacao(id):
    """Rejeita uma solicitação de redefinição de senha"""
    conn = get_db_connection()
    conn.execute('UPDATE solicitacoes_senha SET status = "rejeitado" WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Solicitação rejeitada com sucesso!', 'success')
    return redirect(url_for('admin_solicitacoes_senha'))

@app.route('/admin/painel')
@admin_required
def admin_painel():
    """Painel principal do administrador (versão corrigida)"""
    # Obtém a conexão com o banco de dados
    conn = get_db_connection()
    
    # Lista de usuários
    usuarios = conn.execute('SELECT id, nome, status, admin FROM usuarios ORDER BY id').fetchall()
    
    # Fecha a conexão
    conn.close()
    
    # Renderiza o template com os dados
    return render_template('admin_painel.html', usuarios=usuarios)

@app.route('/')
def index():
    """Página inicial com dashboard"""
    conn = get_db_connection()
    componentes = conn.execute('SELECT * FROM componentes').fetchall()
    produtos_count = conn.execute('SELECT COUNT(*) as total FROM produtos').fetchone()
    
    # Busca as últimas 5 produções
    producoes_rows = conn.execute('''
        SELECT p.id, pr.nome as produto, pr.descricao as cliente, p.quantidade, p.data, p.status 
        FROM producoes p
        JOIN produtos pr ON p.produto_id = pr.id
        ORDER BY p.data DESC
        LIMIT 5
    ''').fetchall()
    
    # Formatar datas manualmente
    producoes = []
    for p in producoes_rows:
        producao = dict(p)
        
        # Formata a data diretamente aqui, aplicando o ajuste de fuso horário
        if isinstance(producao['data'], str):
            try:
                # Converte para objeto datetime
                data = datetime.strptime(producao['data'], '%Y-%m-%d %H:%M:%S')
                # Ajusta para o fuso horário de São Paulo
                data_ajustada = data + timedelta(hours=0)  # Adiciona 3 horas
                # Formata a data ajustada
                producao['data_formatada'] = data_ajustada.strftime('%d/%m/%Y às %H:%Mh')
            except ValueError:
                producao['data_formatada'] = producao['data']
        
        producoes.append(producao)
    
    # Estatísticas básicas
    total_itens = len(componentes)
    total_produtos = produtos_count['total'] if produtos_count else 0
    
    # Contabiliza componentes com status "baixo" (< 300) ou "crítico" (< 100)
    # Usando os mesmos limiares definidos na componentes.html
    itens_baixo_estoque = sum(1 for item in componentes if item['quantidade'] < 300)
    
    conn.close()
    
    return render_template('index.html', 
                          total_itens=total_itens,
                          total_produtos=total_produtos,
                          itens_baixo_estoque=itens_baixo_estoque,
                          producoes=producoes)
    
@app.route('/componentes')
@login_required
def listar_componentes():
    """Lista todos os componentes com opção de busca por código ou nome"""
    # Obtém parâmetros de busca e filtro
    search_query = request.args.get('search', '')
    filtro = request.args.get('filtro', 'todos')
    ver_todos = request.args.get('ver_todos', 'false')
    ordem = request.args.get('ordem', 'asc')  # Nova opção para controlar a ordem (asc/desc)
    
    conn = get_db_connection()
    
    # Construir a consulta SQL de forma mais segura
    base_query = "SELECT * FROM componentes"
    conditions = []
    params = []
    
    # Adicionar condições de busca, se houver
    if search_query:
        conditions.append("(codigo LIKE ? OR UPPER(nome) LIKE UPPER(?))")
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")
    
    # Adicionar condições de filtro, se aplicável
    if filtro == 'critico':
        conditions.append("quantidade < 100")
    elif filtro == 'baixo':
        conditions.append("quantidade >= 100 AND quantidade < 300")
    elif filtro == 'normal':
        conditions.append("quantidade >= 300")
    
    # Determinar a ordenação dos resultados
    # Usando CAST para garantir ordenação numérica e não alfabética do código
    order_by = f"ORDER BY CAST(codigo AS INTEGER) {'DESC' if ordem == 'desc' else 'ASC'}"
    
    # Montar a consulta final
    if conditions:
        query = f"{base_query} WHERE {' AND '.join(conditions)} {order_by}"
    else:
        query = f"{base_query} {order_by}"
    
    print(f"DEBUG - Query: {query}")  # Para debugar
    print(f"DEBUG - Params: {params}")  # Para debugar
    
    try:
        componentes = conn.execute(query, params).fetchall()
    except Exception as e:
        # Manipulação de erro com fallback para consulta simples
        print(f"ERRO SQL: {str(e)}")
        componentes = conn.execute(f"SELECT * FROM componentes {order_by}").fetchall()
    
    conn.close()
    
    return render_template('componentes.html', 
                          componentes=componentes, 
                          search_query=search_query,
                          ver_todos=ver_todos,
                          ordem=ordem,
                          filtro=filtro)
    
@app.route('/componentes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_componente():
    """Adiciona um novo componente"""
    print("\n\n==== INÍCIO DE ADICIONAR_COMPONENTE ====")
    print(f"Método da requisição: {request.method}")
    
    if request.method == 'POST':
        print(f"Dados do formulário: {dict(request.form)}")
        
        try:
            codigo = request.form['codigo']
            nome = request.form['nome']
            quantidade = int(request.form['quantidade'])
            
            print(f"Dados extraídos: Código={codigo}, Nome={nome}, Quantidade={quantidade}")
            
            # Garante que a primeira letra do nome seja maiúscula
            if nome:
                nome = nome[0].upper() + nome[1:] if len(nome) > 1 else nome.upper()
                print(f"Nome após capitalização: {nome}")
            
            conn = get_db_connection()
            print("Conexão com banco de dados estabelecida")
            
            # Verifica se o código já existe
            existente_codigo = conn.execute('SELECT * FROM componentes WHERE codigo = ?', (codigo,)).fetchone()
            existente_nome = conn.execute('SELECT * FROM componentes WHERE UPPER(nome) = UPPER(?)', (nome,)).fetchone()
            
            print(f"Verificação de código existente: {existente_codigo is not None}")
            print(f"Verificação de nome existente: {existente_nome is not None}")
            
            if existente_codigo:
                print("Erro: Código já existe")
                flash('Erro: Componente com este código já existe!', 'danger')
                conn.close()
                return render_template('adicionar.html')
            elif existente_nome:
                print("Erro: Nome já existe")
                flash('Erro: Componente com este nome já existe!', 'danger')
                conn.close()
                return render_template('adicionar.html')
            else:
                print("Inserindo novo componente no banco de dados")
                # Insere o novo componente
                conn.execute('INSERT INTO componentes (codigo, nome, quantidade) VALUES (?, ?, ?)',
                            (codigo, nome, quantidade))
                
                # Registra a transação se a quantidade for maior que zero
                if quantidade > 0:
                    print(f"Registrando transação de entrada para {quantidade} unidades")
                    try:
                        # Tenta primeiro com a coluna origem
                        conn.execute('''
                            INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id, origem) 
                            VALUES (?, ?, ?, datetime("now", "localtime"), ?, ?)
                        ''', (codigo, 'entrada', quantidade, session.get('user_id'), 'criacao_componente'))
                        print("Transação registrada com origem")
                    except sqlite3.OperationalError as e:
                        print(f"Erro ao registrar transação com origem: {str(e)}")
                        # Se falhar, tenta sem a coluna origem
                        conn.execute('''
                            INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id) 
                            VALUES (?, ?, ?, datetime("now", "localtime"), ?)
                        ''', (codigo, 'entrada', quantidade, session.get('user_id')))
                        print("Transação registrada sem origem")
                
                print("Fazendo commit das alterações")
                conn.commit()
                
                # Verifica se o componente foi realmente inserido
                check = conn.execute('SELECT * FROM componentes WHERE codigo = ?', (codigo,)).fetchone()
                if check:
                    print(f"Componente encontrado após inserção: {dict(check)}")
                else:
                    print("ALERTA: Componente não encontrado após inserção!")
                
                conn.close()
                print("Conexão com banco de dados fechada")
                
                flash('Componente adicionado com sucesso!', 'success')
                print("Redirecionando para listar_componentes")
                print("==== FIM DE ADICIONAR_COMPONENTE ====\n\n")
                return redirect(url_for('listar_componentes'))
        except Exception as e:
            print(f"ERRO CRÍTICO: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Erro ao adicionar componente: {str(e)}', 'danger')
            return render_template('adicionar.html')
    
    print("Renderizando template adicionar.html (método GET)")
    print("==== FIM DE ADICIONAR_COMPONENTE ====\n\n")
    return render_template('adicionar.html')

@app.route('/componentes/editar/<codigo>', methods=['GET', 'POST'])
@login_required
def editar_componente(codigo):
    """Edita um componente existente"""
    conn = get_db_connection()
    componente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                             (codigo,)).fetchone()
    
    if componente is None:
        conn.close()
        flash('Componente não encontrado!', 'danger')
        return redirect(url_for('listar_componentes'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        quantidade = int(request.form['quantidade'])
        novo_codigo = request.form.get('novo_codigo', codigo)
        confirmar_alteracao = request.form.get('confirmar_alteracao', 'false')
        confirmar_quantidade = request.form.get('confirmar_quantidade', 'false')
        
        # Garante que a primeira letra do nome seja maiúscula
        if nome:
            nome = nome[0].upper() + nome[1:] if len(nome) > 1 else nome.upper()
        
        # Verifica se o código foi alterado
        codigo_alterado = novo_codigo != codigo
        # Verifica se a quantidade foi alterada
        quantidade_alterada = quantidade != componente['quantidade']
        
        # Se a quantidade foi alterada e não foi confirmada, mostra a tela de confirmação
        if quantidade_alterada and confirmar_quantidade != 'true' and confirmar_alteracao != 'true':
            return render_template('editar.html', 
                                  componente=componente, 
                                  mostrar_confirmacao_quantidade=True, 
                                  novo_codigo=novo_codigo,
                                  nome=nome,
                                  quantidade=quantidade)
        
        # Verifica se o código foi alterado
        if codigo_alterado:
            # Verifica se o novo código é numérico
            if not novo_codigo.isdigit():
                flash('Erro: O código do componente deve ser numérico!', 'danger')
                return render_template('editar.html', componente=componente, mostrar_confirmacao=True, novo_codigo=novo_codigo)
            
            # Verifica se o código já existe
            existente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', (novo_codigo,)).fetchone()
            if existente:
                flash('Erro: Já existe um componente com este código!', 'danger')
                return render_template('editar.html', componente=componente)
            
            # Se a alteração de código não foi confirmada, mostra a tela de confirmação
            if confirmar_alteracao != 'true':
                return render_template('editar.html', 
                                      componente=componente, 
                                      mostrar_confirmacao=True, 
                                      novo_codigo=novo_codigo,
                                      nome=nome,
                                      quantidade=quantidade)
            
            # Atualiza o componente com o novo código
            conn.execute('''
                UPDATE componentes 
                SET codigo = ?, nome = ?, quantidade = ? 
                WHERE codigo = ?
            ''', (novo_codigo, nome, quantidade, codigo))
            
            # Atualiza as referências nas tabelas relacionadas
            conn.execute('UPDATE componentes_produto SET codigo_componente = ? WHERE codigo_componente = ?', 
                        (novo_codigo, codigo))
            conn.execute('UPDATE transacoes SET codigo_componente = ? WHERE codigo_componente = ?', 
                        (novo_codigo, codigo))
            
            # Não registramos mais alterações de quantidade como transações na edição de componentes
            
            codigo_atualizado = novo_codigo
        else:
            # Apenas atualiza o nome e quantidade
            conn.execute('UPDATE componentes SET nome = ?, quantidade = ? WHERE codigo = ?',
                        (nome, quantidade, codigo))
            
            # Não registramos mais alterações de quantidade como transações na edição de componentes
            
            codigo_atualizado = codigo
        
        conn.commit()
        conn.close()
        
        flash('Componente atualizado com sucesso!', 'success')
        return redirect(url_for('listar_componentes'))
    
    conn.close()
    return render_template('editar.html', componente=componente)

@app.route('/componentes/excluir/<codigo>', methods=['POST'])
@login_required
def excluir_componente(codigo):
    """Exclui um componente"""
    conn = get_db_connection()
    conn.execute('DELETE FROM componentes WHERE codigo = ?', (codigo,))
    conn.commit()
    conn.close()
    
    flash('Componente excluído com sucesso!', 'success')
    return redirect(url_for('listar_componentes'))

@app.route('/excluir_componente/<codigo>')
@login_required
def redirecionar_exclusao_componente(codigo):
    """Redireciona para a exclusão do componente"""
    conn = get_db_connection()
    conn.execute('DELETE FROM componentes WHERE codigo = ?', (codigo,))
    conn.commit()
    conn.close()
    
    flash('Componente excluído com sucesso!', 'success')
    return redirect(url_for('listar_componentes'))

@app.route('/registrar_entrada', methods=['GET', 'POST'])
@login_required
def registrar_entrada():
    """Registra entrada de estoque para um componente individual"""
    if request.method == 'POST':
        codigo = request.form['codigo']
        quantidade = int(request.form['quantidade'])
        
        conn = get_db_connection()
        componente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                                (codigo,)).fetchone()
        
        if componente is None:
            flash('Componente não encontrado!', 'danger')
        else:
            nova_quantidade = componente['quantidade'] + quantidade
            conn.execute('UPDATE componentes SET quantidade = ? WHERE codigo = ?',
                        (nova_quantidade, codigo))
            
            # Registra a transação com o ID do usuário e origem
            try:
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id, origem) 
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?, ?)
                ''', (codigo, 'entrada', quantidade, session.get('user_id'), 'entrada_manual'))
            except sqlite3.OperationalError:
                # Fallback se a coluna origem não for acessível
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id) 
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?)
                ''', (codigo, 'entrada', quantidade, session.get('user_id')))
            
            conn.commit()
            flash(f'Entrada registrada. Novo total: {nova_quantidade}', 'success')
            return redirect(url_for('listar_componentes'))
        
        conn.close()
    
    # Para método GET, apenas renderiza o template sem passar a lista de componentes
    return render_template('entrada.html')

@app.route('/transacoes/entrada_produto', methods=['POST'])
@login_required
def registrar_entrada_produto():
    """Registra entrada de estoque para todos os componentes de um produto"""
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = int(request.form['quantidade'])
        
        conn = get_db_connection()
        
        # Busca os componentes do produto
        componentes = conn.execute('''
            SELECT cp.quantidade, c.codigo, c.nome, c.quantidade as estoque
            FROM componentes_produto cp
            JOIN componentes c ON cp.codigo_componente = c.codigo
            WHERE cp.produto_id = ?
        ''', (produto_id,)).fetchall()
        
        # Atualiza cada componente
        for componente in componentes:
            qtd_entrada = componente['quantidade'] * quantidade
            nova_quantidade = componente['estoque'] + qtd_entrada
            
            conn.execute('UPDATE componentes SET quantidade = ? WHERE codigo = ?',
                        (nova_quantidade, componente['codigo']))
            
            # Registra a transação com o ID do usuário
            try:
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id, origem)
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?, ?)
                ''', (componente['codigo'], 'entrada', qtd_entrada, session.get('user_id'), 'entrada_produto'))
            except sqlite3.OperationalError:
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id)
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?)
                ''', (componente['codigo'], 'entrada', qtd_entrada, session.get('user_id')))
        
        conn.commit()
        conn.close()
        
        flash('Entrada de componentes registrada com sucesso!', 'success')
        return redirect(url_for('listar_componentes'))
    
    return redirect(url_for('calcular_producao'))

@app.route('/transacoes/saida', methods=['GET', 'POST'])
@login_required
def registrar_saida():
    """Registra saída de estoque para um componente individual"""
    if request.method == 'POST':
        codigo = request.form['codigo']
        quantidade = int(request.form['quantidade'])
        
        conn = get_db_connection()
        componente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                                 (codigo,)).fetchone()
        
        if componente is None:
            flash('Componente não encontrado!', 'danger')
        elif componente['quantidade'] < quantidade:
            flash('Quantidade insuficiente em estoque!', 'danger')
        else:
            nova_quantidade = componente['quantidade'] - quantidade
            conn.execute('UPDATE componentes SET quantidade = ? WHERE codigo = ?',
                        (nova_quantidade, codigo))
            
            # Registra a transação com o ID do usuário e origem
            try:
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id, origem) 
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?, ?)
                ''', (codigo, 'saida', quantidade, session.get('user_id'), 'saida_manual'))
            except sqlite3.OperationalError:
                # Fallback para bancos sem a coluna origem
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id) 
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?)
                ''', (codigo, 'saida', quantidade, session.get('user_id')))
            
            conn.commit()
            flash(f'Saída registrada. Novo total: {nova_quantidade}', 'success')
            return redirect(url_for('listar_componentes'))
        
        conn.close()
    
    # Para método GET, apenas renderiza o template sem passar a lista de componentes
    return render_template('saida.html')

@app.route('/transacoes/saida_produto', methods=['POST'])
@login_required
def registrar_saida_produto():
    """Registra saída de estoque para todos os componentes de um produto"""
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = int(request.form['quantidade'])
        
        conn = get_db_connection()
        
        # Busca o produto
        produto_row = conn.execute('SELECT * FROM produtos WHERE id = ?', (produto_id,)).fetchone()
        
        if produto_row is None:
            conn.close()
            flash('Produto não encontrado!', 'danger')
            return redirect(url_for('calcular_producao'))
        
        # Busca os componentes do produto
        componentes = conn.execute('''
            SELECT cp.quantidade, c.codigo, c.nome, c.quantidade as estoque
            FROM componentes_produto cp
            JOIN componentes c ON cp.codigo_componente = c.codigo
            WHERE cp.produto_id = ?
        ''', (produto_id,)).fetchall()
        
        # Verifica se há estoque suficiente para todos os componentes
        componentes_insuficientes = []
        for componente in componentes:
            qtd_necessaria = componente['quantidade'] * quantidade
            if componente['estoque'] < qtd_necessaria:
                componentes_insuficientes.append({
                    'codigo': componente['codigo'],
                    'nome': componente['nome'],
                    'necessario': qtd_necessaria,
                    'disponivel': componente['estoque']
                })
        
        if componentes_insuficientes:
            conn.close()
            flash('Não há estoque suficiente para alguns componentes!', 'danger')
            return redirect(url_for('calcular_producao'))
        
        # Debita a quantidade de cada componente do estoque
        for componente in componentes:
            qtd_necessaria = componente['quantidade'] * quantidade
            nova_quantidade = componente['estoque'] - qtd_necessaria
            
            # Atualiza o estoque
            conn.execute('UPDATE componentes SET quantidade = ? WHERE codigo = ?',
                        (nova_quantidade, componente['codigo']))
            
            # Registra a transação com o ID do usuário
            try:
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id, origem) 
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?, ?)
                ''', (componente['codigo'], 'saida', qtd_necessaria, session.get('user_id'), 'saida_produto'))
            except sqlite3.OperationalError:
                conn.execute('''
                    INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id) 
                    VALUES (?, ?, ?, datetime("now", "localtime"), ?)
                ''', (componente['codigo'], 'saida', qtd_necessaria, session.get('user_id')))
        
        # Registra a produção com o ID do usuário
        conn.execute('''
            INSERT INTO producoes (produto_id, quantidade, data, usuario_id)
            VALUES (?, ?, datetime('now', 'localtime'), ?)
        ''', (produto_id, quantidade, session.get('user_id')))
        
        conn.commit()
        conn.close()
        
        flash(f'Produção de {quantidade} unidade(s) registrada com sucesso!', 'success')
        return redirect(url_for('listar_producoes'))
    
    return redirect(url_for('calcular_producao'))

@app.route('/transacoes')
@login_required
def listar_transacoes():
    """Lista o histórico de transações - apenas entradas/saídas manuais e produções"""
    # Obter o parâmetro ver_todos da query string
    ver_todos = request.args.get('ver_todos', 'false')
    
    conn = get_db_connection()
    
    # Usar a consulta SQL original
    try:
        rows = conn.execute('''
            SELECT t.id, t.codigo_componente, c.nome, t.tipo, t.quantidade, t.data, 
                   u.nome as usuario_nome
            FROM transacoes t
            JOIN componentes c ON t.codigo_componente = c.codigo
            LEFT JOIN usuarios u ON t.usuario_id = u.id
            WHERE t.origem = 'entrada_manual' OR t.origem = 'saida_manual' OR t.origem = 'saida_produto'
            ORDER BY t.data DESC
        ''').fetchall()
    except sqlite3.OperationalError:
        rows = conn.execute('''
            SELECT t.id, t.codigo_componente, c.nome, t.tipo, t.quantidade, t.data, 
                   u.nome as usuario_nome
            FROM transacoes t
            JOIN componentes c ON t.codigo_componente = c.codigo
            LEFT JOIN usuarios u ON t.usuario_id = u.id
            WHERE 
                -- Entradas manuais: uma transação de entrada por data e usuário
                (t.tipo = 'entrada' AND t.id IN (
                    SELECT MIN(t2.id) FROM transacoes t2 
                    WHERE t2.tipo = 'entrada' AND t2.data = t.data 
                          AND (t2.usuario_id = t.usuario_id OR (t2.usuario_id IS NULL AND t.usuario_id IS NULL))
                    GROUP BY t2.data, t2.usuario_id
                    HAVING COUNT(*) = 1
                ))
                OR
                -- Saídas manuais: uma transação de saída por data e usuário
                (t.tipo = 'saida' AND t.id IN (
                    SELECT MIN(t3.id) FROM transacoes t3 
                    WHERE t3.tipo = 'saida' AND t3.data = t.data 
                          AND (t3.usuario_id = t.usuario_id OR (t3.usuario_id IS NULL AND t.usuario_id IS NULL))
                    GROUP BY t3.data, t3.usuario_id
                    HAVING COUNT(*) = 1
                ))
                OR
                -- Saídas de produção: múltiplas saídas por data e usuário
                (t.tipo = 'saida' AND EXISTS (
                    SELECT 1 FROM producoes p
                    WHERE DATE(p.data) = DATE(t.data)
                    AND (p.usuario_id = t.usuario_id OR (p.usuario_id IS NULL AND t.usuario_id IS NULL))
                ))
            ORDER BY t.data DESC
        ''').fetchall()
    
    # Converte objetos Row para dicionários
    transacoes = []
    for row in rows:
        # Converte para dicionário
        transacao = dict(row)
        
        # Formata a data diretamente aqui, aplicando o ajuste de fuso horário
        if isinstance(transacao['data'], str):
            try:
                # Converte para objeto datetime
                data = datetime.strptime(transacao['data'], '%Y-%m-%d %H:%M:%S')
                # Ajusta para o fuso horário de São Paulo
                data_ajustada = data + timedelta(hours=0)  # Adiciona 3 horas
                # Formata a data ajustada
                transacao['data_formatada'] = data_ajustada.strftime('%d/%m/%Y às %H:%Mh')
            except ValueError:
                transacao['data_formatada'] = transacao['data']
        
        transacoes.append(transacao)
    
    conn.close()
    
    return render_template('transacoes.html', transacoes=transacoes, ver_todos=ver_todos)

@app.route('/producoes')
@login_required
def listar_producoes():
    """Lista o histórico de produções"""
    # Obter o parâmetro ver_todos da query string
    ver_todos = request.args.get('ver_todos', 'false')
    
    conn = get_db_connection()
    producoes = conn.execute('''
        SELECT p.id, pr.nome as produto, pr.descricao as cliente, p.quantidade, p.data, p.status,
               u.nome as usuario_nome
        FROM producoes p
        JOIN produtos pr ON p.produto_id = pr.id
        LEFT JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY p.data DESC
    ''').fetchall()
    
    # Buscar a lista de produtos para o modal de cálculo
    produtos = conn.execute('SELECT id, nome FROM produtos ORDER BY nome').fetchall()
    
    # Formatar datas manualmente
    producoes_formatadas = []
    for p in producoes:
        producao = dict(p)
        
        # Formata a data diretamente aqui, aplicando o ajuste de fuso horário
        if isinstance(producao['data'], str):
            try:
                # Converte para objeto datetime
                data = datetime.strptime(producao['data'], '%Y-%m-%d %H:%M:%S')
                # Ajusta para o fuso horário de São Paulo
                data_ajustada = data + timedelta(hours=0)  # Adiciona 3 horas
                # Formata a data ajustada
                producao['data_formatada'] = data_ajustada.strftime('%d/%m/%Y às %H:%Mh')
            except ValueError:
                producao['data_formatada'] = producao['data']
        
        producoes_formatadas.append(producao)
    
    conn.close()
    
    return render_template('producoes.html', producoes=producoes_formatadas, ver_todos=ver_todos, produtos=produtos)

@app.route('/produtos')
@login_required
def listar_produtos():
    """Lista todos os produtos com opção de busca por nome e cliente"""
    search_query = request.args.get('search', '')
    cliente_query = request.args.get('cliente', '')
    ver_todos = request.args.get('ver_todos', 'false')
    
    conn = get_db_connection()
    
    # Base da consulta
    query = 'SELECT * FROM produtos'
    params = []
    
    # Adiciona condições de busca conforme os parâmetros fornecidos
    conditions = []
    
    if search_query:
        conditions.append('UPPER(nome) LIKE UPPER(?)')
        params.append('%' + search_query + '%')
    
    if cliente_query:
        conditions.append('UPPER(descricao) LIKE UPPER(?)')
        params.append('%' + cliente_query + '%')
    
    # Combina as condições se houver
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    
    # Ordena por nome
    query += ' ORDER BY nome'
    
    # Executa a consulta
    produtos_rows = conn.execute(query, params).fetchall()
    
    # Converte os objetos Row para dicionários e adiciona os componentes
    produtos = []
    for produto_row in produtos_rows:
        # Converte para dicionário
        produto = dict(produto_row)
        
        # Busca os componentes do produto
        componentes_rows = conn.execute('''
            SELECT cp.quantidade, c.codigo, c.nome
            FROM componentes_produto cp
            JOIN componentes c ON cp.codigo_componente = c.codigo
            WHERE cp.produto_id = ?
        ''', (produto['id'],)).fetchall()
        
        # Converte componentes para dicionários
        componentes = []
        for componente_row in componentes_rows:
            componentes.append({
                'quantidade': componente_row['quantidade'],
                'codigo': componente_row['codigo'],
                'nome': componente_row['nome']
            })
        
        # Adiciona os componentes ao dicionário
        produto['componentes'] = componentes
        produtos.append(produto)
    
    # Busca todos os componentes para as modais de adição e edição
    componentes_rows = conn.execute('SELECT codigo, nome FROM componentes ORDER BY nome').fetchall()
    
    # Converte componentes para lista de dicionários para a serialização JSON
    componentes = []
    for componente in componentes_rows:
        componentes.append({
            'codigo': componente['codigo'],
            'nome': componente['nome']
        })
    
    # Busca todos os clientes únicos para os dropdowns
    clientes_rows = conn.execute('SELECT DISTINCT descricao FROM produtos WHERE descricao IS NOT NULL AND descricao != "" ORDER BY descricao').fetchall()
    
    # Converte para lista simples
    clientes = [cliente['descricao'] for cliente in clientes_rows if cliente['descricao']]
    
    conn.close()
    
    return render_template('produtos.html', 
                          produtos=produtos,
                          componentes=componentes,
                          clientes=clientes,
                          search_query=search_query,
                          cliente_query=cliente_query,
                          ver_todos=ver_todos)

@app.route('/produtos/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    """Adiciona um novo produto"""
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        componentes_json = request.form['componentes_json']
        
        # Garante que a primeira letra do nome seja maiúscula
        if nome:
            nome = nome[0].upper() + nome[1:] if len(nome) > 1 else nome.upper()
        
        try:
            componentes_lista = json.loads(componentes_json)
            
            conn = get_db_connection()
            
            # Verifica se já existe um produto com o mesmo nome
            produto_existente = conn.execute('SELECT id FROM produtos WHERE UPPER(nome) = UPPER(?)', (nome,)).fetchone()
            
            if produto_existente:
                flash(f'Já existe um produto com o nome "{nome}". Por favor, escolha outro nome.', 'danger')
                return redirect(url_for('listar_produtos'))
            
            # Insere o produto
            cursor = conn.execute('INSERT INTO produtos (nome, descricao) VALUES (?, ?)',
                        (nome, descricao))
            produto_id = cursor.lastrowid
            
            # Insere os componentes do produto
            for componente in componentes_lista:
                codigo = componente['codigo']
                quantidade = int(componente['quantidade'])
                
                conn.execute('''
                    INSERT INTO componentes_produto (produto_id, codigo_componente, quantidade)
                    VALUES (?, ?, ?)
                ''', (produto_id, codigo, quantidade))
            
            conn.commit()
            conn.close()
            
            flash('Produto adicionado com sucesso!', 'success')
            return redirect(url_for('listar_produtos'))
            
        except Exception as e:
            flash(f'Erro ao adicionar produto: {str(e)}', 'danger')
            return redirect(url_for('listar_produtos'))
    
    # Se for GET, simplesmente redirecionar para a lista de produtos (agora usamos o modal)
    return redirect(url_for('listar_produtos'))

@app.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    """Edita um produto existente"""
    conn = get_db_connection()
    produto_row = conn.execute('SELECT * FROM produtos WHERE id = ?', (id,)).fetchone()
    
    if produto_row is None:
        conn.close()
        flash('Produto não encontrado!', 'danger')
        return redirect(url_for('listar_produtos'))
    
    # Converte para dicionário
    produto = dict(produto_row)
    
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        componentes_json = request.form['componentes_json']
        
        # Garante que a primeira letra do nome seja maiúscula
        if nome:
            nome = nome[0].upper() + nome[1:] if len(nome) > 1 else nome.upper()
        
        try:
            componentes_lista = json.loads(componentes_json)
            
            # Verifica se já existe outro produto com o mesmo nome
            produto_existente = conn.execute('SELECT id FROM produtos WHERE UPPER(nome) = UPPER(?) AND id != ?', (nome, id)).fetchone()
            
            if produto_existente:
                flash(f'Já existe um produto com o nome "{nome}". Por favor, escolha outro nome.', 'danger')
                # Buscar componentes para manter a página de edição funcionando corretamente após o erro
                componentes_produto = conn.execute('''
                    SELECT cp.codigo_componente, cp.quantidade, c.nome
                    FROM componentes_produto cp
                    JOIN componentes c ON cp.codigo_componente = c.codigo
                    WHERE cp.produto_id = ?
                ''', (id,)).fetchall()
                componentes = conn.execute('SELECT codigo, nome FROM componentes ORDER BY nome').fetchall()
                conn.close()
                return render_template('editar_produto.html', 
                                    produto=produto, 
                                    componentes_produto=componentes_produto,
                                    componentes=componentes)
            
            # Atualiza o produto
            conn.execute('UPDATE produtos SET nome = ?, descricao = ? WHERE id = ?',
                        (nome, descricao, id))
            
            # Remove os componentes antigos
            conn.execute('DELETE FROM componentes_produto WHERE produto_id = ?', (id,))
            
            # Insere os novos componentes
            for componente in componentes_lista:
                codigo = componente['codigo']
                quantidade = int(componente['quantidade'])
                
                conn.execute('''
                    INSERT INTO componentes_produto (produto_id, codigo_componente, quantidade)
                    VALUES (?, ?, ?)
                ''', (id, codigo, quantidade))
            
            conn.commit()
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('listar_produtos'))
            
        except Exception as e:
            flash(f'Erro ao atualizar produto: {str(e)}', 'danger')
    
    # Busca os componentes do produto
    componentes_produto = conn.execute('''
        SELECT cp.codigo_componente, cp.quantidade, c.nome
        FROM componentes_produto cp
        JOIN componentes c ON cp.codigo_componente = c.codigo
        WHERE cp.produto_id = ?
    ''', (id,)).fetchall()
    
    # Busca todos os componentes disponíveis
    componentes = conn.execute('SELECT codigo, nome FROM componentes ORDER BY nome').fetchall()
    
    conn.close()
    
    return render_template('editar_produto.html', 
                          produto=produto, 
                          componentes_produto=componentes_produto,
                          componentes=componentes)

@app.route('/produtos/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_produto(id):
    """Exclui um produto"""
    conn = get_db_connection()
    
    # Remove os componentes do produto
    conn.execute('DELETE FROM componentes_produto WHERE produto_id = ?', (id,))
    
    # Remove o produto
    conn.execute('DELETE FROM produtos WHERE id = ?', (id,))
    
    conn.commit()
    conn.close()
    
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('listar_produtos'))

@app.route('/produtos/calcular', methods=['GET', 'POST'])
@login_required
def calcular_producao():
    """Calcula os componentes necessários para uma quantidade de produtos"""
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        quantidade = int(request.form['quantidade'])
        
        conn = get_db_connection()
        
        # Busca o produto
        produto_row = conn.execute('SELECT * FROM produtos WHERE id = ?', (produto_id,)).fetchone()
        
        if produto_row is None:
            conn.close()
            flash('Produto não encontrado!', 'danger')
            return redirect(url_for('calcular_producao'))
        
        # Converte para dicionário
        produto = dict(produto_row)
        
        # Busca os componentes do produto
        componentes = conn.execute('''
            SELECT cp.quantidade, c.codigo, c.nome, c.quantidade as estoque
            FROM componentes_produto cp
            JOIN componentes c ON cp.codigo_componente = c.codigo
            WHERE cp.produto_id = ?
        ''', (produto_id,)).fetchall()
        
        # Calcula a quantidade necessária de cada componente
        componentes_necessarios = []
        indisponiveis = 0
        
        for componente in componentes:
            qtd_necessaria = componente['quantidade'] * quantidade
            disponivel = componente['estoque'] >= qtd_necessaria
            
            if not disponivel:
                indisponiveis += 1
                
            componentes_necessarios.append({
                'codigo': componente['codigo'],
                'nome': componente['nome'],
                'quantidade_unitaria': componente['quantidade'],
                'quantidade_total': qtd_necessaria,
                'estoque': componente['estoque'],
                'disponivel': disponivel
            })
        
        conn.close()
        
        return render_template('resultado_calculo.html', 
                              produto=produto, 
                              quantidade=quantidade,
                              componentes=componentes_necessarios,
                              indisponiveis=indisponiveis)
    
    conn = get_db_connection()
    produtos = conn.execute('SELECT id, nome FROM produtos ORDER BY nome').fetchall()
    conn.close()
    
    return render_template('calcular_producao.html', produtos=produtos)

@app.route('/api/check_code')
@login_required
def check_code():
    """Verifica disponibilidade de código"""
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Parâmetro code é obrigatório'}), 400
    
    conn = get_db_connection()
    existente = conn.execute('SELECT codigo FROM componentes WHERE codigo = ?', (code,)).fetchone()
    conn.close()
    
    return jsonify({'available': not existente})

@app.route('/api/check_name')
@login_required
def check_name():
    """Verifica disponibilidade de nome"""
    name = request.args.get('name', '')
    if not name:
        return jsonify({'error': 'Parâmetro name é obrigatório'}), 400
    
    conn = get_db_connection()
    
    # Normaliza o nome para comparação: remove espaços extras, converte para lowercase
    # e remove caracteres não alfanuméricos
    name_normalized = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    
    # Verifica se já existe um componente com nome similar
    componentes = conn.execute('SELECT nome FROM componentes').fetchall()
    conn.close()
    
    # Compara normalizando cada nome do banco
    for componente in componentes:
        componente_nome = componente['nome']
        componente_normalizado = re.sub(r'[^a-zA-Z0-9]', '', componente_nome.lower())
        
        if componente_normalizado == name_normalized:
            return jsonify({'available': False, 'message': f'Já existe um componente com nome similar: {componente_nome}'})
    
    return jsonify({'available': True})

@app.route('/api/componentes')
@login_required
def api_componentes():
    """API para buscar componentes"""
    termo = request.args.get('termo', '').strip()
    
    conn = get_db_connection()
    
    if termo:
        # Se foi informado um termo, filtra os resultados
        componentes = conn.execute(
            'SELECT codigo, nome, quantidade FROM componentes WHERE codigo LIKE ? OR UPPER(nome) LIKE UPPER(?) ORDER BY nome', 
            (f'%{termo}%', f'%{termo}%')
        ).fetchall()
    else:
        # Se não foi informado um termo, retorna todos os componentes
        componentes = conn.execute('SELECT codigo, nome, quantidade FROM componentes ORDER BY nome').fetchall()
    
    conn.close()
    
    # Converte para lista de dicionários
    resultado = [dict(componente) for componente in componentes]
    
    return jsonify(resultado)

@app.route('/api/produto/<int:produto_id>/componentes')
@login_required
def api_produto_componentes(produto_id):
    """API para buscar componentes de um produto específico"""
    conn = get_db_connection()
    
    # Busca os componentes do produto
    componentes = conn.execute('''
        SELECT cp.codigo_componente as codigo, cp.quantidade, c.nome
        FROM componentes_produto cp
        JOIN componentes c ON cp.codigo_componente = c.codigo
        WHERE cp.produto_id = ?
    ''', (produto_id,)).fetchall()
    
    conn.close()
    
    # Converte para lista de dicionários
    resultado = [dict(componente) for componente in componentes]
    
    return jsonify(resultado)

# Inicialização do arquivo CSS para tabelas com rolagem
@app.route('/static/css/table-styles.css')
def table_styles_css():
    """Serve o arquivo CSS personalizado para tabelas com rolagem"""
    return """
    /* Estilização para tabelas com scroll */
    .table-responsive {
        max-height: 350px;
        overflow-y: auto;
        margin-bottom: 1rem;
        border-radius: 0.25rem;
        box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    }

    /* Estilização para cabeçalhos fixos */
    .table-responsive thead {
        position: sticky;
        top: 0;
        z-index: 1;
    }

    .table-responsive thead th {
        background-color: #f8f9fa;
        border-bottom: 2px solid #dee2e6;
        box-shadow: 0 1px 0 #dee2e6;
    }

    /* Efeito de hover nas linhas */
    .table-hover tbody tr:hover {
        background-color: rgba(0, 123, 255, 0.05);
        transition: background-color 0.2s ease;
    }

    /* Botão de ver todos */
    .btn-ver-todos {
        margin-top: 0.5rem;
        transition: all 0.2s ease;
    }

    .btn-ver-todos:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }

    /* Customização da barra de rolagem */
    .table-responsive::-webkit-scrollbar {
        width: 8px;
    }

    .table-responsive::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    .table-responsive::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }

    .table-responsive::-webkit-scrollbar-thumb:hover {
        background: #a1a1a1;
    }
    """, {'Content-Type': 'text/css'}

# Inicialização do arquivo JavaScript para animações em tabelas
@app.route('/static/js/table-animations.js')
def table_animations_js():
    """Serve o arquivo JavaScript personalizado para animações em tabelas"""
    return """
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
    """, {'Content-Type': 'application/javascript'}

@app.route('/avaliacao-fornecedores')
@login_required
def avaliacao_fornecedores():
    """Página principal de avaliação de fornecedores"""
    # Obter parâmetros da URL para saber qual tab deve estar ativa
    tab = request.args.get('tab', 'recebimento')
    
    # Buscar dados necessários
    fornecedores = get_fornecedores()
    recebimentos = get_recebimentos()
    
    # Calcular avaliações
    avaliacoes = calcular_avaliacoes()
    
    # Calcular ranking
    ranking_fornecedores = calcular_ranking_fornecedores()
    
    # Calcular métricas para o dashboard de análise
    total_fornecedores = len(fornecedores)
    fornecedores_acima_meta = len([r for r in ranking_fornecedores if r['scoreFinal'] >= 85])
    fornecedores_abaixo_meta = total_fornecedores - fornecedores_acima_meta
    
    # Calcular média geral de performance
    media_geral_performance = 0
    if total_fornecedores > 0:
        media_geral_performance = sum(a['scoreFinal'] for a in avaliacoes) / total_fornecedores
    
    # Gerar análise de tendências
    analise_tendencias = gerar_analise_tendencias()
    
    return render_template('avaliacao_fornecedores.html',
                          fornecedores=fornecedores,
                          recebimentos=recebimentos,
                          avaliacoes=avaliacoes,
                          total_recebimentos=len(recebimentos),
                          ranking_fornecedores=ranking_fornecedores,
                          total_fornecedores=total_fornecedores,
                          fornecedores_acima_meta=fornecedores_acima_meta,
                          fornecedores_abaixo_meta=fornecedores_abaixo_meta,
                          media_geral_performance=round(media_geral_performance, 1),
                          analise_tendencias=analise_tendencias)

@app.route('/sistema-avaliacao-fornecedores')
@login_required
def sistema_avaliacao_fornecedores():
    """Página do sistema de avaliação de fornecedores"""
    # Esta é uma nova rota para a página do sistema de avaliação
    
    return render_template('sistema_avaliacao_fornecedores.html')

@app.route('/avaliacao-fornecedores/adicionar-fornecedor', methods=['POST'])
@login_required
def adicionar_fornecedor():
    """Adicionar um novo fornecedor"""
    if request.method == 'POST':
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        email = request.form.get('email', '')
        telefone = request.form.get('telefone', '')
        
        conn = get_db_connection()
        
        # Verificar se já existe um fornecedor com este nome ou CNPJ
        existente_nome = conn.execute('SELECT * FROM fornecedores WHERE nome = ?', (nome,)).fetchone()
        existente_cnpj = conn.execute('SELECT * FROM fornecedores WHERE cnpj = ?', (cnpj,)).fetchone()
        
        if existente_nome:
            flash('Já existe um fornecedor com este nome!', 'danger')
            conn.close()
            return redirect(url_for('avaliacao_fornecedores', tab='fornecedores'))
        
        if existente_cnpj:
            flash('Já existe um fornecedor com este CNPJ!', 'danger')
            conn.close()
            return redirect(url_for('avaliacao_fornecedores', tab='fornecedores'))
        
        # Inserir o novo fornecedor
        conn.execute('INSERT INTO fornecedores (nome, cnpj, email, telefone) VALUES (?, ?, ?, ?)',
                   (nome, cnpj, email, telefone))
        conn.commit()
        conn.close()
        
        flash('Fornecedor adicionado com sucesso!', 'success')
        return redirect(url_for('avaliacao_fornecedores', tab='fornecedores'))

@app.route('/avaliacao-fornecedores/editar-fornecedor/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_fornecedor(id):
    """Editar um fornecedor existente"""
    conn = get_db_connection()
    fornecedor = conn.execute('SELECT * FROM fornecedores WHERE id = ?', (id,)).fetchone()
    
    if not fornecedor:
        flash('Fornecedor não encontrado!', 'danger')
        conn.close()
        return redirect(url_for('avaliacao_fornecedores', tab='fornecedores'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        cnpj = request.form['cnpj']
        email = request.form.get('email', '')
        telefone = request.form.get('telefone', '')
        
        # Verificar se o novo nome ou CNPJ já existe (excluindo o fornecedor atual)
        existente_nome = conn.execute('SELECT * FROM fornecedores WHERE nome = ? AND id != ?', 
                                     (nome, id)).fetchone()
        existente_cnpj = conn.execute('SELECT * FROM fornecedores WHERE cnpj = ? AND id != ?', 
                                     (cnpj, id)).fetchone()
        
        if existente_nome:
            flash('Já existe um fornecedor com este nome!', 'danger')
            conn.close()
            return redirect(url_for('editar_fornecedor', id=id))
        
        if existente_cnpj:
            flash('Já existe um fornecedor com este CNPJ!', 'danger')
            conn.close()
            return redirect(url_for('editar_fornecedor', id=id))
        
        # Atualizar o fornecedor
        conn.execute('UPDATE fornecedores SET nome = ?, cnpj = ?, email = ?, telefone = ? WHERE id = ?',
                   (nome, cnpj, email, telefone, id))
        conn.commit()
        
        flash('Fornecedor atualizado com sucesso!', 'success')
        return redirect(url_for('avaliacao_fornecedores', tab='fornecedores'))
    
    conn.close()
    return render_template('editar_fornecedor.html', fornecedor=fornecedor)

@app.route('/avaliacao-fornecedores/excluir-fornecedor/<int:id>', methods=['POST'])
@login_required
def excluir_fornecedor(id):
    """Excluir um fornecedor"""
    conn = get_db_connection()
    
    try:
        # Verificar se existem recebimentos associados a este fornecedor
        recebimentos = conn.execute('SELECT * FROM recebimentos WHERE fornecedor_id = ?', (id,)).fetchall()
        
        if recebimentos:
            # Excluir todos os recebimentos associados a este fornecedor
            conn.execute('DELETE FROM recebimentos WHERE fornecedor_id = ?', (id,))
            
        # Excluir o fornecedor
        conn.execute('DELETE FROM fornecedores WHERE id = ?', (id,))
        conn.commit()
        
        flash('Fornecedor excluído com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao excluir fornecedor: {str(e)}', 'danger')
    finally:
        conn.close()
    
    return redirect(url_for('avaliacao_fornecedores', tab='fornecedores'))

@app.route('/avaliacao-fornecedores/adicionar-recebimento', methods=['POST'])
@login_required
def adicionar_recebimento():
    """Adicionar um novo recebimento"""
    if request.method == 'POST':
        try:
            data_recebimento = request.form['dataRecebimento']
            data_prevista = request.form['dataPrevista']
            pc = request.form['pc']
            nf = request.form['nf']
            fornecedor_id = int(request.form['fornecedor_id'])
            valor = float(request.form['valor'])
            quantidade = int(request.form['quantidade'])
            status = request.form['status']
            recebido_por = request.form['recebido_por']
            
            # Campos opcionais para problemas
            descricao_ocorrencia = request.form.get('descricao_ocorrencia', '')
            acao_imediata = request.form.get('acao_imediata', '')
            acao_corretiva = request.form.get('acao_corretiva', '')
            
            # Calcular dias de atraso
            dias_atraso = calcular_dias_atraso(data_prevista, data_recebimento)
            
            conn = get_db_connection()
            
            # Verificar se já existe um recebimento com este PC ou NF
            existente_pc = conn.execute('SELECT * FROM recebimentos WHERE pc = ?', (pc,)).fetchone()
            existente_nf = conn.execute('SELECT * FROM recebimentos WHERE nf = ?', (nf,)).fetchone()
            
            if existente_pc:
                flash('Já existe um recebimento com este número de PC!', 'danger')
                conn.close()
                return redirect(url_for('avaliacao_fornecedores', tab='recebimento'))
            
            if existente_nf:
                flash('Já existe um recebimento com este número de NF!', 'danger')
                conn.close()
                return redirect(url_for('avaliacao_fornecedores', tab='recebimento'))
            
            # Inserir o novo recebimento
            conn.execute('''
                INSERT INTO recebimentos 
                (data_recebimento, data_prevista, dias_atraso, pc, nf, fornecedor_id, valor, 
                quantidade, status, recebido_por, descricao_ocorrencia, acao_imediata, acao_corretiva, usuario_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data_recebimento, data_prevista, dias_atraso, pc, nf, fornecedor_id, valor, 
                 quantidade, status, recebido_por, descricao_ocorrencia, acao_imediata, acao_corretiva, session.get('user_id')))
            
            conn.commit()
            conn.close()
            
            flash('Recebimento registrado com sucesso!', 'success')
        except Exception as e:
            flash(f'Erro ao registrar recebimento: {str(e)}', 'danger')
        
        return redirect(url_for('avaliacao_fornecedores', tab='recebimento'))

@app.route('/avaliacao-fornecedores/editar-recebimento/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_recebimento(id):
    """Editar um recebimento existente"""
    conn = get_db_connection()
    recebimento = conn.execute('SELECT * FROM recebimentos WHERE id = ?', (id,)).fetchone()
    
    if not recebimento:
        flash('Recebimento não encontrado!', 'danger')
        conn.close()
        return redirect(url_for('avaliacao_fornecedores', tab='recebimento'))
    
    fornecedores = conn.execute('SELECT * FROM fornecedores ORDER BY nome').fetchall()
    
    if request.method == 'POST':
        try:
            data_recebimento = request.form['dataRecebimento']
            data_prevista = request.form['dataPrevista']
            pc = request.form['pc']
            nf = request.form['nf']
            fornecedor_id = int(request.form['fornecedor_id'])
            valor = float(request.form['valor'])
            quantidade = int(request.form['quantidade'])
            status = request.form['status']
            recebido_por = request.form['recebido_por']
            
            # Campos opcionais para problemas
            descricao_ocorrencia = request.form.get('descricao_ocorrencia', '')
            acao_imediata = request.form.get('acao_imediata', '')
            acao_corretiva = request.form.get('acao_corretiva', '')
            
            # Calcular dias de atraso
            dias_atraso = calcular_dias_atraso(data_prevista, data_recebimento)
            
            # Verificar se o novo PC ou NF já existe (excluindo o recebimento atual)
            existente_pc = conn.execute('SELECT * FROM recebimentos WHERE pc = ? AND id != ?', 
                                      (pc, id)).fetchone()
            existente_nf = conn.execute('SELECT * FROM recebimentos WHERE nf = ? AND id != ?', 
                                      (nf, id)).fetchone()
            
            if existente_pc:
                flash('Já existe um recebimento com este número de PC!', 'danger')
                conn.close()
                return redirect(url_for('editar_recebimento', id=id))
            
            if existente_nf:
                flash('Já existe um recebimento com este número de NF!', 'danger')
                conn.close()
                return redirect(url_for('editar_recebimento', id=id))
            
            # Atualizar o recebimento
            conn.execute('''
                UPDATE recebimentos SET 
                data_recebimento = ?, data_prevista = ?, dias_atraso = ?, pc = ?, 
                nf = ?, fornecedor_id = ?, valor = ?, quantidade = ?, status = ?, 
                recebido_por = ?, descricao_ocorrencia = ?, acao_imediata = ?, 
                acao_corretiva = ? 
                WHERE id = ?
            ''', (data_recebimento, data_prevista, dias_atraso, pc, nf, fornecedor_id, 
                 valor, quantidade, status, recebido_por, descricao_ocorrencia, 
                 acao_imediata, acao_corretiva, id))
            
            conn.commit()
            flash('Recebimento atualizado com sucesso!', 'success')
            return redirect(url_for('avaliacao_fornecedores', tab='recebimento'))
        except Exception as e:
            flash(f'Erro ao atualizar recebimento: {str(e)}', 'danger')
    
    conn.close()
    return render_template('editar_recebimento.html', recebimento=recebimento, fornecedores=fornecedores)

@app.route('/avaliacao-fornecedores/excluir-recebimento/<int:id>', methods=['POST'])
@login_required
def excluir_recebimento(id):
    """Excluir um recebimento"""
    conn = get_db_connection()
    conn.execute('DELETE FROM recebimentos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Recebimento excluído com sucesso!', 'success')
    return redirect(url_for('avaliacao_fornecedores', tab='recebimento'))

@app.route('/init-db-fornecedores')
@admin_required
def init_db_fornecedores():
    """Inicializa o banco de dados com as tabelas de avaliação de fornecedores"""
    try:
        from avaliacao_fornecedores_update import update_database_fornecedores
        update_database_fornecedores()
        flash('Banco de dados de avaliação de fornecedores inicializado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao inicializar banco de dados: {str(e)}', 'danger')
    
    return redirect(url_for('admin_painel'))

@app.route('/api/check_product_name')
@login_required
def check_product_name():
    """Verifica se já existe um produto com o nome fornecido"""
    nome = request.args.get('nome', '').strip()
    produto_id = request.args.get('produto_id', None)
    
    if not nome:
        return jsonify({'valid': False, 'message': 'Nome não fornecido'})
    
    conn = get_db_connection()
    
    # Para depuração
    print(f"Verificando nome de produto: '{nome}', ID: {produto_id}")
    
    if produto_id:
        # Verificando na edição (excluindo o produto atual)
        produto = conn.execute('SELECT id FROM produtos WHERE UPPER(nome) = UPPER(?) AND id != ?', 
                             (nome, produto_id)).fetchone()
    else:
        # Verificando na criação
        query = 'SELECT id FROM produtos WHERE UPPER(nome) = UPPER(?)'
        try:
            produto = conn.execute(query, (nome,)).fetchone()
            # Log para depuração
            if produto:
                print(f"Produto encontrado com esse nome: ID={produto['id']}")
            else:
                print(f"Nenhum produto encontrado com o nome: '{nome}'")
        except Exception as e:
            conn.close()
            print(f"Erro ao verificar nome: {str(e)}")
            return jsonify({'valid': False, 'message': f'Erro na verificação: {str(e)}'})
    
    conn.close()
    
    if produto:
        return jsonify({'valid': False, 'message': f'Já existe um produto com o nome "{nome}"'})
    else:
        return jsonify({'valid': True, 'message': 'Nome disponível'})

@app.route('/api/search-clientes')
@login_required
def search_clientes():
    """API para buscar clientes pelo nome"""
    termo = request.args.get('termo', '').strip()
    
    if not termo or len(termo) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    
    # Busca clientes que correspondem ao termo
    clientes = conn.execute(
        'SELECT DISTINCT descricao FROM produtos WHERE descricao IS NOT NULL AND descricao != "" AND UPPER(descricao) LIKE UPPER(?) ORDER BY descricao LIMIT 10', 
        (f'%{termo}%',)
    ).fetchall()
    
    conn.close()
    
    # Converter para lista de strings
    resultado = [cliente['descricao'] for cliente in clientes]
    
    return jsonify(resultado)

@app.route('/api/search-componentes')
@login_required
def search_componentes():
    """API para buscar componentes pelo nome ou código"""
    termo = request.args.get('termo', '').strip()
    
    if not termo or len(termo) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    
    # Busca componentes que correspondem ao termo
    componentes = conn.execute(
        'SELECT codigo, nome FROM componentes WHERE UPPER(codigo) LIKE UPPER(?) OR UPPER(nome) LIKE UPPER(?) ORDER BY nome LIMIT 10', 
        (f'%{termo}%', f'%{termo}%')
    ).fetchall()
    
    conn.close()
    
    # Converter para lista de dicionários
    resultado = [{'codigo': c['codigo'], 'nome': c['nome']} for c in componentes]
    
    return jsonify(resultado)

@app.route('/api/search-produtos')
@login_required
def search_produtos():
    """API para buscar produtos pelo nome ou cliente"""
    termo = request.args.get('termo', '').strip()
    
    if not termo or len(termo) < 2:
        return jsonify([])
    
    conn = get_db_connection()
    
    # Busca produtos que correspondem ao termo (no nome ou no cliente)
    produtos = conn.execute(
        'SELECT id, nome, descricao as cliente FROM produtos WHERE UPPER(nome) LIKE UPPER(?) OR UPPER(descricao) LIKE UPPER(?) ORDER BY nome LIMIT 10', 
        (f'%{termo}%', f'%{termo}%')
    ).fetchall()
    
    conn.close()
    
    # Converter para lista de dicionários com id e nome
    resultado = [{'id': prod['id'], 'nome': prod['nome'], 'cliente': prod['cliente'] or ''} for prod in produtos]
    
    return jsonify(resultado)

@app.route('/api/calcular-producao')
@login_required
def api_calcular_producao():
    """API para calcular produção (retorna HTML para injetar no modal)"""
    produto_id = request.args.get('produto_id', '')
    quantidade = int(request.args.get('quantidade', 1))
    
    conn = get_db_connection()
    
    # Busca o produto
    produto_row = conn.execute('SELECT * FROM produtos WHERE id = ?', (produto_id,)).fetchone()
    
    if produto_row is None:
        conn.close()
        return jsonify({'error': 'Produto não encontrado!'}), 404
    
    # Converte para dicionário
    produto = dict(produto_row)
    
    # Busca os componentes do produto
    componentes = conn.execute('''
        SELECT cp.quantidade, c.codigo, c.nome, c.quantidade as estoque
        FROM componentes_produto cp
        JOIN componentes c ON cp.codigo_componente = c.codigo
        WHERE cp.produto_id = ?
    ''', (produto_id,)).fetchall()
    
    # Calcula a quantidade necessária de cada componente
    componentes_necessarios = []
    indisponiveis = 0
    
    for componente in componentes:
        qtd_necessaria = componente['quantidade'] * quantidade
        disponivel = componente['estoque'] >= qtd_necessaria
        
        if not disponivel:
            indisponiveis += 1
            
        componentes_necessarios.append({
            'codigo': componente['codigo'],
            'nome': componente['nome'],
            'quantidade_unitaria': componente['quantidade'],
            'quantidade_total': qtd_necessaria,
            'estoque': componente['estoque'],
            'disponivel': disponivel
        })
    
    conn.close()
    
    # Renderiza o template parcial
    html_content = render_template('_resultado_calculo_partial.html', 
                         produto=produto, 
                         quantidade=quantidade,
                         componentes=componentes_necessarios,
                         indisponiveis=indisponiveis)
    
    return jsonify({
        'html': html_content,
        'todos_disponiveis': indisponiveis == 0
    })

@app.route('/atualizar_componente/<codigo_original>/<codigo_novo>/<nome>/<quantidade>')
@login_required
def atualizar_componente_rapido(codigo_original, codigo_novo, nome, quantidade):
    """Atualiza um componente (versão rápida)"""
    conn = get_db_connection()
    componente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                             (codigo_original,)).fetchone()
    
    if componente is None:
        conn.close()
        flash('Componente não encontrado!', 'danger')
        return redirect(url_for('listar_componentes'))
    
    try:
        quantidade = int(quantidade)
        codigo_alterado = codigo_original != codigo_novo
        
        # Garante que a primeira letra do nome seja maiúscula
        if nome:
            nome = nome[0].upper() + nome[1:] if len(nome) > 1 else nome.upper()
        
        # Verificar se o novo código já existe (apenas se foi alterado)
        if codigo_alterado:
            # Verifica se o novo código já existe
            existente = conn.execute('SELECT * FROM componentes WHERE codigo = ? AND codigo != ?', 
                                    (codigo_novo, codigo_original)).fetchone()
            if existente:
                flash(f'Erro: Já existe um componente com o código {codigo_novo}!', 'danger')
                conn.close()
                return redirect(url_for('listar_componentes'))
        
        # Verificar se o nome já existe (usando normalização para comparação case-insensitive)
        nome_original = componente['nome']
        if nome.lower() != nome_original.lower():  # Checa se o nome foi alterado
            name_normalized = re.sub(r'[^a-zA-Z0-9]', '', nome.lower())
            componentes = conn.execute('SELECT nome FROM componentes WHERE codigo != ?', 
                                     (codigo_original,)).fetchall()
            
            for componente_row in componentes:
                componente_nome = componente_row['nome']
                componente_normalizado = re.sub(r'[^a-zA-Z0-9]', '', componente_nome.lower())
                
                if componente_normalizado == name_normalized:
                    flash(f'Erro: Já existe um componente com nome similar: {componente_nome}!', 'danger')
                    conn.close()
                    return redirect(url_for('listar_componentes'))
        
        if codigo_alterado:
            # Atualiza o componente com o novo código e atualiza referências
            conn.execute('''
                UPDATE componentes 
                SET codigo = ?, nome = ?, quantidade = ? 
                WHERE codigo = ?
            ''', (codigo_novo, nome, quantidade, codigo_original))
            
            # Atualiza referências em outras tabelas
            conn.execute('UPDATE componentes_produto SET codigo_componente = ? WHERE codigo_componente = ?', 
                        (codigo_novo, codigo_original))
            conn.execute('UPDATE transacoes SET codigo_componente = ? WHERE codigo_componente = ?', 
                        (codigo_novo, codigo_original))
            
            flash('Componente atualizado com sucesso! O código foi alterado.', 'success')
        else:
            # Apenas atualiza o nome e quantidade sem alterar o código
            conn.execute('UPDATE componentes SET nome = ?, quantidade = ? WHERE codigo = ?',
                        (nome, quantidade, codigo_original))
            
            flash('Componente atualizado com sucesso!', 'success')
        
        conn.commit()
        conn.close()
    except Exception as e:
        flash(f'Erro ao atualizar componente: {str(e)}', 'danger')
        conn.close()
    
    return redirect(url_for('listar_componentes'))

@app.route('/componentes/adicionar_rapido/<codigo>/<nome>/<quantidade>', methods=['GET'])
@login_required
def adicionar_componente_rapido(codigo, nome, quantidade):
    """Adiciona um novo componente a partir do modal, usando parâmetros da URL"""
    conn = get_db_connection()
    
    # Verificar se o código já existe
    existente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                           (codigo,)).fetchone()
    if existente:
        flash(f'Erro: Já existe um componente com o código {codigo}!', 'danger')
        conn.close()
        return redirect(url_for('listar_componentes'))
    
    # Verificar se o nome já existe (usando normalização para comparação case-insensitive)
    name_normalized = re.sub(r'[^a-zA-Z0-9]', '', nome.lower())
    componentes = conn.execute('SELECT nome FROM componentes').fetchall()
    
    for componente in componentes:
        componente_nome = componente['nome']
        componente_normalizado = re.sub(r'[^a-zA-Z0-9]', '', componente_nome.lower())
        
        if componente_normalizado == name_normalized:
            flash(f'Erro: Já existe um componente com nome similar: {componente_nome}!', 'danger')
            conn.close()
            return redirect(url_for('listar_componentes'))
    
    try:
        # Garantir que a quantidade seja um número inteiro
        quantidade = int(quantidade)
        
        # Garantir que a primeira letra do nome seja maiúscula
        if nome:
            nome = nome[0].upper() + nome[1:] if len(nome) > 1 else nome.upper()
        
        # Inserir o novo componente
        conn.execute('INSERT INTO componentes (codigo, nome, quantidade) VALUES (?, ?, ?)',
                    (codigo, nome, quantidade))
        
        # Registrar no histórico de transações se a quantidade for maior que zero
        if quantidade > 0:
            usuario_id = session.get('user_id', None)
            data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            conn.execute('''
                INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, usuario_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (codigo, 'entrada', quantidade, data_atual, usuario_id))
        
        conn.commit()
        conn.close()
        
        flash('Componente adicionado com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f'Erro ao adicionar componente: {str(e)}', 'danger')
    
    return redirect(url_for('listar_componentes'))

@app.route('/api/produto/<int:produto_id>')
@login_required
def api_produto(produto_id):
    """API para obter detalhes de um produto pelo ID"""
    conn = get_db_connection()
    
    # Busca o produto
    produto = conn.execute('SELECT id, nome, descricao FROM produtos WHERE id = ?', (produto_id,)).fetchone()
    
    if produto is None:
        conn.close()
        return jsonify({'error': 'Produto não encontrado'}), 404
    
    # Busca os componentes do produto
    componentes = conn.execute('''
        SELECT cp.codigo_componente as codigo, c.nome, cp.quantidade
        FROM componentes_produto cp
        JOIN componentes c ON cp.codigo_componente = c.codigo
        WHERE cp.produto_id = ?
    ''', (produto_id,)).fetchall()
    
    conn.close()
    
    # Converter para dicionário
    result = {
        'id': produto['id'],
        'nome': produto['nome'],
        'descricao': produto['descricao'],
        'componentes': [{'codigo': c['codigo'], 'nome': c['nome'], 'quantidade': c['quantidade']} for c in componentes]
    }
    
    return jsonify(result)

@app.route('/avaliacao-fornecedores/relatorios-analise')
@login_required
def relatorios_analise():
    """Nova página de relatórios com design simplificado e moderno"""
    # Verificar se há parâmetros na solicitação (se um relatório está sendo gerado)
    has_report = len(request.args) > 0
    
    # Obter anos disponíveis para o filtro
    anos = obter_anos_disponiveis()
    
    # Se não for para gerar relatório, mostrar apenas o formulário
    if not has_report:
        # Obter a lista de fornecedores para o dropdown de seleção
        fornecedores = get_fornecedores()
        return render_template('relatorios_analise.html',
                              fornecedores=fornecedores,
                              anos=anos,
                              has_report=False)
    
    # Parâmetros do relatório
    report_type = request.args.get('report_type', '')
    period_type = request.args.get('period_type', '')
    
    # Obter valores de período conforme o tipo selecionado
    month_period = request.args.get('month_period', '')
    quarter_period = request.args.get('quarter_period', '')
    year_period = request.args.get('year_period', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Filtro de fornecedores
    supplier_filter = request.args.get('supplier_filter', 'all')
    specific_supplier = request.args.get('specific_supplier', '')
    
    # Opções
    include_chart = request.args.get('include_chart', 'off') == 'on'
    
    # Formatação do período selecionado para exibição
    periodo_selecionado = formatar_periodo_selecionado(period_type, month_period, quarter_period, year_period, start_date, end_date)
    
    # Obter recebimentos filtrados com base no período
    recebimentos_filtrados = filtrar_recebimentos_por_periodo_avancado(
        period_type, month_period, quarter_period, year_period, start_date, end_date
    )
    
    # Se não houver dados para o período, mostrar mensagem
    if not recebimentos_filtrados:
        fornecedores = get_fornecedores()
        return render_template('relatorios_analise.html',
                              fornecedores=fornecedores,
                              anos=anos,
                              has_report=True,
                              report_title="Sem dados para o período",
                              report_type=report_type,
                              periodo_selecionado=periodo_selecionado,
                              total_fornecedores=0,
                              fornecedores_acima_meta=0,
                              fornecedores_abaixo_meta=0,
                              media_geral_performance=0,
                              report_content="<div class='alert alert-warning'>Não há dados disponíveis para o período selecionado.</div>",
                              report_query_string=request.query_string.decode())
    
    # Calcular métricas gerais
    fornecedores = get_fornecedores()
    avaliacoes_periodo = calcular_avaliacoes(recebimentos_filtrados)
    
    # Aplicar filtro de fornecedores
    if supplier_filter == 'critical':
        avaliacoes_periodo = [a for a in avaliacoes_periodo if a['scoreFinal'] < 85]
    elif supplier_filter == 'top':
        avaliacoes_periodo = sorted(avaliacoes_periodo, key=lambda x: x['scoreFinal'], reverse=True)[:10]
    elif supplier_filter == 'specific' and specific_supplier:
        avaliacoes_periodo = [a for a in avaliacoes_periodo if a['id'] == int(specific_supplier)]
    
    # Calcular métricas sobre os dados filtrados
    total_fornecedores = len(avaliacoes_periodo)
    fornecedores_acima_meta = len([a for a in avaliacoes_periodo if a['scoreFinal'] >= 85])
    fornecedores_abaixo_meta = len([a for a in avaliacoes_periodo if a['scoreFinal'] < 85])
    media_geral_performance = round(sum(a['scoreFinal'] for a in avaliacoes_periodo) / total_fornecedores if total_fornecedores else 0, 1)
    
    # Gerar títulos personalizados com base no tipo de relatório
    report_titles = {
        'performance': 'Análise de Desempenho Geral',
        'critical': 'Fornecedores com Desempenho Crítico',
        'trend': 'Análise de Tendências',
        'comparative': 'Análise Comparativa de Fornecedores'
    }
    
    report_title = report_titles.get(report_type, 'Relatório de Fornecedores')
    
    # Gerar conteúdo do relatório
    report_content = gerar_conteudo_relatorio(
        report_type, 
        avaliacoes_periodo, 
        recebimentos_filtrados, 
        periodo_selecionado,
        include_chart
    )
    
    # Renderizar template com os dados do relatório
    return render_template('relatorios_analise.html',
                          fornecedores=fornecedores,
                          anos=anos,
                          has_report=True,
                          report_title=report_title,
                          report_type=report_type,
                          periodo_selecionado=periodo_selecionado,
                          total_fornecedores=total_fornecedores,
                          fornecedores_acima_meta=fornecedores_acima_meta,
                          fornecedores_abaixo_meta=fornecedores_abaixo_meta,
                          media_geral_performance=media_geral_performance,
                          avaliacoes_periodo=avaliacoes_periodo,
                          recebimentos_filtrados=recebimentos_filtrados,
                          report_content=report_content,
                          report_query_string=request.query_string.decode())

def formatar_periodo_selecionado(period_type, month_period, quarter_period, year_period, start_date, end_date):
    """Formata o período selecionado para exibição"""
    if period_type == 'month' and month_period:
        try:
            date_parts = month_period.split('-')
            year = date_parts[0]
            month = int(date_parts[1])
            months = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                     'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
            return f"{months[month-1]} de {year}"
        except:
            return month_period
    elif period_type == 'quarter' and quarter_period:
        try:
            date_parts = quarter_period.split('-')
            year = date_parts[0]
            quarter = date_parts[1]
            return f"{quarter}º Trimestre de {year}"
        except:
            return quarter_period
    elif period_type == 'year' and year_period:
        return f"Ano de {year_period}"
    elif period_type == 'custom' and start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            end = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            return f"De {start} até {end}"
        except:
            return f"{start_date} até {end_date}"
    else:
        return "Período não especificado"

def filtrar_recebimentos_por_periodo_avancado(period_type, month_period, quarter_period, year_period, start_date, end_date):
    """Filtra recebimentos com base nos parâmetros avançados de período"""
    # Obter todos os recebimentos
    recebimentos = get_recebimentos()
    
    # Se não houver parâmetros de filtro, retornar vazio
    if not period_type:
        return []
    
    # Converter para o formato adequado com base no tipo de período
    if period_type == 'month' and month_period:
        # Formato month_period: "YYYY-MM"
        try:
            date_parts = month_period.split('-')
            year = int(date_parts[0])
            month = int(date_parts[1])
            
            # Primeiro e último dia do mês
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        except:
            return []
            
    elif period_type == 'quarter' and quarter_period:
        # Formato quarter_period: "YYYY-Q" (ex: "2023-1" para 1º trimestre de 2023)
        try:
            date_parts = quarter_period.split('-')
            year = int(date_parts[0])
            quarter = int(date_parts[1])
            
            # Determinar meses do trimestre
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            
            # Primeiro dia do trimestre
            start_date = datetime(year, start_month, 1)
            
            # Último dia do trimestre
            if end_month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, end_month + 1, 1) - timedelta(days=1)
        except:
            return []
            
    elif period_type == 'year' and year_period:
        # Formato year_period: "YYYY"
        try:
            year = int(year_period)
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
        except:
            return []
            
    elif period_type == 'custom' and start_date and end_date:
        # Formato start_date/end_date: "YYYY-MM-DD"
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except:
            return []
    else:
        return []
    
    # Filtrar recebimentos que estão dentro do período
    filtered_recebimentos = []
    for recebimento in recebimentos:
        try:
            # Converter a data do recebimento
            recebimento_date = datetime.strptime(recebimento['data_recebimento'], '%Y-%m-%d') if isinstance(recebimento['data_recebimento'], str) else recebimento['data_recebimento']
            
            # Verificar se está dentro do período
            if start_date <= recebimento_date <= end_date:
                filtered_recebimentos.append(recebimento)
        except:
            continue
    
    return filtered_recebimentos

def gerar_conteudo_relatorio(report_type, avaliacoes, recebimentos, periodo, include_chart):
    """Gera o conteúdo HTML para o relatório com base no tipo"""
    if not avaliacoes:
        return "<div class='alert alert-warning'>Não há dados para o período selecionado</div>"
        
    if report_type == 'performance':
        return gerar_relatorio_desempenho(avaliacoes, include_chart)
    elif report_type == 'critical':
        return gerar_relatorio_criticos(avaliacoes, recebimentos, include_chart)
    elif report_type == 'trend':
        return gerar_relatorio_tendencias(recebimentos, periodo, include_chart)
    elif report_type == 'comparative':
        return gerar_relatorio_comparativo(avaliacoes, include_chart)
    else:
        return "<div class='alert alert-info'>Tipo de relatório não reconhecido</div>"

def gerar_relatorio_desempenho(avaliacoes, include_chart):
    """Gera o relatório de desempenho geral"""
    html = '<div class="card shadow-sm border-0 mb-4">'
    html += '<div class="card-header bg-white py-3"><h5 class="mb-0 text-primary"><i class="fas fa-chart-line me-2"></i>Desempenho Geral dos Fornecedores</h5></div>'
    html += '<div class="card-body p-0">'
    
    # Tabela de avaliações
    html += '<div class="table-responsive">'
    html += '<table class="table table-hover align-middle mb-0">'
    html += '<thead class="table-light"><tr>'
    html += '<th class="py-3">Fornecedor</th>'
    html += '<th class="py-3 text-center">Total Recebimentos</th>'
    html += '<th class="py-3 text-center">% Aprovação</th>'
    html += '<th class="py-3 text-center">% Pontualidade</th>'
    html += '<th class="py-3 text-center">Score Final</th>'
    html += '<th class="py-3 text-center">Status</th>'
    html += '</tr></thead><tbody>'
    
    # Ordenar fornecedores por score (do maior para o menor)
    sorted_avaliacoes = sorted(avaliacoes, key=lambda x: x['scoreFinal'], reverse=True)
    
    for avaliacao in sorted_avaliacoes:
        status_class = "success" if avaliacao['scoreFinal'] >= 85 else "danger"
        status_text = "BOM" if avaliacao['scoreFinal'] >= 85 else "CRÍTICO"
        
        html += f'<tr>'
        html += f'<td class="fw-bold">{avaliacao["nome"]}</td>'
        html += f'<td class="text-center">{avaliacao["total"]}</td>'
        
        # Aprovação com barra de progresso
        html += f'<td class="text-center">'
        html += f'<div class="d-flex align-items-center justify-content-center">'
        html += f'<div class="progress flex-grow-1" style="height: 8px; max-width: 80px;">'
        html += f'<div class="progress-bar bg-{"success" if avaliacao["percentualAprovacao"] >= 85 else "danger"}" role="progressbar" style="width: {avaliacao["percentualAprovacao"]}%"></div>'
        html += f'</div>'
        html += f'<span class="ms-2 fw-semibold">{avaliacao["percentualAprovacao"]}%</span>'
        html += f'</div>'
        html += f'</td>'
        
        # Pontualidade com barra de progresso
        html += f'<td class="text-center">'
        html += f'<div class="d-flex align-items-center justify-content-center">'
        html += f'<div class="progress flex-grow-1" style="height: 8px; max-width: 80px;">'
        html += f'<div class="progress-bar bg-{"success" if avaliacao["percentualPontualidade"] >= 85 else "danger"}" role="progressbar" style="width: {avaliacao["percentualPontualidade"]}%"></div>'
        html += f'</div>'
        html += f'<span class="ms-2 fw-semibold">{avaliacao["percentualPontualidade"]}%</span>'
        html += f'</div>'
        html += f'</td>'
        
        # Score final
        html += f'<td class="text-center">'
        html += f'<div class="display-6 fw-bold" style="font-size: 1.25rem; color: {"#198754" if avaliacao["scoreFinal"] >= 85 else "#dc3545"};">{avaliacao["scoreFinal"]}%</div>'
        html += f'<div class="small text-muted">Meta: 85%</div>'
        html += f'</td>'
        
        # Status
        html += f'<td class="text-center">'
        html += f'<span class="badge rounded-pill text-bg-{status_class} px-3 py-2">{status_text}</span>'
        html += f'</td>'
        
        html += f'</tr>'
    
    html += '</tbody></table>'
    html += '</div>' # Fim da table-responsive
    
    html += '</div>' # Fim do card-body
    html += '</div>' # Fim do card
    
    # Adicionar gráfico se solicitado
    if include_chart:
        html += '<div class="card shadow-sm border-0">'
        html += '<div class="card-header bg-white py-3"><h5 class="mb-0 text-primary"><i class="fas fa-chart-pie me-2"></i>Distribuição de Performance</h5></div>'
        html += '<div class="card-body p-4 text-center">'
        html += '<div class="alert alert-info">Visualização de gráficos será implementada em uma atualização futura.</div>'
        html += '</div>'
        html += '</div>'
    
    return html

def gerar_relatorio_criticos(avaliacoes, recebimentos, include_chart):
    """Gera o relatório de fornecedores críticos"""
    # Filtrar apenas fornecedores críticos
    fornecedores_criticos = [a for a in avaliacoes if a['scoreFinal'] < 85]
    
    # Se não houver fornecedores críticos
    if not fornecedores_criticos:
        return "<div class='alert alert-success'><i class='fas fa-check-circle me-2'></i>Não há fornecedores com desempenho crítico no período selecionado.</div>"
    
    html = '<div class="card shadow-sm border-0 mb-4">'
    html += '<div class="card-header bg-white py-3"><h5 class="mb-0 text-primary"><i class="fas fa-exclamation-triangle me-2"></i>Fornecedores com Desempenho Crítico</h5></div>'
    html += '<div class="card-body p-0">'
    
    # Tabela de fornecedores críticos
    html += '<div class="table-responsive">'
    html += '<table class="table table-hover align-middle mb-0">'
    html += '<thead class="table-light"><tr>'
    html += '<th class="py-3">Fornecedor</th>'
    html += '<th class="py-3 text-center">Total Recebimentos</th>'
    html += '<th class="py-3 text-center">% Aprovação</th>'
    html += '<th class="py-3 text-center">% Pontualidade</th>'
    html += '<th class="py-3 text-center">Score Final</th>'
    html += '<th class="py-3 text-center">Status</th>'
    html += '</tr></thead><tbody>'
    
    # Ordenar fornecedores por score (do menor para o maior)
    sorted_criticos = sorted(fornecedores_criticos, key=lambda x: x['scoreFinal'])
    
    for fornecedor in sorted_criticos:
        html += f'<tr class="clickable-row" data-bs-toggle="collapse" data-bs-target="#detalhes-{fornecedor["id"]}">'
        
        # Nome com ícone expansível
        html += f'<td class="fw-bold">'
        html += f'<div class="d-flex align-items-center">'
        html += f'<span class="rounded-circle bg-danger bg-opacity-10 p-2 me-3">'
        html += f'<i class="fas fa-caret-right text-danger transition-icon"></i>'
        html += f'</span>'
        html += f'{fornecedor["nome"]}'
        html += f'</div>'
        html += f'</td>'
        
        html += f'<td class="text-center">{fornecedor["total"]}</td>'
        
        # Aprovação com barra de progresso
        html += f'<td class="text-center">'
        html += f'<div class="d-flex align-items-center justify-content-center">'
        html += f'<div class="progress flex-grow-1" style="height: 8px; max-width: 80px;">'
        html += f'<div class="progress-bar bg-danger" role="progressbar" style="width: {fornecedor["percentualAprovacao"]}%"></div>'
        html += f'</div>'
        html += f'<span class="ms-2 fw-semibold">{fornecedor["percentualAprovacao"]}%</span>'
        html += f'</div>'
        html += f'</td>'
        
        # Pontualidade com barra de progresso
        html += f'<td class="text-center">'
        html += f'<div class="d-flex align-items-center justify-content-center">'
        html += f'<div class="progress flex-grow-1" style="height: 8px; max-width: 80px;">'
        html += f'<div class="progress-bar bg-danger" role="progressbar" style="width: {fornecedor["percentualPontualidade"]}%"></div>'
        html += f'</div>'
        html += f'<span class="ms-2 fw-semibold">{fornecedor["percentualPontualidade"]}%</span>'
        html += f'</div>'
        html += f'</td>'
        
        # Score final
        html += f'<td class="text-center">'
        html += f'<div class="display-6 fw-bold" style="font-size: 1.25rem; color: #dc3545;">{fornecedor["scoreFinal"]}%</div>'
        html += f'<div class="small text-muted">Meta: 85%</div>'
        html += f'</td>'
        
        # Status
        html += f'<td class="text-center">'
        html += f'<span class="badge rounded-pill text-bg-danger px-3 py-2"><i class="fas fa-exclamation-circle me-1"></i>Crítico</span>'
        html += f'</td>'
        
        html += f'</tr>'
        
        # Detalhes do fornecedor (seção expandível)
        html += f'<tr class="collapse-row">'
        html += f'<td colspan="6" class="p-0 border-0">'
        html += f'<div class="collapse shadow-sm" id="detalhes-{fornecedor["id"]}">'
        html += f'<div class="p-4 bg-light border-top border-bottom">'
        
        # Adicionar mais detalhes aqui (problemas, recomendações, etc.)
        html += f'<div class="alert alert-light border">Detalhes adicionais serão implementados em uma atualização futura.</div>'
        
        html += f'</div>'
        html += f'</div>'
        html += f'</td>'
        html += f'</tr>'
    
    html += '</tbody></table>'
    html += '</div>' # Fim da table-responsive
    
    html += '</div>' # Fim do card-body
    
    # Adicionar rodapé
    html += '<div class="card-footer bg-light py-3">'
    html += '<div class="text-muted"><i class="fas fa-info-circle me-1"></i> Clique em um fornecedor para ver detalhes adicionais.</div>'
    html += '</div>'
    
    html += '</div>' # Fim do card
    
    return html

def gerar_relatorio_tendencias(recebimentos, periodo, include_chart):
    """Gera o relatório de análise de tendências"""
    html = '<div class="card shadow-sm border-0">'
    html += '<div class="card-header bg-white py-3"><h5 class="mb-0 text-primary"><i class="fas fa-chart-line me-2"></i>Análise de Tendências</h5></div>'
    html += '<div class="card-body p-4">'
    
    html += '<div class="alert alert-info">O relatório de análise de tendências será implementado em uma atualização futura.</div>'
    
    html += '</div>' # Fim do card-body
    html += '</div>' # Fim do card
    
    return html

def gerar_relatorio_comparativo(avaliacoes, include_chart=True):
    """
    Gera o HTML para o relatório comparativo de fornecedores
    
    Args:
        avaliacoes: Lista de dicionários com avaliações dos fornecedores
        include_chart: Se True, inclui gráficos comparativos
        
    Returns:
        str: HTML do relatório comparativo
    """
    if not avaliacoes or len(avaliacoes) == 0:
        return '<div class="alert alert-warning">Não há dados suficientes para análise no período selecionado.</div>'
    
    # Ordenar por pontuação final (decrescente)
    avaliacoes.sort(key=lambda x: x['scoreFinal'], reverse=True)
    
    # Gerar tabela comparativa
    html_tabela = """
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="mb-0">Tabela Comparativa</h5>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th scope="col">Critério</th>
    """
    
    # Adicionar cabeçalhos dos fornecedores
    for avaliacao in avaliacoes:
        html_tabela += f'<th scope="col" class="text-center">{avaliacao["nome"]}</th>\n'
    
    html_tabela += """
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Linha de qualidade
    html_tabela += '<tr><th scope="row">Qualidade dos Itens</th>\n'
    for avaliacao in avaliacoes:
        qualidade = avaliacao['percentualAprovacao']
        cls = 'success' if qualidade >= 90 else ('warning' if qualidade >= 70 else 'danger')
        html_tabela += f"""
                        <td class="text-center">
                            <span class="badge badge-{cls}">{qualidade:.1f}%</span>
                            <div class="progress mt-1" style="height: 4px;">
                                <div class="progress-bar bg-{cls}" role="progressbar" style="width: {qualidade}%;"></div>
                            </div>
                        </td>
        """
    html_tabela += '</tr>\n'
    
    # Linha de pontualidade
    html_tabela += '<tr><th scope="row">Pontualidade nas Entregas</th>\n'
    for avaliacao in avaliacoes:
        pontualidade = avaliacao['percentualPontualidade']
        cls = 'success' if pontualidade >= 90 else ('warning' if pontualidade >= 70 else 'danger')
        html_tabela += f"""
                        <td class="text-center">
                            <span class="badge badge-{cls}">{pontualidade:.1f}%</span>
                            <div class="progress mt-1" style="height: 4px;">
                                <div class="progress-bar bg-{cls}" role="progressbar" style="width: {pontualidade}%;"></div>
                            </div>
                        </td>
        """
    html_tabela += '</tr>\n'
    
    # Linha de pontuação geral
    html_tabela += '<tr class="table-primary"><th scope="row">Pontuação Geral</th>\n'
    for avaliacao in avaliacoes:
        html_tabela += f'<td class="text-center font-weight-bold">{avaliacao["scoreFinal"]:.1f}%</td>\n'
    html_tabela += '</tr>\n'
    
    html_tabela += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    
    # Gerar gráfico de radar se solicitado
    html_grafico = ""
    if include_chart and len(avaliacoes) > 0:
        html_grafico = gerar_grafico_comparativo(avaliacoes)
    
    # Gerar conclusões e recomendações
    html_conclusoes = gerar_conclusoes_recomendacoes(avaliacoes)
    
    return html_tabela + html_grafico + html_conclusoes

def gerar_grafico_comparativo(avaliacoes):
    """
    Gera o HTML com gráfico comparativo de fornecedores
    
    Args:
        avaliacoes: Lista de dicionários com avaliações dos fornecedores
        
    Returns:
        str: HTML do gráfico comparativo
    """
    # Gerar dados para o gráfico
    categorias = ['Qualidade', 'Pontualidade']
    fornecedores = [avaliacao['nome'] for avaliacao in avaliacoes]
    
    # Criar figura
    plt.figure(figsize=(10, 6))
    
    # Definir posições das barras
    x = np.arange(len(categorias))
    width = 0.2  # largura de cada barra
    offsets = np.linspace(-(width * (len(fornecedores)-1)/2), (width * (len(fornecedores)-1)/2), len(fornecedores))
    
    # Plotar barras para cada fornecedor
    for i, avaliacao in enumerate(avaliacoes):
        valores = [avaliacao['percentualAprovacao'], avaliacao['percentualPontualidade']]
        plt.bar(x + offsets[i], valores, width, label=avaliacao['nome'])
    
    # Adicionar rótulos e legendas
    plt.xlabel('Critérios')
    plt.ylabel('Pontuação (%)')
    plt.title('Comparativo de Desempenho de Fornecedores')
    plt.xticks(x, categorias)
    plt.ylim(0, 100)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Converter o gráfico para base64
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Montar HTML do gráfico
    html_grafico = f"""
    <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">Comparativo Geral por Critérios</h5>
        </div>
        <div class="card-body">
            <div class="chart-container text-center">
                <img src="data:image/png;base64,{img_str}" class="img-fluid" alt="Gráfico Comparativo">
            </div>
        </div>
    </div>
    """
    
    return html_grafico

def gerar_conclusoes_recomendacoes(avaliacoes):
    """
    Gera o HTML com conclusões e recomendações baseadas na análise dos fornecedores
    
    Args:
        avaliacoes: Lista de dicionários com avaliações dos fornecedores
        
    Returns:
        str: HTML das conclusões e recomendações
    """
    # Determinar fornecedor com melhor desempenho (já está ordenado na função principal)
    melhor_fornecedor = avaliacoes[0]['nome']
    pontuacao_melhor = avaliacoes[0]['scoreFinal']
    
    # Identificar fornecedores críticos (pontuação < 70%)
    fornecedores_criticos = [f for f in avaliacoes if f['scoreFinal'] < 70]
    
    # Construir HTML
    html_conclusoes = """
    <div class="card">
        <div class="card-header">
            <h5 class="mb-0">Conclusões e Recomendações</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <h6>Avaliação Geral</h6>
    """
    
    if len(avaliacoes) > 1:
        html_conclusoes += f"""
                    <p>A análise comparativa entre os fornecedores selecionados demonstra que <strong>{melhor_fornecedor}</strong> 
                    apresenta o melhor desempenho geral com pontuação de {pontuacao_melhor:.1f}%.
                    """
        
        # Se houver fornecedores críticos, adicionar alerta
        if fornecedores_criticos:
            html_conclusoes += """
                    <div class="alert alert-warning">
                        <strong>Atenção:</strong> Os seguintes fornecedores apresentam pontuação crítica:
                        <ul class="mb-0 mt-2">
            """
            for fc in fornecedores_criticos:
                pontos_fracos = []
                if fc['percentualAprovacao'] < 70:
                    pontos_fracos.append("qualidade")
                if fc['percentualPontualidade'] < 70:
                    pontos_fracos.append("pontualidade")
                
                html_conclusoes += f"""
                            <li><strong>{fc['nome']}</strong> ({fc['scoreFinal']:.1f}%) - 
                            Pontos críticos: {', '.join(pontos_fracos)}</li>
                """
            html_conclusoes += """
                        </ul>
                    </div>
            """
    else:
        html_conclusoes += f"""
                    <p>A análise do fornecedor <strong>{melhor_fornecedor}</strong> apresenta pontuação geral de {pontuacao_melhor:.1f}%.</p>
        """
    
    html_conclusoes += """
                </div>
                <div class="col-md-6">
                    <h6>Recomendações Estratégicas</h6>
                    <ol class="mb-0">
    """
    
    # Recomendações gerais
    if len(avaliacoes) > 0 and avaliacoes[0]['scoreFinal'] >= 90:
        html_conclusoes += f"""
                        <li class="mb-2">Manter <strong>{avaliacoes[0]['nome']}</strong> como fornecedor principal para os itens de maior volume e criticidade.</li>
        """
    
    # Adicionar recomendação para cada fornecedor crítico
    for fc in fornecedores_criticos:
        html_conclusoes += f"""
                        <li class="mb-2">Implementar plano de desenvolvimento com <strong>{fc['nome']}</strong>, com metas claras para melhoria de desempenho.</li>
        """
        
        if fc['scoreFinal'] < 60:
            html_conclusoes += f"""
                        <li class="mb-2">Considerar buscar fornecedores alternativos para os itens atualmente fornecidos por <strong>{fc['nome']}</strong> caso não haja melhoria em 60 dias.</li>
            """
    
    html_conclusoes += """
                    </ol>
                </div>
            </div>
        </div>
    </div>
    """
    
    return html_conclusoes

def formatar_data_brasil(data_str):
    """
    Formata uma data no formato YYYY-MM-DD para DD/MM/YYYY
    
    Args:
        data_str (str): Data no formato YYYY-MM-DD
        
    Returns:
        str: Data formatada como DD/MM/YYYY
    """
    try:
        data = datetime.strptime(data_str, '%Y-%m-%d')
        return data.strftime('%d/%m/%Y')
    except:
        return data_str

def get_recebimentos_por_periodo(data_inicio, data_fim):
    """
    Obtém recebimentos dentro de um período específico
    
    Args:
        data_inicio (str): Data de início no formato YYYY-MM-DD
        data_fim (str): Data de fim no formato YYYY-MM-DD
        
    Returns:
        list: Lista de recebimentos no período
    """
    try:
        # Converter strings para objetos date
        inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        # Executar consulta SQL
        sqlite3.Cursor.execute("""
            SELECT r.*, f.nome as fornecedor_nome 
            FROM recebimentos r
            JOIN fornecedores f ON r.fornecedor_id = f.id
            WHERE r.data_recebimento BETWEEN %s AND %s
            ORDER BY r.data_recebimento DESC
        """, (inicio, fim))
        
        # Obter resultados
        columns = [desc[0] for desc in sqlite3.Cursor.description]
        recebimentos = [dict(zip(columns, row)) for row in sqlite3.Cursor.fetchall()]
        
        return recebimentos
    except Exception as e:
        print(f"Erro ao buscar recebimentos por período: {str(e)}")
        return []

def gerar_conteudo_relatorio_comparativo(data_inicio, data_fim, data_inicio_comparativo=None, data_fim_comparativo=None):
    """Gera o HTML com o relatório comparativo de fornecedores."""
    # Buscar todos os recebimentos no período
    recebimentos = get_recebimentos_por_periodo(data_inicio, data_fim)
    
    # Se não há recebimentos no período
    if not recebimentos:
        return "<div class='alert alert-warning'><i class='fas fa-exclamation-circle me-2'></i>Não há recebimentos no período selecionado.</div>"
    
    # Agrupar recebimentos por fornecedor
    fornecedores = {}
    
    for recebimento in recebimentos:
        fornecedor_id = recebimento['fornecedor_id']
        if fornecedor_id not in fornecedores:
            sqlite3.Cursor.execute("SELECT nome FROM fornecedores WHERE id = %s", (fornecedor_id,))
            result = sqlite3.Cursor.fetchone()
            nome_fornecedor = result[0] if result else "Fornecedor desconhecido"
            
            fornecedores[fornecedor_id] = {
                'nome': nome_fornecedor,
                'recebimentos': [],
                'total': 0,
                'aprovados': 0,
                'reprovados': 0,
                'no_prazo': 0,
                'atrasados': 0
            }
        
        fornecedores[fornecedor_id]['recebimentos'].append(recebimento)
        fornecedores[fornecedor_id]['total'] += 1
        
        # Contar aprovações
        if recebimento['status'] == 'Aprovado':
            fornecedores[fornecedor_id]['aprovados'] += 1
        elif recebimento['status'] == 'Reprovado':
            fornecedores[fornecedor_id]['reprovados'] += 1
            
        # Contar pontualidade
        if recebimento['pontualidade'] == 'No prazo':
            fornecedores[fornecedor_id]['no_prazo'] += 1
        elif recebimento['pontualidade'] == 'Atrasado':
            fornecedores[fornecedor_id]['atrasados'] += 1
    
    # Calcular métricas para cada fornecedor
    avaliacoes = []
    
    for fornecedor_id, dados in fornecedores.items():
        # Pular fornecedores com menos de 3 recebimentos no período (amostra muito pequena)
        if dados['total'] < 3:
            continue
            
        percentual_aprovacao = round((dados['aprovados'] / dados['total']) * 100) if dados['total'] > 0 else 0
        percentual_pontualidade = round((dados['no_prazo'] / dados['total']) * 100) if dados['total'] > 0 else 0
        
        # Cálculo do score final (média ponderada)
        score_final = round((percentual_aprovacao * 0.6) + (percentual_pontualidade * 0.4))
        
        avaliacoes.append({
            'id': fornecedor_id,
            'nome': dados['nome'],
            'total': dados['total'],
            'aprovados': dados['aprovados'],
            'reprovados': dados['reprovados'],
            'noPrazo': dados['no_prazo'],
            'atrasados': dados['atrasados'],
            'percentualAprovacao': percentual_aprovacao,
            'percentualPontualidade': percentual_pontualidade,
            'scoreFinal': score_final
        })
    
    # Ordenar por score final (decrescente)
    avaliacoes.sort(key=lambda x: x['scoreFinal'], reverse=True)
    
    # Se não há fornecedores com dados suficientes
    if not avaliacoes:
        return "<div class='alert alert-warning'><i class='fas fa-exclamation-circle me-2'></i>Não há fornecedores com recebimentos suficientes no período para análise (mínimo 3 recebimentos).</div>"
    
    # Gerar o HTML do relatório
    include_chart = len(avaliacoes) >= 3  # Incluir gráfico somente se houver pelo menos 3 fornecedores
    html_relatorio = gerar_relatorio_comparativo(avaliacoes, include_chart)
    
    # Adicionar cabeçalho com informações do período
    html_header = f'''
    <div class="alert alert-light border shadow-sm mb-4">
        <h5 class="mb-2"><i class="fas fa-calendar-alt me-2"></i>Período da Análise</h5>
        <p class="mb-0">De <strong>{formatar_data_brasil(data_inicio)}</strong> até <strong>{formatar_data_brasil(data_fim)}</strong></p>
        <p class="small text-muted mt-2 mb-0">Análise baseada em <strong>{sum(f['total'] for f in avaliacoes)}</strong> recebimentos de <strong>{len(avaliacoes)}</strong> fornecedores.</p>
    </div>
    '''
    
    return html_header + html_relatorio

@app.route('/relatorio_comparativo', methods=['GET', 'POST'])
def relatorio_comparativo():
    if request.method == 'POST':
        data_inicio = request.form.get('data_inicio')
        data_fim = request.form.get('data_fim')
        
        if not data_inicio or not data_fim:
            flash('Por favor, selecione o período para o relatório.', 'warning')
            return redirect(url_for('relatorio_comparativo'))
        
        # Gerar conteúdo do relatório
        conteudo_relatorio = gerar_conteudo_relatorio_comparativo(data_inicio, data_fim)
        
        return render_template('relatorio_analise_comparativo.html', 
                               conteudo_relatorio=conteudo_relatorio,
                               data_inicio=data_inicio,
                               data_fim=data_fim)
    
    return render_template('relatorio_analise_comparativo.html',
                          conteudo_relatorio=None,
                          data_inicio=None,
                          data_fim=None)

@app.route('/admin/api-keys', methods=['GET'])
@admin_required
def admin_api_keys():
    """Página para gerenciar as chaves API do sistema"""
    # Carregar valores atuais das variáveis de ambiente
    telegram_token = os.getenv("TELEGRAM_TOKEN", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    allowed_users = os.getenv("ALLOWED_USERS", "[]")
    bot_mode = os.getenv("BOT_MODE", "DUAL")
    
    # Formatar allowed_users para exibição no formulário
    # Se for um JSON array válido, converter para string separada por vírgulas
    try:
        users_array = json.loads(allowed_users)
        allowed_users_formatted = ", ".join(users_array)
    except:
        allowed_users_formatted = allowed_users.strip('[]"\'').replace('"', '').replace("'", "")
    
    return render_template(
        'admin_api_keys.html', 
        telegram_token=telegram_token,
        openai_api_key=openai_api_key,
        allowed_users=allowed_users_formatted,
        bot_mode=bot_mode,
        success_msg=request.args.get('success_msg', '')
    )

@app.route('/admin/update-api-keys', methods=['POST'])
@admin_required
def admin_update_api_keys():
    """Atualiza as chaves API no arquivo .env"""
    if request.method == 'POST':
        # Obter valores do formulário
        telegram_token = request.form.get('telegram_token', '')
        openai_api_key = request.form.get('openai_api_key', '')
        allowed_users = request.form.get('allowed_users', '')
        bot_mode = request.form.get('bot_mode', 'DUAL')
        
        # Formatar lista de usuários para JSON
        user_list = [user.strip() for user in allowed_users.split(",") if user.strip()]
        user_json = json.dumps(user_list)
        
        try:
            # Configurações para o arquivo .env
            env_content = f"""# Configurações do bot de Telegram
TELEGRAM_TOKEN={telegram_token}

# Chave OpenAI para usar com os modos OPENAI ou DUAL
OPENAI_API_KEY={openai_api_key}

# Lista de IDs de usuários autorizados a usar o bot
ALLOWED_USERS={user_json}

# Modo de operação do bot (LOCAL, OPENAI, ou DUAL)
BOT_MODE={bot_mode}
"""
            # Escrever no arquivo .env
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(env_content)
                
            # Atualizar as variáveis de ambiente da aplicação atual
            os.environ["TELEGRAM_TOKEN"] = telegram_token
            os.environ["OPENAI_API_KEY"] = openai_api_key
            os.environ["ALLOWED_USERS"] = user_json
            os.environ["BOT_MODE"] = bot_mode
                
            success_msg = "Chaves API atualizadas com sucesso!"
            return redirect(url_for('admin_api_keys', success_msg=success_msg))
            
        except Exception as e:
            flash(f'Erro ao atualizar as chaves API: {str(e)}', 'danger')
            return redirect(url_for('admin_api_keys'))

@app.route('/admin/bot-control', methods=['GET', 'POST'])
@admin_required
def admin_bot_control():
    """Página para controlar o bot de Telegram"""
    # Verificar se o bot está em execução
    import subprocess
    
    # Função para verificar se o processo do bot está rodando
    def is_bot_running():
        try:
            # Executa o comando para listar processos python
            if os.name == 'nt':  # Windows
                # Usar o comando WMIC que é mais confiável para encontrar processos por linha de comando
                # Isso busca todos os processos Python que estão executando o script run_telegram_bot.py
                cmd = 'wmic process where "name=\'python.exe\' and commandline like \'%run_telegram_bot.py%\'" get processid'
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, _ = proc.communicate()
                output = output.decode('utf-8', errors='ignore').strip()
                
                # Se encontrar algum PID além do cabeçalho, o bot está rodando
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                if len(lines) > 1:  # Primeira linha é o cabeçalho "ProcessId"
                    return True
                
                # Método alternativo: verificar usando tasklist
                cmd = 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /V'
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, _ = proc.communicate()
                output = output.decode('utf-8', errors='ignore').strip()
                
                # Verificar se há alguma linha com run_telegram_bot.py
                for line in output.split('\n'):
                    if 'run_telegram_bot.py' in line:
                        return True
                
                # Para instalações do Telegram Bot como serviço do Windows
                cmd = 'sc query "TelegramBot" | find "RUNNING"'
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, _ = proc.communicate()
                if 'RUNNING' in output.decode('utf-8', errors='ignore'):
                    return True
                
                return False
            else:  # Linux/Unix
                # Método mais confiável para Linux: pgrep
                cmd = 'pgrep -f "python.*run_telegram_bot.py"'
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                output = proc.stdout.read().decode('utf-8', errors='ignore').strip()
                
                if output:  # Se encontrou algum PID
                    return True
                
                # Método alternativo: ps
                proc = subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE)
                output = proc.stdout.read().decode('utf-8', errors='ignore')
                if 'run_telegram_bot.py' in output:
                    return True
                
                # Verificar se está rodando como serviço systemd
                cmd = 'systemctl is-active telegram-bot.service'
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output = proc.stdout.read().decode('utf-8', errors='ignore').strip()
                if output == 'active':
                    return True
                
                return False
        except Exception as e:
            print(f'Erro ao verificar o status do bot: {str(e)}')
            return False
    
    # Verificar PID do bot para controle
    def get_bot_pid():
        try:
            if os.name == 'nt':  # Windows
                # Usar WMIC para obter PID de forma mais confiável
                cmd = 'wmic process where "name=\'python.exe\' and commandline like \'%run_telegram_bot.py%\'" get processid'
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, _ = proc.communicate()
                output = output.decode('utf-8', errors='ignore').strip()
                
                # Extrair o primeiro PID encontrado
                lines = [line.strip() for line in output.split('\n') if line.strip()]
                if len(lines) > 1:  # Primeira linha é o cabeçalho "ProcessId"
                    return lines[1]  # Retorna o primeiro PID
                
                # Método alternativo: tasklist
                cmd = 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /V'
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, _ = proc.communicate()
                output = output.decode('utf-8', errors='ignore')
                
                for line in output.strip().split('\n'):
                    if 'run_telegram_bot.py' in line:
                        # O formato CSV tem aspas em volta de cada campo
                        parts = line.split('","')
                        if len(parts) >= 2:
                            # O PID é o segundo campo (índice 1)
                            return parts[1].strip('"')
                
                return None
            else:  # Linux/Unix
                # Método mais confiável: pgrep
                cmd = 'pgrep -f "python.*run_telegram_bot.py"'
                proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                output = proc.stdout.read().decode('utf-8', errors='ignore').strip()
                
                if output:
                    # Retorna o primeiro PID encontrado
                    return output.split('\n')[0]
                
                return None
        except Exception as e:
            print(f'Erro ao obter PID do bot: {str(e)}')
            return None
    
    # Processar ações de POST
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'start':
            # Iniciar o bot
            try:
                # Primeiro verifique se o bot já está rodando e mate qualquer instância existente
                pid = get_bot_pid()
                if pid:
                    if os.name == 'nt':  # Windows
                        subprocess.call(['taskkill', '/PID', pid, '/F', '/T'], shell=True)
                    else:  # Linux/Unix
                        subprocess.call(['kill', pid])
                
                # Agora inicie uma nova instância
                if os.name == 'nt':  # Windows
                    # Inicia de forma simples como um processo em segundo plano
                    subprocess.Popen(['python', 'run_telegram_bot.py'], 
                                    stdout=open('telegram_bot.log', 'a'), 
                                    stderr=open('telegram_bot_error.log', 'a'), 
                                    shell=True, 
                                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:  # Linux/Unix
                    # Inicia o processo em background no Linux
                    subprocess.Popen(['nohup', 'python', 'run_telegram_bot.py', '&'], 
                                    stdout=open('telegram_bot.log', 'a'), 
                                    stderr=open('telegram_bot_error.log', 'a'))
                
                flash('Bot iniciado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao iniciar o bot: {str(e)}', 'danger')
        
        elif action == 'stop':
            # Parar o bot
            try:
                pid = get_bot_pid()
                if pid:
                    if os.name == 'nt':  # Windows
                        subprocess.call(['taskkill', '/PID', pid, '/F'], shell=True)
                    else:  # Linux/Unix
                        subprocess.call(['kill', pid])
                    flash('Bot parado com sucesso!', 'success')
                else:
                    flash('Bot não está em execução.', 'info')
            except Exception as e:
                flash(f'Erro ao parar o bot: {str(e)}', 'danger')
        
        elif action == 'restart':
            # Reiniciar o bot
            try:
                # Tenta parar primeiro
                pid = get_bot_pid()
                if pid:
                    if os.name == 'nt':  # Windows
                        subprocess.call(['taskkill', '/PID', pid, '/F'], shell=True)
                    else:  # Linux/Unix
                        subprocess.call(['kill', pid])
                
                # Espera um pouco para garantir que o processo anterior terminou
                import time
                time.sleep(1)
                
                # Inicia o bot
                if os.name == 'nt':  # Windows
                    subprocess.Popen(['python', 'run_telegram_bot.py'], 
                                   stdout=open('telegram_bot.log', 'a'), 
                                   stderr=open('telegram_bot_error.log', 'a'), 
                                   shell=True, 
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:  # Linux/Unix
                    subprocess.Popen(['nohup', 'python', 'run_telegram_bot.py', '&'], 
                                   stdout=open('telegram_bot.log', 'a'), 
                                   stderr=open('telegram_bot_error.log', 'a'))
                
                flash('Bot reiniciado com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao reiniciar o bot: {str(e)}', 'danger')
    
    # Obter o status do bot
    bot_running = is_bot_running()
    
    # Carregar valores atuais das variáveis de ambiente
    telegram_token = os.getenv("TELEGRAM_TOKEN", "")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    allowed_users = os.getenv("ALLOWED_USERS", "[]")
    bot_mode = os.getenv("BOT_MODE", "DUAL")
    
    # Verificar se as chaves estão configuradas
    keys_configured = bool(telegram_token and (openai_api_key or bot_mode == "LOCAL") and allowed_users != "[]")
    
    return render_template(
        'admin_bot_control.html', 
        bot_running=bot_running,
        keys_configured=keys_configured,
        bot_mode=bot_mode
    )

@app.route('/api/fornecedor/<int:id>/recebimentos/count', methods=['GET'])
@login_required
def contar_recebimentos_fornecedor(id):
    """Retorna a contagem de recebimentos de um fornecedor"""
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) as total FROM recebimentos WHERE fornecedor_id = ?', (id,)).fetchone()['total']
    conn.close()
    
    return jsonify({'count': count})

if __name__ == '__main__':
    # Configuração para desenvolvimento (quando executado diretamente)
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True)
    # Configuração para produção (quando executado via Gunicorn/uWSGI)
    else:
        app.run(host='0.0.0.0', port=5000, debug=False)