#!/usr/bin/env python
"""
Script para iniciar o bot de Telegram do sistema de gestão de estoque
"""

import os
import sys
import json
import argparse
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_env_variables():
    """Configura as variáveis de ambiente para o bot"""
    # Carregar variáveis do arquivo .env se existir
    load_dotenv()
    
    # Verificar variáveis necessárias
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    allowed_users = os.getenv("ALLOWED_USERS")
    bot_mode = os.getenv("BOT_MODE", "LOCAL")
    
    if not telegram_token:
        telegram_token = input("Digite o token do bot do Telegram: ").strip()
        os.environ["TELEGRAM_TOKEN"] = telegram_token
    
    if not openai_key and (bot_mode == "OPENAI" or bot_mode == "DUAL"):
        openai_key = input("Digite a chave da API OpenAI: ").strip()
        os.environ["OPENAI_API_KEY"] = openai_key
    
    if not allowed_users:
        user_id = input("Digite seu ID de usuário do Telegram: ").strip()
        os.environ["ALLOWED_USERS"] = json.dumps([user_id])
    
    if not bot_mode:
        os.environ["BOT_MODE"] = "LOCAL"
    
    # Confirmar configuração
    logger.info("Variáveis de ambiente configuradas com sucesso")

def save_env_file(args):
    """Salva as variáveis de ambiente em um arquivo .env"""
    if not args.save_env:
        return
    
    env_content = [
        "# Configurações do bot de Telegram",
        f"TELEGRAM_TOKEN={os.getenv('TELEGRAM_TOKEN', '')}",
        f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}",
        f"ALLOWED_USERS={os.getenv('ALLOWED_USERS', '[]')}",
        f"BOT_MODE={os.getenv('BOT_MODE', 'LOCAL')}"
    ]
    
    with open(".env", "w") as f:
        f.write("\n".join(env_content))
    
    logger.info("Arquivo .env salvo com as configurações")

def start_bot():
    """Inicia o bot do Telegram"""
    try:
        # Importa aqui para garantir que as variáveis de ambiente estão configuradas
        from telegram_bot import main
        
        logger.info("Iniciando bot do Telegram...")
        main()
    except ImportError as e:
        logger.error(f"Erro ao importar módulo do bot: {e}")
        logger.error("Verifique se todas as dependências estão instaladas: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro ao iniciar o bot: {e}")
        sys.exit(1)

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Inicia o bot de Telegram para o sistema de gestão de estoque")
    parser.add_argument("--save-env", action="store_true", help="Salva as configurações em um arquivo .env")
    parser.add_argument("--setup-only", action="store_true", help="Configura variáveis de ambiente sem iniciar o bot")
    parser.add_argument("--mode", choices=["LOCAL", "OPENAI", "DUAL"], default=None, help="Define o modo de operação do bot")
    args = parser.parse_args()
    
    try:
        # Configurar modo de operação se especificado
        if args.mode:
            os.environ["BOT_MODE"] = args.mode
        
        # Configurar variáveis de ambiente
        setup_env_variables()
        
        # Salvar arquivo .env se solicitado
        save_env_file(args)
        
        # Encerrar se for apenas configuração
        if args.setup_only:
            logger.info("Configuração concluída. Use --save-env para salvar as configurações.")
            return
        
        # Iniciar o bot
        start_bot()
        
    except KeyboardInterrupt:
        logger.info("Processo interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 