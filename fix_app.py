import re

# Ler o arquivo completo
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontrar todas as ocorrências da definição da função admin_painel
pattern = re.compile(r'@app\.route\(\'/admin/painel\'\)\s*@admin_required\s*def admin_painel\(\):.*?return render_template\(\'admin_painel\.html\',\s*usuarios=usuarios\)', re.DOTALL)
matches = list(pattern.finditer(content))

# Se houver mais de uma ocorrência, remover a segunda
if len(matches) > 1:
    # Extrair os índices de início e fim da segunda ocorrência
    start2 = matches[1].start()
    end2 = matches[1].end()
    
    # Criar um novo conteúdo sem a segunda definição
    new_content = content[:start2] + content[end2+1:]
    
    # Salvar o arquivo corrigido
    with open('app_fixed.py', 'w', encoding='utf-8') as out:
        out.write(new_content)
    
    print('Arquivo app_fixed.py criado com sucesso!')
else:
    print('Não foram encontradas múltiplas definições da função admin_painel.') 