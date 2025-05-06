from flask import Flask
from flask_caching import Cache
import os
from datetime import datetime, timedelta

# Inicialização da extensão de cache
cache = Cache()

def create_app(test_config=None):
    """
    Função factory para criação da aplicação Flask
    """
    # Criar e configurar a aplicação
    app = Flask(__name__, instance_relative_config=True)
    
    # Configurações padrão
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_replace_in_production'),
        DATABASE=os.path.join(app.instance_path, 'estoque.db'),
        CACHE_TYPE='SimpleCache',
        CACHE_DEFAULT_TIMEOUT=300,  # 5 minutos
        TIMEZONE_OFFSET=-3  # Fuso horário de São Paulo (UTC-3)
    )
    
    # Carregar configurações de teste ou produção
    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)
    
    # Inicializar cache
    cache.init_app(app)
    
    # Garantir que o diretório de instância existe
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Registrar funções de utilidade para templates
    from functools import wraps
    
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
    
    # Função para verificar se o usuário é administrador (para uso em templates)
    def is_admin():
        if 'user_id' not in session:
            return False
        
        conn = get_db_connection()
        usuario = conn.execute('SELECT admin FROM usuarios WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        
        return usuario and usuario['admin']
    
    # Registrar funções para uso em templates
    @app.context_processor
    def utility_processor():
        def now_adjusted():
            # Ajustar a data/hora para o fuso horário configurado
            offset = app.config['TIMEZONE_OFFSET']
            now = datetime.utcnow() + timedelta(hours=offset)
            return now
        
        return {
            'now_adjusted': now_adjusted,
            'is_admin': is_admin
        }
    
    # Filtros personalizados
    @app.template_filter('formatdatetime')
    def format_datetime(value, format='%d/%m/%Y às %H:%Mh'):
        if not value:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
        
        offset = app.config['TIMEZONE_OFFSET']
        value = value + timedelta(hours=offset)
        return value.strftime(format)
    
    # Registrar blueprints
    # Importações dentro da função para evitar problemas de importação circular
    from database import init_db
    
    # Registrar API blueprint
    from api_routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Inicializar banco de dados
    with app.app_context():
        init_db()
        
        # Inicializar tabelas para o sistema de avaliação de fornecedores
        from database import get_db_connection
        
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
    
    # Registrar rota de dashboard
    @app.route('/')
    def index():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        conn = get_db_connection()
        
        # Total de componentes
        total_componentes = conn.execute('SELECT COUNT(*) FROM componentes').fetchone()[0]
        
        # Componentes com estoque crítico (<=5) e baixo (<=20)
        estoque_critico = conn.execute('SELECT COUNT(*) FROM componentes WHERE quantidade <= 5').fetchone()[0]
        estoque_baixo = conn.execute('SELECT COUNT(*) FROM componentes WHERE quantidade > 5 AND quantidade <= 20').fetchone()[0]
        
        # Total de transações nos últimos 30 dias
        data_limite = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        total_transacoes = conn.execute(
            'SELECT COUNT(*) FROM transacoes WHERE data >= ?', 
            (data_limite,)
        ).fetchone()[0]
        
        # Entradas e saídas nos últimos 30 dias
        entradas = conn.execute(
            'SELECT COUNT(*) FROM transacoes WHERE tipo = "entrada" AND data >= ?', 
            (data_limite,)
        ).fetchone()[0]
        
        saidas = conn.execute(
            'SELECT COUNT(*) FROM transacoes WHERE tipo = "saida" AND data >= ?', 
            (data_limite,)
        ).fetchone()[0]
        
        # Componentes críticos para exibição na tabela
        componentes_criticos = conn.execute(
            'SELECT codigo, nome, quantidade FROM componentes WHERE quantidade <= 5 ORDER BY quantidade ASC'
        ).fetchall()
        
        conn.close()
        
        return render_template('dashboard.html',
                               total_componentes=total_componentes,
                               estoque_critico=estoque_critico,
                               estoque_baixo=estoque_baixo,
                               total_transacoes=total_transacoes,
                               entradas=entradas,
                               saidas=saidas,
                               componentes_criticos=componentes_criticos)
    
    # Importar e registrar outras rotas
    from flask import render_template, session, redirect, url_for, flash, request
    
    # Adicionar o resto do código do app.py original aqui
    # Importado da aplicação original
    
    return app 