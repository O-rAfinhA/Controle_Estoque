import sqlite3
import os
import sys

def reset_database():
    """Limpa completamente o banco de dados e recria com a estrutura correta"""
    print("Iniciando limpeza do banco de dados...")
    
    # Remover o arquivo de banco de dados existente se ele existir
    if os.path.exists('estoque.db'):
        os.remove('estoque.db')
        print("Arquivo de banco de dados existente removido.")
    
    # Criar uma nova conexão (isso criará um novo arquivo)
    conn = sqlite3.connect('estoque.db')
    cursor = conn.cursor()
    
    print("Criando estrutura do banco de dados...")
    
    # Criar tabela usuarios
    cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            admin INTEGER DEFAULT 0,
            status TEXT DEFAULT 'aprovado',
            data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("- Tabela 'usuarios' criada")
    
    # Criar tabela componentes
    cursor.execute('''
        CREATE TABLE componentes (
            codigo TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    print("- Tabela 'componentes' criada")
    
    # Criar tabela transacoes
    cursor.execute('''
        CREATE TABLE transacoes (
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
    print("- Tabela 'transacoes' criada")
    
    # Criar tabela produtos
    cursor.execute('''
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT
        )
    ''')
    print("- Tabela 'produtos' criada")
    
    # Criar tabela componentes_produto
    cursor.execute('''
        CREATE TABLE componentes_produto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            codigo_componente TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos (id),
            FOREIGN KEY (codigo_componente) REFERENCES componentes (codigo)
        )
    ''')
    print("- Tabela 'componentes_produto' criada")
    
    # Criar tabela producoes
    cursor.execute('''
        CREATE TABLE producoes (
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
    print("- Tabela 'producoes' criada")
    
    # Criar tabela fornecedores
    cursor.execute('''
        CREATE TABLE fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            cnpj TEXT UNIQUE NOT NULL,
            email TEXT,
            telefone TEXT,
            data_cadastro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("- Tabela 'fornecedores' criada")
    
    # Criar tabela recebimentos
    cursor.execute('''
        CREATE TABLE recebimentos (
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
    print("- Tabela 'recebimentos' criada")
    
    # Criar tabela solicitacoes_senha
    cursor.execute('''
        CREATE TABLE solicitacoes_senha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            data_solicitacao TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'pendente',
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    print("- Tabela 'solicitacoes_senha' criada")
    
    conn.commit()
    conn.close()
    
    print("\nBanco de dados foi limpo e recriado com sucesso!")

if __name__ == "__main__":
    reset_database() 