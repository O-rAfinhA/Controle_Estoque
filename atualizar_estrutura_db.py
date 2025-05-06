import sqlite3
from database import get_db_connection

def adicionar_coluna_origem_transacoes():
    """Adiciona a coluna 'origem' à tabela 'transacoes' se ela não existir"""
    conn = get_db_connection()
    try:
        # Verifica se a coluna já existe
        colunas = conn.execute("PRAGMA table_info(transacoes)").fetchall()
        colunas_nomes = [coluna['name'] for coluna in colunas]
        
        print(f"Colunas existentes na tabela 'transacoes': {colunas_nomes}")
        
        if 'origem' not in colunas_nomes:
            print("Adicionando coluna 'origem' à tabela 'transacoes'...")
            conn.execute("ALTER TABLE transacoes ADD COLUMN origem TEXT")
            conn.commit()
            print("Coluna 'origem' adicionada com sucesso!")
        else:
            print("Coluna 'origem' já existe na tabela 'transacoes'")
        
        # Verifica novamente a estrutura da tabela
        colunas_atualizadas = conn.execute("PRAGMA table_info(transacoes)").fetchall()
        colunas_nomes_atualizadas = [coluna['name'] for coluna in colunas_atualizadas]
        print(f"Colunas atualizadas na tabela 'transacoes': {colunas_nomes_atualizadas}")
        
    except Exception as e:
        print(f"Erro ao adicionar coluna 'origem': {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    adicionar_coluna_origem_transacoes() 