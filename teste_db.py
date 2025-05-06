from database import get_db_connection
import random

def testar_inserir_componente():
    """Testa a inserção de um componente no banco de dados"""
    # Gera um código aleatório para evitar conflitos
    codigo = str(random.randint(10000, 99999))
    nome = f"Componente Teste {codigo}"
    quantidade = 10
    
    print(f"Tentando inserir: Código={codigo}, Nome={nome}, Quantidade={quantidade}")
    
    conn = get_db_connection()
    try:
        # Insere o componente
        conn.execute('INSERT INTO componentes (codigo, nome, quantidade) VALUES (?, ?, ?)',
                    (codigo, nome, quantidade))
        conn.commit()
        print("Inserção bem-sucedida!")
        
        # Verifica se o componente foi inserido
        componente = conn.execute('SELECT * FROM componentes WHERE codigo = ?', 
                                (codigo,)).fetchone()
        
        if componente:
            print(f"Componente encontrado: Código={componente['codigo']}, Nome={componente['nome']}, Quantidade={componente['quantidade']}")
        else:
            print("ERRO: Componente não encontrado após inserção!")
    except Exception as e:
        print(f"ERRO ao inserir componente: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    testar_inserir_componente() 