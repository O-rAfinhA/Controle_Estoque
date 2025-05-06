# Guia de Implantação do Estoque Agilux em VPS

Este guia detalha os passos necessários para implantar o sistema Estoque Agilux e o bot do Telegram em um servidor VPS.

## Requisitos

- Servidor VPS com Ubuntu 20.04 ou mais recente
- Domínio apontado para o IP do servidor
- Acesso SSH ao servidor com privilégios de administrador

## Método Automatizado (Recomendado)

Preparamos um script de instalação que configura automaticamente todos os componentes necessários.

### Passos:

1. **Copie o código para a VPS**

   ```bash
   # De sua máquina local, usando rsync ou scp
   rsync -av --exclude venv --exclude __pycache__ --exclude .git /caminho/local/Estoque_Agilux/ usuario@servidor:/tmp/Estoque_Agilux/
   
   # Na VPS
   sudo mkdir -p /var/www/Estoque_Agilux
   sudo cp -r /tmp/Estoque_Agilux/* /var/www/Estoque_Agilux/
   sudo chown -R www-data:www-data /var/www/Estoque_Agilux
   ```

2. **Execute o script de instalação**

   ```bash
   cd /var/www/Estoque_Agilux
   sudo bash install_vps.sh
   ```

3. **Siga as instruções do script**
   - Informe o nome de domínio
   - Escolha se deseja configurar SSL com Let's Encrypt
   - Forneça o token do bot do Telegram
   - Informe a chave da API da OpenAI (opcional)
   - Forneça o seu ID de usuário do Telegram

O script irá:
- Instalar todas as dependências
- Configurar o ambiente Python
- Configurar o Nginx
- Configurar o certificado SSL (se solicitado)
- Configurar e iniciar os serviços para a aplicação web e o bot do Telegram

## Método Manual

Se preferir configurar manualmente, siga estes passos:

### 1. Preparar o Servidor

```bash
# Atualizar o sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y python3 python3-pip python3-venv sqlite3 nginx certbot python3-certbot-nginx
```

### 2. Configurar a Aplicação Web

```bash
# Criar diretório
sudo mkdir -p /var/www/Estoque_Agilux

# Copiar arquivos
# (use rsync, scp ou git clone para copiar os arquivos)

# Configurar ambiente virtual
cd /var/www/Estoque_Agilux
sudo python3 -m venv venv
sudo chown -R www-data:www-data /var/www/Estoque_Agilux
sudo -u www-data /var/www/Estoque_Agilux/venv/bin/pip install -r requirements.txt
sudo -u www-data /var/www/Estoque_Agilux/venv/bin/pip install gunicorn
```

### 3. Configurar o Serviço da Aplicação Web

```bash
# Copiar arquivo de serviço
sudo cp /var/www/Estoque_Agilux/estoque_agilux.service /etc/systemd/system/

# Habilitar e iniciar o serviço
sudo systemctl daemon-reload
sudo systemctl enable estoque_agilux
sudo systemctl start estoque_agilux
```

### 4. Configurar Nginx

```bash
# Copiar a configuração
sudo cp /var/www/Estoque_Agilux/nginx_estoque_agilux /etc/nginx/sites-available/estoque_agilux

# Editar o arquivo para definir o domínio correto
sudo sed -i "s/seu_dominio.com/seu-dominio-real.com/g" /etc/nginx/sites-available/estoque_agilux

# Habilitar o site
sudo ln -sf /etc/nginx/sites-available/estoque_agilux /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Configurar SSL (opcional)

```bash
sudo certbot --nginx -d seu-dominio-real.com
```

### 6. Configurar o Bot do Telegram

```bash
# Criar arquivo .env
sudo nano /var/www/Estoque_Agilux/.env
```

Adicione ao arquivo .env:
```
# Configurações do bot de Telegram
TELEGRAM_TOKEN=seu_token_do_telegram
OPENAI_API_KEY=sua_chave_da_openai
ALLOWED_USERS=["seu_id_telegram"]
BOT_MODE=DUAL
```

```bash
# Ajustar permissões
sudo chown www-data:www-data /var/www/Estoque_Agilux/.env
sudo chmod 600 /var/www/Estoque_Agilux/.env

# Configurar o serviço do bot
sudo cp /var/www/Estoque_Agilux/telegram_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable telegram_bot
sudo systemctl start telegram_bot
```

## Verificar a Instalação

```bash
# Verificar o status do serviço web
sudo systemctl status estoque_agilux

# Verificar o status do bot
sudo systemctl status telegram_bot

# Verificar os logs
sudo journalctl -u estoque_agilux -f
sudo journalctl -u telegram_bot -f
```

## Solução de Problemas

1. **A aplicação web não inicia**:
   - Verifique os logs: `sudo journalctl -u estoque_agilux -f`
   - Verifique as permissões: `sudo chown -R www-data:www-data /var/www/Estoque_Agilux`

2. **O bot do Telegram não funciona**:
   - Verifique os logs: `sudo journalctl -u telegram_bot -f`
   - Verifique o arquivo .env: `sudo cat /var/www/Estoque_Agilux/.env`
   - Reinicie o serviço: `sudo systemctl restart telegram_bot`

3. **Erro no Nginx**:
   - Verifique a sintaxe: `sudo nginx -t`
   - Verifique os logs: `sudo tail /var/log/nginx/error.log`

4. **Problemas com SSL**:
   - Verifique se o domínio está apontando corretamente para o servidor
   - Execute novamente: `sudo certbot --nginx -d seu-dominio-real.com`

## Manutenção

### Atualização do Sistema

```bash
# Atualizar o código
# (copie os novos arquivos para /var/www/Estoque_Agilux)

# Reiniciar os serviços
sudo systemctl restart estoque_agilux
sudo systemctl restart telegram_bot
```

### Backup

```bash
# Backup do banco de dados
sudo cp /var/www/Estoque_Agilux/data.db /var/backups/estoque_agilux_db_$(date +%Y%m%d).db

# Backup de toda a aplicação
sudo tar -czf /var/backups/estoque_agilux_full_$(date +%Y%m%d).tar.gz -C /var/www Estoque_Agilux
``` 