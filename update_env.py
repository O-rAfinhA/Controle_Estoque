#!/usr/bin/env python
# Script para atualizar o arquivo .env com configurações

import os
import getpass

# Solicitar dados do usuário
print("Configuração das variáveis de ambiente para o bot")
print("=================================================")

telegram_token = getpass.getpass("Digite o token do bot do Telegram: ")
openai_key = getpass.getpass("Digite sua chave da API OpenAI: ")
allowed_users = input("Digite os IDs de usuários autorizados (separados por vírgula): ")
bot_mode = input("Digite o modo de operação do bot (LOCAL, OPENAI, ou DUAL) [DUAL]: ") or "DUAL"

# Formatar lista de usuários
user_list = [user.strip() for user in allowed_users.split(",") if user.strip()]
user_json = str(user_list).replace("'", '"')

# Configurações
env_content = f"""# Configurações do bot de Telegram
TELEGRAM_TOKEN={telegram_token}

# Chave OpenAI para usar com os modos OPENAI ou DUAL
OPENAI_API_KEY={openai_key}

# Lista de IDs de usuários autorizados a usar o bot
ALLOWED_USERS={user_json}

# Modo de operação do bot (LOCAL, OPENAI, ou DUAL)
BOT_MODE={bot_mode}
"""

# Escrever no arquivo
with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)

print("Arquivo .env atualizado com sucesso!")
print("ATENÇÃO: Nunca compartilhe ou envie o arquivo .env para o GitHub.") 