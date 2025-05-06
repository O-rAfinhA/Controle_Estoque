import sqlite3
from database import DATABASE_PATH
from werkzeug.security import generate_password_hash
import os

def migrar_banco_dados():
    """Migra o banco de dados para incluir o sistema de aprovação de usuários e recuperação de senha"""
    print("Iniciando migração do banco de dados...")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"Erro: Banco de dados não encontrado em '{DATABASE_PATH}'")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    # Verifica se a tabela de usuários já existe
    usuario_table_exists = conn.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='usuarios'
    ''').fetchone()
    
    # Se a tabela não existir, cria com os campos necessários
    if not usuario_table_exists:
        print("Criando tabela de usuários...")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                data_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'aprovado',
                admin BOOLEAN NOT NULL DEFAULT 0
            )
        ''')
        
        # Cria um usuário administrador padrão
        print("Criando usuário administrador padrão...")
        conn.execute('''
            INSERT INTO usuarios (nome, senha, status, admin)
            VALUES (?, ?, ?, ?)
        ''', ('Administrador', generate_password_hash('admin123'), 'aprovado', 1))
    else:
        # Se a tabela já existe, verifica se os campos necessários existem
        usuarios_info = conn.execute('PRAGMA table_info(usuarios)').fetchall()
        
        # Verifica se os campos status e admin existem
        status_exists = any(col['name'] == 'status' for col in usuarios_info)
        admin_exists = any(col['name'] == 'admin' for col in usuarios_info)
        
        # Adiciona os campos se não existirem
        if not status_exists:
            print("Adicionando coluna status à tabela usuarios...")
            conn.execute('ALTER TABLE usuarios ADD COLUMN status TEXT NOT NULL DEFAULT "aprovado"')
        
        if not admin_exists:
            print("Adicionando coluna admin à tabela usuarios...")
            conn.execute('ALTER TABLE usuarios ADD COLUMN admin BOOLEAN NOT NULL DEFAULT 0')
            
            # Define o primeiro usuário como administrador
            primeiro_usuario = conn.execute('SELECT id FROM usuarios ORDER BY id LIMIT 1').fetchone()
            if primeiro_usuario:
                conn.execute('UPDATE usuarios SET admin = 1 WHERE id = ?', (primeiro_usuario['id'],))
                print(f"Usuário ID {primeiro_usuario['id']} definido como administrador.")
    
    # Cria a tabela de solicitações de redefinição de senha se não existir
    solicitacoes_exists = conn.execute('''
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='solicitacoes_senha'
    ''').fetchone()
    
    if not solicitacoes_exists:
        print("Criando tabela de solicitações de redefinição de senha...")
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
    
    conn.commit()
    
    # Verifica e mostra informações sobre o administrador
    admin = conn.execute('SELECT * FROM usuarios WHERE admin = 1 LIMIT 1').fetchone()
    if admin:
        print(f"Administrador configurado: {admin['nome']} (ID: {admin['id']})")
    
    conn.close()
    print("Migração do banco de dados concluída com sucesso!")

if __name__ == "__main__":
    migrar_banco_dados()