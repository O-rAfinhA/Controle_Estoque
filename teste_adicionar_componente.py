import sqlite3
import random
from database import get_db_connection

def testar_adicionar_componente_direto():
    """Testa a inserção direta de um componente no banco de dados, sem passar pelo Flask"""
    # Gera um código aleatório para evitar conflitos
    codigo = str(random.randint(10000, 99999))
    nome = f"Componente Teste Direto {codigo}"
    quantidade = 10
    
    print(f"Tentando inserir diretamente: Código={codigo}, Nome={nome}, Quantidade={quantidade}")
    
    conn = get_db_connection()
    try:
        # Verifica se o código já existe
        existente_codigo = conn.execute('SELECT * FROM componentes WHERE codigo = ?', (codigo,)).fetchone()
        existente_nome = conn.execute('SELECT * FROM componentes WHERE UPPER(nome) = UPPER(?)', (nome,)).fetchone()
        
        if existente_codigo:
            print("Erro: Código já existe")
            return
        elif existente_nome:
            print("Erro: Nome já existe")
            return
        
        # Insere o componente
        conn.execute('INSERT INTO componentes (codigo, nome, quantidade) VALUES (?, ?, ?)',
                    (codigo, nome, quantidade))
        
        # Registra a transação com a coluna origem
        conn.execute('''
            INSERT INTO transacoes (codigo_componente, tipo, quantidade, data, origem) 
            VALUES (?, ?, ?, datetime("now", "localtime"), ?)
        ''', (codigo, 'entrada', quantidade, 'teste_script'))
        
        conn.commit()
        print("Inserção direta bem-sucedida!")
        
        # Verifica se o componente foi inserido
        componente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                                (codigo,)).fetchone()
        
        if componente:
            print(f"Componente encontrado: Código={componente['codigo']}, Nome={componente['nome']}, Quantidade={componente['quantidade']}")
            
            # Verificamos também se a transação foi registrada
            transacao = conn.execute('SELECT * FROM transacoes WHERE codigo_componente = ? ORDER BY id DESC LIMIT 1', 
                                    (codigo,)).fetchone()
            if transacao:
                print(f"Transação registrada: ID={transacao['id']}, Tipo={transacao['tipo']}, Quantidade={transacao['quantidade']}, Origem={transacao['origem']}")
            else:
                print("ALERTA: Transação não encontrada após inserção!")
        else:
            print("ERRO: Componente não encontrado após inserção!")
    except Exception as e:
        print(f"ERRO ao inserir componente: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    testar_adicionar_componente_direto() 