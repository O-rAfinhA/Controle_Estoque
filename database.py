import sqlite3
import os

DATABASE_PATH = 'estoque.db'

def get_db_connection():
    """Cria uma conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    # Verifica se o banco de dados já existe
    if os.path.exists(DATABASE_PATH):
        return
    
    conn = get_db_connection()
    
    # Cria a tabela de usuários
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cria a tabela de componentes
    conn.execute('''
        CREATE TABLE IF NOT EXISTS componentes (
            codigo TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    
    # Cria a tabela de transações
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_componente TEXT NOT NULL,
            tipo TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            data TIMESTAMP NOT NULL,
            usuario_id INTEGER,
            FOREIGN KEY (codigo_componente) REFERENCES componentes (codigo),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Cria a tabela de produtos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT
        )
    ''')
    
    # Cria a tabela de componentes de produto
    conn.execute('''
        CREATE TABLE IF NOT EXISTS componentes_produto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            codigo_componente TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos (id),
            FOREIGN KEY (codigo_componente) REFERENCES componentes (codigo)
        )
    ''')
    
    # Cria a tabela de produções
    conn.execute('''
        CREATE TABLE IF NOT EXISTS producoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            data TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'Registrada',
            usuario_id INTEGER,
            FOREIGN KEY (produto_id) REFERENCES produtos (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("Banco de dados inicializado com sucesso!")

def importar_dados_existentes(estoque):
    """Importa dados do dicionário de estoque para o banco de dados"""
    conn = get_db_connection()
    
    for codigo, componente in estoque.items():
        # Verifica se o componente já existe
        existente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                               (codigo,)).fetchone()
        
        if not existente:
            conn.execute('INSERT INTO componentes (codigo, nome, quantidade) VALUES (?, ?, ?)',
                        (componente.codigo, componente.nome, componente.quantidade))
    
    conn.commit()
    conn.close()
    
    print("Dados importados com sucesso!")
