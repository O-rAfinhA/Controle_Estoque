# Sistema de Gestão de Estoque Agilux

Um sistema web completo para gerenciamento de estoque de componentes e avaliação de fornecedores, desenvolvido com Flask e SQLite.

## Funcionalidades

- Dashboard interativo com gráficos e métricas
- Gerenciamento completo de componentes (adicionar, editar, excluir)
- Registro de entradas e saídas de estoque
- Histórico de transações
- Sistema de avaliação de fornecedores
- Geração de relatórios e gráficos de desempenho
- Cálculo de componentes para produção
- Interface responsiva e amigável
- Sistema de notificações para itens críticos

## Requisitos

- Python 3.6+
- Flask 2.3+
- SQLite3
- Outras dependências listadas em `requirements.txt`

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Crie e ative um ambiente virtual (recomendado)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:

```bash
python update_env.py
```

O script irá criar um arquivo `.env` solicitando as informações necessárias. **IMPORTANTE**: Este arquivo contém dados sensíveis e não deve ser compartilhado ou enviado para o GitHub.

## Segurança e Chaves API

Para proteger suas chaves API ao utilizar o controle de versão (Git):

1. O arquivo `.gitignore` já está configurado para ignorar o arquivo `.env`
2. Nunca cometa arquivos com chaves API ou tokens diretamente no código
3. As chaves API podem ser gerenciadas de duas formas:
   - Através do painel de administrador na opção "Gerenciar Chaves API"
   - Usando o script `update_env.py` para configurar as variáveis em cada ambiente
4. Não modifique o arquivo `update_env.py` para incluir suas chaves reais

### Gerenciando Chaves API pelo Painel de Administrador

1. Faça login como administrador
2. Acesse o Painel de Administração no menu de usuário
3. Clique em "Gerenciar Chaves API"
4. Configure as chaves do Telegram, OpenAI e usuários autorizados
5. Salve as configurações

## Uso

1. Para iniciar o servidor web:

```bash
python wsgi.py
```

2. Acesse o sistema em seu navegador:

```
http://localhost:5000
```

3. Faça login com as credenciais padrão (se for a primeira vez):
   - Usuário: admin
   - Senha: admin123

## Nova Arquitetura

O sistema foi reestruturado para usar o padrão de fábrica de aplicativos (Application Factory Pattern), melhorando sua organização e facilidade de manutenção:

- `app_factory.py` - Implementação do padrão Factory para criação da aplicação
- `wsgi.py` - Ponto de entrada para servidores WSGI
- `api_routes.py` - Rotas da API para os gráficos e funcionalidades assíncronas
- `static/js/common.js` - Biblioteca de funções JavaScript reutilizáveis
- `static/js/chart-integration.js` - Integração com Chart.js para gráficos interativos

## Integração com Telegram e IA (Novo!)

O sistema agora conta com um bot de Telegram integrado com IA que permite:

- Consultar o sistema remotamente via Telegram
- Receber alertas sobre estoque crítico
- Verificar avaliações de fornecedores
- Obter relatórios e análises
- Fazer perguntas em linguagem natural sobre o sistema

Para configurar o bot:

1. Instale as dependências adicionais:
   ```bash
   pip install -r requirements.txt
   ```

2. Execute o script de configuração:
   ```bash
   python run_telegram_bot.py --save-env
   ```

3. Siga as instruções para configurar seu token do Telegram, chave da API OpenAI e ID do Telegram.

Para mais detalhes, consulte o arquivo `README_TELEGRAM_BOT.md`.

## Melhorias Implementadas

1. **Dashboard Interativo**:
   - Gráficos em tempo real com Chart.js
   - Indicadores de desempenho
   - Listagem de itens críticos

2. **Biblioteca JavaScript**:
   - Sistema de validação de formulários
   - Paginação padronizada
   - Filtros de tabela
   - Notificações toast
   - Funções utilitárias comuns

3. **API RESTful**:
   - Endpoints para dados dos gráficos
   - Sistema de notificações
   - Filtros por período

4. **Segurança e Performance**:
   - Sistema de cache para consultas frequentes
   - Validação de entrada de dados
   - Proteção contra CSRF
   - Controle de acesso por níveis de usuário

5. **UX/UI**:
   - Design moderno e responsivo
   - Tema claro/escuro
   - Feedback visual para ações
   - Navegação aprimorada

6. **Assistente de IA** (Novo!):
   - Integração com a API OpenAI
   - Chat via Telegram para consultas
   - Análises avançadas de dados
   - Notificações inteligentes

## Estrutura do Projeto

- `app_factory.py` - Aplicação Flask usando o padrão Factory
- `wsgi.py` - Ponto de entrada para servidores WSGI
- `api_routes.py` - Rotas da API
- `database.py` - Configuração e funções do banco de dados
- `fornecedores_utils.py` - Funções para o sistema de fornecedores
- `static/` - Arquivos estáticos (CSS, JS, imagens)
  - `js/common.js` - Biblioteca JavaScript comum
  - `js/chart-integration.js` - Integração com Chart.js
- `templates/` - Templates HTML
- `estoque.db` - Banco de dados SQLite

## Capturas de Tela

### Dashboard
![Dashboard](static/img/dashboard.png)

### Lista de Componentes
![Componentes](static/img/componentes.png)

### Avaliação de Fornecedores
![Fornecedores](static/img/fornecedores.png)

## Licença

Este projeto está licenciado sob a licença MIT.
