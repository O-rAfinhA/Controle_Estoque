#!/usr/bin/env python
"""
Script para verificar dependências do sistema de gestão de estoque
"""

import os
import sys
import importlib
import logging
import sqlite3
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Mapeamento entre nomes de pacotes e módulos
PACKAGE_TO_MODULE = {
    "flask": "flask",
    "werkzeug": "werkzeug",
    "flask-caching": "flask_caching",
    "flask-login": "flask_login",
    "flask-wtf": "flask_wtf", 
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "reportlab": "reportlab",
    "gunicorn": "gunicorn",
    "pytest": "pytest",
    "python-dotenv": "dotenv",
    "python-telegram-bot": "telegram",
    "openai": "openai",
    "requests": "requests"
}

def check_environment_variables():
    """Verifica se as variáveis de ambiente necessárias estão configuradas"""
    load_dotenv()
    
    logger.info("Verificando variáveis de ambiente...")
    
    missing = []
    
    # Verificar variáveis do Telegram Bot
    if not os.getenv("TELEGRAM_TOKEN"):
        missing.append("TELEGRAM_TOKEN")
    
    if not os.getenv("ALLOWED_USERS"):
        missing.append("ALLOWED_USERS")
    
    # Verificar modo do bot
    bot_mode = os.getenv("BOT_MODE", "LOCAL")
    logger.info(f"Modo do bot configurado para: {bot_mode}")
    
    # Verificar chave da API OpenAI se modo não for LOCAL
    if bot_mode in ["OPENAI", "DUAL"] and not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY (necessário para os modos OPENAI ou DUAL)")
    
    if missing:
        logger.warning(f"Variáveis de ambiente ausentes: {', '.join(missing)}")
        logger.warning("Execute 'python update_env.py' para configurar essas variáveis.")
    else:
        logger.info("Todas as variáveis de ambiente necessárias estão configuradas.")
    
    return len(missing) == 0

def check_required_packages():
    """Verifica se todos os pacotes necessários estão instalados"""
    logger.info("Verificando pacotes necessários...")
    
    missing = []
    for package, module_name in PACKAGE_TO_MODULE.items():
        try:
            importlib.import_module(module_name)
            logger.info(f"✓ {package}")
        except ImportError:
            missing.append(package)
            logger.warning(f"✗ {package} - Não encontrado")
    
    if missing:
        logger.error(f"Pacotes ausentes: {', '.join(missing)}")
        logger.error("Execute 'pip install -r requirements.txt' para instalar os pacotes necessários.")
    else:
        logger.info("Todos os pacotes necessários estão instalados.")
    
    return len(missing) == 0

def check_database():
    """Verifica se o banco de dados existe e está acessível"""
    logger.info("Verificando banco de dados...")
    
    db_path = os.path.join(os.getcwd(), "estoque.db")
    if not os.path.exists(db_path):
        logger.error(f"Banco de dados não encontrado: {db_path}")
        logger.error("Execute 'python init_db_script.py' para inicializar o banco de dados.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se as tabelas principais existem
        tables = [
            "componentes",
            "transacoes",
            "produtos",
            "producoes",
            "usuarios",
            "fornecedores"
        ]
        
        missing_tables = []
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            logger.warning(f"Tabelas ausentes: {', '.join(missing_tables)}")
            logger.warning("O banco de dados parece estar incompleto ou corrompido.")
        else:
            logger.info("Banco de dados verificado e todas as tabelas necessárias encontradas.")
        
        conn.close()
        return len(missing_tables) == 0
    
    except sqlite3.Error as e:
        logger.error(f"Erro ao acessar o banco de dados: {e}")
        return False

def main():
    """Função principal"""
    logger.info("Verificando dependências do sistema de gestão de estoque...")
    
    # Verificar Python
    python_version = sys.version.split()[0]
    logger.info(f"Python versão: {python_version}")
    
    # Verificar SQLite
    sqlite_version = sqlite3.sqlite_version
    logger.info(f"SQLite versão: {sqlite_version}")
    
    # Verificar pacotes
    packages_ok = check_required_packages()
    
    # Verificar variáveis de ambiente
    env_ok = check_environment_variables()
    
    # Verificar banco de dados
    db_ok = check_database()
    
    # Resultado final
    if packages_ok and env_ok and db_ok:
        logger.info("Todas as verificações passaram! O sistema está pronto para uso.")
        return 0
    else:
        logger.warning("Algumas verificações falharam. Corrija os problemas antes de continuar.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 