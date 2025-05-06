# Sistema de Avaliação de Fornecedores

Este módulo adiciona funcionalidades de avaliação de fornecedores ao sistema de controle de estoque existente.

## Funcionalidades

- Cadastro e gerenciamento de fornecedores
- Registro de recebimentos de materiais
- Avaliação de fornecedores com base em métricas de pontualidade e qualidade
- Análise de desempenho e rankings
- Relatórios e exportação de dados

## Instalação

1. Certifique-se de que o sistema principal de controle de estoque está funcionando corretamente
2. Adicione os novos arquivos no diretório do projeto:
   - `fornecedores_utils.py` - Funções utilitárias para o sistema de avaliação
   - `avaliacao_fornecedores_update.py` - Script para atualizar o banco de dados
   - Templates HTML nas pastas correspondentes

3. Inicialize as tabelas do banco de dados acessando a rota `/init-db-fornecedores` (requer login de administrador)

## Como Usar

1. Acesse o sistema através do menu "Avaliação de Fornecedores"
2. Cadastre os fornecedores na aba "Fornecedores"
3. Registre os recebimentos de materiais na aba "Recebimento de Materiais"
4. Visualize as avaliações automáticas na aba "Avaliação de Fornecedores"
5. Analise o desempenho e tendências na aba "Análise de Desempenho"
6. Exporte relatórios na aba "Relatórios"

## Métricas de Avaliação

O sistema avalia os fornecedores com base em duas métricas principais:

1. **Pontualidade** - Porcentagem de entregas realizadas dentro do prazo
   - Meta: 85%
   - Cálculo: (Total de entregas no prazo / Total de entregas) × 100

2. **Qualidade** - Porcentagem de produtos recebidos em conformidade total
   - Meta: 85%
   - Cálculo: (Total de aprovações 100% / Total de recebimentos) × 100

3. **Score Final** - Média entre pontualidade e qualidade
   - Cálculo: (Pontualidade + Qualidade) / 2

## Integração com o Menu Principal

Para adicionar um link para o sistema de avaliação de fornecedores no menu principal, adicione o seguinte código no template base.html:

```html
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('avaliacao_fornecedores') }}">
        <i class="fas fa-star-half-alt"></i> Avaliação de Fornecedores
    </a>
</li>
```

## Solução de Problemas

- Se as tabelas não forem criadas corretamente, verifique o arquivo `avaliacao_fornecedores_update.py`
- Para reiniciar as tabelas, acesse a rota `/init-db-fornecedores` novamente
- Em caso de problemas com as consultas, verifique o arquivo `fornecedores_utils.py` 