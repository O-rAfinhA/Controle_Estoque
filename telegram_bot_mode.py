#!/usr/bin/env python
# Controle de modo para o bot do Telegram

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Modos disponíveis:
# 1. OPENAI - Usa OpenAI API para processamento de linguagem natural (requer chave válida)
# 2. LOCAL - Usa apenas comandos diretos, sem processamento de linguagem natural
# 3. DUAL - Tenta usar OpenAI primeiro, mas se falhar, usa o modo LOCAL como fallback

# O modo DUAL permite tentar usar AI quando possível, mas mantém o bot funcional mesmo com problemas na API

def is_openai_mode():
    """Verifica se o bot está em modo OpenAI"""
    return os.getenv('BOT_MODE', 'LOCAL') == "OPENAI"

def is_local_mode():
    """Verifica se o bot está em modo Local"""
    return os.getenv('BOT_MODE', 'LOCAL') == "LOCAL"

def is_dual_mode():
    """Verifica se o bot está em modo Dual (OpenAI com fallback para Local)"""
    return os.getenv('BOT_MODE', 'LOCAL') == "DUAL" 