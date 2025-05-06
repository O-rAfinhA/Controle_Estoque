# Bot de Telegram para Sistema de Gestão de Estoque

Este módulo adiciona um bot de Telegram com IA integrada ao sistema de gestão de estoque, permitindo consultas e interações por meio do aplicativo Telegram.

## Funcionalidades

- Consulta ao estoque por meio de linguagem natural
- Verificação de componentes com nível crítico de estoque
- Consulta à avaliação de fornecedores
- Listagem e detalhamento de produtos
- Integração com a API OpenAI para responder perguntas sobre o sistema

## Requisitos

- Token de bot do Telegram (obtenha via [@BotFather](https://t.me/BotFather))
- Chave da API OpenAI
- Python 3.7+
- Dependências do `requirements.txt`

## Configuração

1. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```

2. Crie um arquivo `.env` na raiz do projeto com as seguintes configurações:
   ```
   # Configurações do Telegram Bot e OpenAI
   TELEGRAM_TOKEN=seu_token_do_telegram_aqui
   OPENAI_API_KEY=sua_chave_da_api_openai_aqui

   # Lista de IDs de usuário do Telegram autorizados a usar o bot (formato JSON)
   # Exemplo: ["123456789", "987654321"]
   ALLOWED_USERS=["seu_id_do_telegram"]
   ```

3. Para obter seu ID do Telegram, você pode enviar uma mensagem para [@userinfobot](https://t.me/userinfobot).

## Execução

Para iniciar o bot, execute:

```bash
python telegram_bot.py
```

O bot deve iniciar e estar disponível no Telegram para os usuários autorizados.

## Comandos disponíveis

- `/start` - Inicia a interação com o bot
- `/help` - Mostra a lista de comandos disponíveis
- `/estoque` - Lista componentes com nível crítico de estoque
- `/fornecedores` - Mostra a avaliação dos fornecedores
- `/produtos` - Lista produtos cadastrados no sistema

## Uso da IA

Além dos comandos, o bot responde a perguntas em linguagem natural sobre o sistema, como:

- "Quantos componentes estão em estoque crítico?"
- "Quais são os melhores fornecedores?"
- "Preciso de informações sobre produção"
- "Qual a média de desempenho dos fornecedores?"

## Segurança

- O bot só responde a usuários cujos IDs estejam na lista `ALLOWED_USERS`
- As informações sensíveis não são compartilhadas
- A comunicação com a API da OpenAI é criptografada

## Solução de Problemas

### O bot não responde

- Verifique se o token do Telegram está correto
- Confirme que seu ID de usuário está na lista de permitidos
- Verifique os logs para mensagens de erro

### Erros na integração com IA

- Confirme que a chave da API OpenAI é válida
- Verifique se há créditos disponíveis na sua conta OpenAI
- Verifique a conectividade com a internet

## Integração com Web Hooks (Opcional)

Para ambientes de produção, você pode configurar um webhook em vez de polling:

1. Configure um servidor com HTTPS
2. Modifique o código em `telegram_bot.py` para usar webhooks
3. Configure o webhook usando a API do Telegram

## Limitações

- O bot só tem acesso às informações presentes no banco de dados local
- Consultas muito específicas podem requerer o uso da interface web
- O modelo de IA tem um limite de tokens por chamada 