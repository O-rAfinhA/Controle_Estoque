import sqlite3
import sys

def check_and_fix_users_table():
    """Verifica e corrige a estrutura da tabela usuarios"""
    print("Verificando estrutura da tabela usuarios...")
    conn = sqlite3.connect('estoque.db')
    cursor = conn.cursor()
    
    # Verificar se a tabela usuarios existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
    if not cursor.fetchone():
        print("Tabela usuarios não existe, criando...")
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
        conn.commit()
        print("Tabela usuarios criada com sucesso!")
    else:
        # Verificar se a coluna status existe
        cursor.execute("PRAGMA table_info(usuarios)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'status' not in column_names:
            print("Coluna 'status' não encontrada, adicionando...")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN status TEXT DEFAULT 'aprovado'")
            conn.commit()
            print("Coluna 'status' adicionada com sucesso!")
        else:
            print("Coluna 'status' já existe, nenhuma ação necessária.")
    
    print("\nEstrutura atual da tabela usuarios:")
    cursor.execute("PRAGMA table_info(usuarios)")
    columns = cursor.fetchall()
    for column in columns:
        print(f"  - {column[1]} ({column[2]}), nulo: {column[3]}, padrão: {column[4]}")
    
    conn.close()
    print("\nVerificação concluída!")

if __name__ == "__main__":
    check_and_fix_users_table() 