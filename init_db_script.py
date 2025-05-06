import sqlite3
import sys

def init_database():
    """Initialize the database with all required tables"""
    print("Initializing database...")
    sys.stdout.flush()
    
    conn = sqlite3.connect('estoque.db')
    
    # Create the users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            admin INTEGER DEFAULT 0,
            status TEXT DEFAULT 'aprovado',
            data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("- Created usuarios table")
    sys.stdout.flush()
    
    # Create the components table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS componentes (
            codigo TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    print("- Created componentes table")
    sys.stdout.flush()
    
    # Create the transactions table
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
    print("- Created transacoes table")
    sys.stdout.flush()
    
    # Create the products table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT
        )
    ''')
    print("- Created produtos table")
    sys.stdout.flush()
    
    # Create the product components table
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
    print("- Created componentes_produto table")
    sys.stdout.flush()
    
    # Create the productions table
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
    print("- Created producoes table")
    sys.stdout.flush()
    
    # Create the suppliers table
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
    print("- Created fornecedores table")
    sys.stdout.flush()
    
    # Create the receipts table
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
    print("- Created recebimentos table")
    sys.stdout.flush()
    
    # Create the password recovery requests table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_senha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            data_solicitacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pendente',
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    print("- Created solicitacoes_senha table")
    sys.stdout.flush()
    
    conn.commit()
    conn.close()
    
    print("Database initialization complete!")
    sys.stdout.flush()

if __name__ == "__main__":
    init_database() 