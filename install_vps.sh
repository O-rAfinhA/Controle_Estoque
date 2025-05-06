#!/bin/bash

# Script de instalação para o sistema Estoque Agilux em VPS
# Deve ser executado com sudo: sudo bash install_vps.sh

# Cores para saída
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}== Iniciando instalação do Estoque Agilux ==${NC}"

# Verificar se está executando como root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Por favor, execute este script com sudo${NC}"
  exit 1
fi

# Obter o domínio do usuário
echo -e "${YELLOW}Digite o nome de domínio para o sistema (ex: estoque.seudominio.com):${NC}"
read domain_name

# Perguntar se quer instalar SSL com Let's Encrypt
echo -e "${YELLOW}Deseja configurar SSL/HTTPS com Let's Encrypt? (s/n)${NC}"
read configure_ssl

# Atualizar o sistema
echo -e "${GREEN}Atualizando o sistema...${NC}"
apt update && apt upgrade -y

# Instalar dependências
echo -e "${GREEN}Instalando dependências...${NC}"
apt install -y python3 python3-pip python3-venv sqlite3 nginx certbot python3-certbot-nginx

# Criar diretório para a aplicação
echo -e "${GREEN}Configurando diretórios...${NC}"
mkdir -p /var/www/Estoque_Agilux
chown -R www-data:www-data /var/www/Estoque_Agilux

# Perguntar se o código já foi enviado para o servidor
echo -e "${YELLOW}O código já foi enviado para o servidor? (s/n)${NC}"
read code_uploaded

if [ "$code_uploaded" != "s" ]; then
  echo -e "${RED}Por favor, envie o código para o servidor antes de continuar.${NC}"
  echo -e "${YELLOW}Você pode usar scp, git clone ou outro método para copiar os arquivos para /var/www/Estoque_Agilux${NC}"
  exit 1
fi

# Configurar ambiente virtual
echo -e "${GREEN}Configurando ambiente virtual Python...${NC}"
cd /var/www/Estoque_Agilux
python3 -m venv venv
chown -R www-data:www-data /var/www/Estoque_Agilux

# Instalar dependências Python
echo -e "${GREEN}Instalando dependências Python...${NC}"
/var/www/Estoque_Agilux/venv/bin/pip install -r requirements.txt
/var/www/Estoque_Agilux/venv/bin/pip install gunicorn

# Configurar serviços systemd
echo -e "${GREEN}Configurando serviços...${NC}"
cp /var/www/Estoque_Agilux/estoque_agilux.service /etc/systemd/system/
cp /var/www/Estoque_Agilux/telegram_bot.service /etc/systemd/system/

# Habilitar e iniciar serviço da aplicação web
systemctl daemon-reload
systemctl enable estoque_agilux
systemctl start estoque_agilux

# Configurar Nginx
echo -e "${GREEN}Configurando Nginx...${NC}"
cp /var/www/Estoque_Agilux/nginx_estoque_agilux /etc/nginx/sites-available/estoque_agilux

# Substituir o domínio no arquivo de configuração
sed -i "s/seu_dominio.com/$domain_name/g" /etc/nginx/sites-available/estoque_agilux

# Habilitar o site no Nginx
ln -sf /etc/nginx/sites-available/estoque_agilux /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Configurar Let's Encrypt se solicitado
if [ "$configure_ssl" = "s" ]; then
  echo -e "${GREEN}Configurando SSL com Let's Encrypt...${NC}"
  certbot --nginx -d $domain_name
fi

# Configurar o bot do Telegram
echo -e "${GREEN}Configurando o bot do Telegram...${NC}"
echo -e "${YELLOW}Por favor, insira o token do bot do Telegram:${NC}"
read telegram_token

echo -e "${YELLOW}Por favor, insira a chave da API da OpenAI (deixe em branco se não quiser usar):${NC}"
read openai_key

echo -e "${YELLOW}Por favor, insira o seu ID de usuário do Telegram (você pode obter isso enviando /start para @userinfobot no Telegram):${NC}"
read telegram_user_id

# Criar arquivo .env para o bot
cat > /var/www/Estoque_Agilux/.env << EOL
# Configurações do bot de Telegram
TELEGRAM_TOKEN=${telegram_token}
OPENAI_API_KEY=${openai_key}
ALLOWED_USERS=["${telegram_user_id}"]
BOT_MODE=${openai_key:+DUAL}
EOL

# Se a API da OpenAI não foi fornecida, definir como LOCAL
if [ -z "$openai_key" ]; then
  sed -i "s/BOT_MODE=/BOT_MODE=LOCAL/g" /var/www/Estoque_Agilux/.env
fi

# Ajustar permissões
chown www-data:www-data /var/www/Estoque_Agilux/.env
chmod 600 /var/www/Estoque_Agilux/.env

# Iniciar o bot do Telegram
systemctl enable telegram_bot
systemctl start telegram_bot

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Instalação concluída!${NC}"
echo -e "${GREEN}O sistema Estoque Agilux está rodando em: http://$domain_name${NC}"
if [ "$configure_ssl" = "s" ]; then
  echo -e "${GREEN}HTTPS está configurado em: https://$domain_name${NC}"
fi
echo -e "${GREEN}O bot do Telegram está em execução.${NC}"
echo -e "${GREEN}============================================${NC}"

# Mostrar status dos serviços
echo -e "${YELLOW}Status do serviço web:${NC}"
systemctl status estoque_agilux --no-pager

echo -e "${YELLOW}Status do bot:${NC}"
systemctl status telegram_bot --no-pager

echo -e "${GREEN}Pronto! Verifique se tudo está funcionando corretamente.${NC}" 