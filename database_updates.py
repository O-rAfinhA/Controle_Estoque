from database import get_db_connection

def update_database():
    conn = get_db_connection()
    
    # Adicionar o campo 'origem' à tabela transacoes
    conn.executescript('''
    -- Criar tabela temporária
    CREATE TABLE transacoes_temp (
        id INTEGER,
        codigo_componente TEXT,
        tipo TEXT,
        quantidade INTEGER,
        data TEXT,
        usuario_id INTEGER
    );
    
    -- Copiar dados para a tabela temporária
    INSERT INTO transacoes_temp 
    SELECT id, codigo_componente, tipo, quantidade, data, usuario_id 
    FROM transacoes;
    
    -- Remover a tabela original
    DROP TABLE transacoes;
    
    -- Criar a nova tabela com o campo 'origem'
    CREATE TABLE transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_componente TEXT,
        tipo TEXT,
        quantidade INTEGER,
        data TEXT,
        usuario_id INTEGER,
        origem TEXT
    );
    
    -- Copiar os dados de volta, definindo todas as transações existentes como NULL para origem
    INSERT INTO transacoes (id, codigo_componente, tipo, quantidade, data, usuario_id, origem)
    SELECT id, codigo_componente, tipo, quantidade, data, usuario_id, NULL
    FROM transacoes_temp;
    
    -- Remover a tabela temporária
    DROP TABLE transacoes_temp;
    ''')
    
    conn.commit()
    conn.close()
    
    print("Atualização do banco de dados concluída com sucesso!")

if __name__ == "__main__":
    update_database()