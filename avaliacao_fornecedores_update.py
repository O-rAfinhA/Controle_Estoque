from database import get_db_connection

def update_database_fornecedores():
    """Atualiza o banco de dados com as tabelas necessárias para avaliação de fornecedores"""
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
    
    print("Tabelas para avaliação de fornecedores criadas com sucesso!")

if __name__ == "__main__":
    update_database_fornecedores() 