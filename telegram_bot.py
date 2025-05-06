import os
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import OpenAI
from dotenv import load_dotenv
from database import get_db_connection
from fornecedores_utils import (
    get_fornecedores, get_recebimentos, calcular_avaliacoes, 
    calcular_ranking_fornecedores
)
from telegram_assistant_utils import (
    get_estoque_stats, get_fornecedores_stats, get_transacoes_recentes, get_producao_stats,
    consultar_componente, consultar_produto, consultar_fornecedor,
    get_system_context_data, format_system_context,
    analisar_tendencias_estoque, analisar_desempenho_fornecedores,
    consultar_cliente
)
from telegram_bot_mode import is_openai_mode, is_local_mode, is_dual_mode

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Obter tokens das variáveis de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALLOWED_USERS = json.loads(os.getenv("ALLOWED_USERS", "[]"))

# Cliente da API OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Verificação de usuários permitidos
def is_authorized(user_id):
    """Verifica se o usuário está autorizado a usar o bot"""
    return str(user_id) in ALLOWED_USERS

# Comandos do bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mensagem de boas-vindas quando o usuário inicia o bot"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if not is_authorized(user_id):
        await update.message.reply_text(f"Eita! Você não tá autorizado a usar este bot. Seu ID é {user_id}")
        return
    
    mensagem = f"""
E aí, {user_name}! 👋

Sou o assistente do sistema de gestão de estoque. Posso te ajudar com:

• Ver componentes com estoque crítico
• Consultar status de fornecedores
• Buscar informações de produtos
• E muito mais!

Use /help para ver todos os comandos disponíveis.
"""
    
    # Verificar modo de operação
    modo = os.getenv('BOT_MODE', 'LOCAL')
    
    if modo == 'OPENAI' or modo == 'DUAL':
        mensagem += "\nVocê também pode me fazer perguntas diretamente em português! 🤖"
    
    await update.message.reply_text(mensagem)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra a lista de comandos disponíveis"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Eita! Você não tá autorizado a usar este bot. Seu ID é {user_id}")
        return
    
    help_text = """
*Comandos Disponíveis:*

📊 *Estoque e Componentes:*
/estoque - Mostra componentes com estoque crítico
/estoque\_completo - Mostra todos os componentes em estoque
/componente \[código/nome\] - Busca detalhes de um componente específico
/transacoes \[dias\] - Mostra transações recentes (padrão: 7 dias)

🏭 *Produção e Produtos:*
/produtos - Lista os produtos disponíveis
/produto \[id/nome\] - Busca detalhes de um produto específico
/producoes - Mostra produções em andamento e recentes

📈 *Análises e Relatórios:*
/analise\_estoque - Análise de tendências de estoque
/analise\_fornecedores - Análise de desempenho de fornecedores

🏢 *Fornecedores e Clientes:*
/fornecedores - Mostra avaliação dos fornecedores
/cliente \[nome\] - Busca informações de um cliente específico
"""
    
    # Modo de operação atual
    modo = os.getenv('BOT_MODE', 'LOCAL')
    modo_text = f"\n\n🤖 *Modo atual:* {modo}"
    
    if modo == 'OPENAI' or modo == 'DUAL':
        modo_text += "\nAlém dos comandos, você também pode me fazer perguntas em linguagem natural!"
    
    # Enviar mensagem de ajuda
    try:
        await update.message.reply_text(help_text + modo_text, parse_mode='Markdown')
    except Exception as e:
        # Se falhar com Markdown, tenta enviar sem formatação
        logger.error(f"Erro ao enviar mensagem formatada: {e}")
        await update.message.reply_text(help_text + modo_text)

async def estoque_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra itens com estoque crítico"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Eita! Você não tá autorizado a usar este bot. Seu ID é {user_id}")
        return
    
    try:
        # Usar a função avançada de estatísticas de estoque
        stats = get_estoque_stats()
        componentes_criticos = stats['componentes_criticos']
        
        if not componentes_criticos:
            await update.message.reply_text("Opa, que beleza! Não temos nenhum componente com estoque crítico agora. 🎉")
            return
        
        mensagem = "🚨 *Componentes com estoque crítico:*\n\n"
        for comp in componentes_criticos:
            mensagem += f"• *{comp['nome']}* (Código: {comp['codigo']})\n"
            mensagem += f"  Quantidade: *{comp['quantidade']}* unidades\n\n"
        
        # Adicionar resumo
        mensagem += f"📊 *Resumão do Estoque:*\n"
        mensagem += f"- Total de componentes: {stats['total']}\n"
        mensagem += f"- Componentes críticos: {stats['critico']}\n"
        mensagem += f"- Componentes com estoque baixo: {stats['baixo']}\n"
        mensagem += f"- Componentes com estoque normal: {stats['normal']}\n"
        
        # Adicionar instrução para usar /estoque_completo
        mensagem += f"\nPara ver a lista completa de componentes, manda um /estoque\\_completo aí"
        
        try:
            await update.message.reply_text(mensagem, parse_mode='Markdown')
        except Exception as e:
            # Se falhar com Markdown, tenta enviar sem formatação
            logger.error(f"Erro ao enviar mensagem formatada: {e}")
            await update.message.reply_text(mensagem.replace('*', '').replace('_', ''))
    
    except Exception as e:
        logger.error(f"Erro ao obter estoque crítico: {e}")
        await update.message.reply_text(f"Putz, deu ruim ao buscar as informações: {str(e)}")

async def estoque_completo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra lista completa de todos os componentes em estoque"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Desculpe, você não está autorizado a usar este bot. ID: {user_id}")
        return
    
    try:
        # Obter estatísticas completas do estoque
        stats = get_estoque_stats()
        
        if stats['total'] == 0:
            await update.message.reply_text("Não há componentes cadastrados no sistema.")
            return
        
        mensagem = "📦 *Listagem Completa de Estoque:*\n\n"
        
        # Componentes críticos
        if stats['componentes_criticos']:
            mensagem += "*Componentes com estoque crítico (<100 unidades):*\n\n"
            for comp in stats['componentes_criticos']:
                mensagem += f"• *{comp['nome']}* (Código: {comp['codigo']})\n"
                mensagem += f"  Estoque: *{comp['quantidade']}* un. | Status: 🔴 CRÍTICO\n\n"
        
        # Componentes baixos
        if stats['componentes_baixo']:
            mensagem += "*Componentes com estoque baixo (100-299 unidades):*\n\n"
            for comp in stats['componentes_baixo']:
                mensagem += f"• *{comp['nome']}* (Código: {comp['codigo']})\n"
                mensagem += f"  Estoque: *{comp['quantidade']}* un. | Status: 🟡 BAIXO\n\n"
        
        # Componentes normais
        if stats['componentes_normal']:
            mensagem += "*Componentes com estoque normal (≥300 unidades):*\n\n"
            for comp in stats['componentes_normal']:
                mensagem += f"• *{comp['nome']}* (Código: {comp['codigo']})\n"
                mensagem += f"  Estoque: *{comp['quantidade']}* un. | Status: 🟢 NORMAL\n\n"
            
        # Limitar o tamanho da mensagem (Telegram tem limite de 4096 caracteres)
        if len(mensagem) > 3800:
            mensagem = mensagem[:3700] + "\n\n... e mais componentes. Use /componente <código> para detalhes específicos."
        
        # Adicionar resumo
        mensagem += f"\n📊 *Resumo do Estoque:*\n"
        mensagem += f"- Total de componentes: {stats['total']}\n"
        mensagem += f"- Componentes críticos: {stats['critico']}\n"
        mensagem += f"- Componentes com estoque baixo: {stats['baixo']}\n"
        mensagem += f"- Componentes com estoque normal: {stats['normal']}\n"
        
        # Adicionar instrução para detalhes
        mensagem += f"\nPara ver detalhes de um componente específico, use:\n/componente <código ou nome>"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao listar componentes: {e}")
        await update.message.reply_text(f"Erro ao obter informações: {str(e)}")

async def transacoes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra transações recentes"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Eita! Você não tá autorizado a usar este bot. Seu ID é {user_id}")
        return
    
    try:
        # Definir período padrão (7 dias) ou usar argumento fornecido
        dias = 7
        if context.args and len(context.args) > 0:
            try:
                dias = int(context.args[0])
            except ValueError:
                await update.message.reply_text("O número de dias deve ser um número inteiro. Usando o padrão de 7 dias.")
        
        # Buscar transações
        transacoes = get_transacoes_recentes(dias=dias, limite=15)
        
        if not transacoes:
            await update.message.reply_text(f"Não foram encontradas transações nos últimos {dias} dias.")
            return
        
        # Formatar mensagem
        mensagem = f"🔄 *Transações dos últimos {dias} dias:*\n\n"
        
        for t in transacoes:
            tipo_emoji = "📥" if t['tipo'] == 'entrada' else "📤"
            tipo_texto = "ENTRADA" if t['tipo'] == 'entrada' else "SAÍDA"
            data_formatada = t.get('data_formatada', t['data'])
            usuario = t.get('usuario', 'Sistema')
            mensagem += f"{tipo_emoji} *{tipo_texto}:* {t['componente']} (Cód: {t['codigo_componente']})\n"
            mensagem += f"   📊 Quantidade: {t['quantidade']} unidades\n"
            mensagem += f"   🕒 Data/Hora: {data_formatada}\n"
            mensagem += f"   👤 Responsável: {usuario}\n\n"
        
        # Adicionar rodapé
        mensagem += f"Total: {len(transacoes)} transações encontradas."
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao obter transações: {str(e)}")
        await update.message.reply_text(f"Erro ao obter informações: {str(e)}")

async def fornecedores_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra avaliação dos fornecedores"""
    if not is_authorized(update.effective_user.id):
        return
    
    try:
        # Obter estatísticas de fornecedores
        fornecedores_stats = get_fornecedores_stats()
        
        if fornecedores_stats['total'] == 0:
            await update.message.reply_text("Não há dados de avaliação de fornecedores disponíveis.")
            return
        
        mensagem = "📊 *Avaliação de Fornecedores:*\n\n"
        
        # Adicionar melhores fornecedores
        mensagem += "*Melhores Fornecedores:*\n"
        for i, fornecedor in enumerate(fornecedores_stats['top_5'][:5], 1):
            status = "✅ BOM" if fornecedor['scoreFinal'] >= 85 else "⚠️ CRÍTICO"
            mensagem += f"{i}. *{fornecedor['nome']}*\n"
            mensagem += f"   Score: *{fornecedor['scoreFinal']}%* ({status})\n"
            mensagem += f"   Aprovação: {fornecedor['percentualAprovacao']}%\n"
            mensagem += f"   Pontualidade: {fornecedor['percentualPontualidade']}%\n\n"
        
        # Adicionar fornecedores críticos (se houver)
        if fornecedores_stats['criticos'] > 0:
            mensagem += "*Fornecedores Críticos:*\n"
            for i, fornecedor in enumerate(fornecedores_stats['bottom_5'], 1):
                if fornecedor['scoreFinal'] < 85:
                    mensagem += f"{i}. *{fornecedor['nome']}*\n"
                    mensagem += f"   Score: *{fornecedor['scoreFinal']}%* ⚠️\n"
                    mensagem += f"   Aprovação: {fornecedor['percentualAprovacao']}%\n"
                    mensagem += f"   Pontualidade: {fornecedor['percentualPontualidade']}%\n\n"
        
        # Adicionar resumo
        mensagem += f"\n*Resumo:*\n"
        mensagem += f"- Total de fornecedores: {fornecedores_stats['total']}\n"
        mensagem += f"- Fornecedores com bom desempenho: {fornecedores_stats['bons']}\n"
        mensagem += f"- Fornecedores críticos: {fornecedores_stats['criticos']}\n"
        mensagem += f"- Score médio: {fornecedores_stats['media_score']}%\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao obter avaliação de fornecedores: {e}")
        await update.message.reply_text(f"Erro ao obter informações: {str(e)}")

async def produtos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista os produtos disponíveis"""
    if not is_authorized(update.effective_user.id):
        return
    
    conn = get_db_connection()
    produtos = conn.execute('SELECT id, nome, descricao FROM produtos ORDER BY nome').fetchall()
    conn.close()
    
    if not produtos:
        await update.message.reply_text("Não há produtos cadastrados no sistema.")
        return
    
    # Criar teclado inline para selecionar produtos
    keyboard = []
    for i, produto in enumerate(produtos[:10]):  # Limitar a 10 produtos para não sobrecarregar
        keyboard.append([
            InlineKeyboardButton(produto['nome'], callback_data=f"produto_{produto['id']}")
        ])
    
    # Adicionar botão para pesquisar produtos
    keyboard.append([
        InlineKeyboardButton("🔍 Pesquisar produto específico", callback_data="search_produto")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Selecione um produto para ver detalhes:", 
        reply_markup=reply_markup
    )

async def componente_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca detalhes de um componente específico"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Desculpe, você não está autorizado a usar este bot. ID: {user_id}")
        return
    
    # Verificar se foi fornecido um código/nome
    if not context.args:
        await update.message.reply_text(
            "Por favor, forneça o código ou nome do componente.\n"
            "Exemplo: /componente 123 ou /componente resistor"
        )
        return
    
    codigo_ou_nome = ' '.join(context.args)
    
    try:
        # Buscar componente
        componente = consultar_componente(codigo_ou_nome)
        
        if not componente:
            await update.message.reply_text(f"Componente '{codigo_ou_nome}' não encontrado.")
            return
        
        # Formatar mensagem
        mensagem = f"📦 *Componente: {componente['nome']}*\n"
        mensagem += f"Código: `{componente['codigo']}`\n"
        mensagem += f"Quantidade em estoque: *{componente['quantidade']}* unidades\n"
        
        # Status do estoque
        status = "🔴 Crítico" if componente['quantidade'] < 100 else ("🟡 Baixo" if componente['quantidade'] < 300 else "🟢 Normal")
        mensagem += f"Status: {status}\n\n"
        
        # Estatísticas gerais
        if 'total_entradas' in componente:
            mensagem += "*Estatísticas:*\n"
            mensagem += f"- Total já entregue: {componente['total_entradas']} unidades\n"
            mensagem += f"- Total já consumido: {componente['total_saidas']} unidades\n"
            mensagem += f"- Movimento por: {componente['total_usuarios']} usuários\n"
            mensagem += f"- Total de transações: {componente['total_transacoes']}\n\n"
        
        # Produtos que usam este componente
        if componente['produtos']:
            mensagem += "*Utilizado nos produtos:*\n"
            for produto in componente['produtos']:
                mensagem += f"- {produto['nome']} (Qtd. necessária: {produto['quantidade']} un.)\n"
        else:
            mensagem += "*Não está associado a nenhum produto.*\n"
        
        # Histórico de transações
        if componente['transacoes']:
            mensagem += "\n*Últimas transações:*\n"
            for transacao in componente['transacoes']:
                tipo = "➕ Entrada" if transacao['tipo'] == 'entrada' else "➖ Saída"
                usuario = transacao['usuario'] or "Sistema"
                data = transacao.get('data_formatada', transacao['data'])
                
                mensagem += f"- {tipo}: {transacao['quantidade']} un. ({data})\n"
                mensagem += f"  Por: {usuario}\n"
        
        # Adicionar informação sobre como ver todas as transações
        mensagem += "\nPara ver todas as transações recentes, use `/transacoes`"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao consultar componente: {e}")
        await update.message.reply_text(f"Erro ao buscar informações: {str(e)}")

async def produto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Busca detalhes de um produto específico"""
    if not is_authorized(update.effective_user.id):
        return
    
    # Verificar se foi fornecido um ID/nome
    if not context.args:
        await update.message.reply_text(
            "Por favor, forneça o ID ou nome do produto.\n"
            "Exemplo: /produto 5 ou /produto placa"
        )
        return
    
    nome_ou_id = ' '.join(context.args)
    
    try:
        # Buscar produto
        produto = consultar_produto(nome_ou_id)
        
        if not produto:
            await update.message.reply_text(f"Produto '{nome_ou_id}' não encontrado.")
            return
        
        # Formatar mensagem
        mensagem = f"🔍 *Produto: {produto['nome']}*\n"
        if produto['descricao']:
            mensagem += f"Cliente/Descrição: {produto['descricao']}\n"
        
        # Status de produção
        status_producao = "✅ Disponível para produção" if produto['disponivel_producao'] else "❌ Componentes insuficientes"
        mensagem += f"Status: {status_producao}\n\n"
        
        # Componentes necessários
        mensagem += "*Componentes necessários:*\n"
        for comp in produto['componentes']:
            disponibilidade = "✅" if comp['estoque'] >= comp['quantidade'] else "❌"
            mensagem += f"- {comp['nome']} (Código: {comp['codigo']})\n"
            mensagem += f"  Qtd. necessária: {comp['quantidade']} | Em estoque: {comp['estoque']} {disponibilidade}\n"
        
        # Histórico de produções
        if produto['producoes']:
            mensagem += "\n*Últimas produções:*\n"
            for producao in produto['producoes']:
                data = producao['data']
                try:
                    # Formatar a data se for string
                    if isinstance(data, str):
                        data = datetime.strptime(data, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
                except:
                    pass
                usuario = producao['usuario'] or 'Sistema'
                mensagem += f"- {producao['quantidade']} unidades ({data}) por {usuario}\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao consultar produto: {e}")
        await update.message.reply_text(f"Erro ao buscar informações: {str(e)}")

async def analise_estoque_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra análise de tendências do estoque"""
    if not is_authorized(update.effective_user.id):
        return
    
    # Informar ao usuário que a análise está sendo gerada
    await update.message.reply_text("Gerando análise de tendências do estoque... ⏳")
    
    try:
        # Período padrão: 30 dias
        dias = 30
        if context.args and context.args[0].isdigit():
            dias = int(context.args[0])
            if dias > 365:
                dias = 365  # Limitar a 1 ano
        
        # Gerar análise
        analise = analisar_tendencias_estoque(dias)
        
        if analise['status'] == 'empty':
            await update.message.reply_text(analise['message'])
            return
        
        # Construir mensagem
        mensagem = f"📊 *Análise de Tendências do Estoque - Últimos {dias} dias*\n\n"
        
        periodo = analise['periodo']
        mensagem += f"*Período analisado:* {periodo['inicio']} a {periodo['fim']} ({periodo['dias']} dias)\n\n"
        
        # Totais
        totais = analise['totais']
        mensagem += f"*Movimentação total:*\n"
        mensagem += f"➕ Entradas: {totais['entradas']} unidades\n"
        mensagem += f"➖ Saídas: {totais['saidas']} unidades\n"
        mensagem += f"🔄 Saldo: {totais['saldo']} unidades\n\n"
        
        # Componentes mais movimentados
        top_componentes = analise['top_componentes']
        mensagem += "*Componentes mais movimentados:*\n"
        for i, comp in enumerate(top_componentes, 1):
            mensagem += f"{i}. *{comp['nome']}* (Código: {comp['codigo']})\n"
            mensagem += f"   ➕ Entradas: {comp['entrada']} | ➖ Saídas: {comp['saida']} | 🔄 Total: {comp['total']}\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro na análise de estoque: {e}")
        await update.message.reply_text(f"Erro ao gerar análise: {str(e)}")

async def analise_fornecedores_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra análise de desempenho dos fornecedores"""
    if not is_authorized(update.effective_user.id):
        return
    
    # Informar ao usuário que a análise está sendo gerada
    await update.message.reply_text("Gerando análise de desempenho dos fornecedores... ⏳")
    
    try:
        # Período padrão: 90 dias
        dias = 90
        if context.args and context.args[0].isdigit():
            dias = int(context.args[0])
            if dias > 365:
                dias = 365  # Limitar a 1 ano
        
        # Gerar análise
        analise = analisar_desempenho_fornecedores(dias)
        
        if analise['status'] == 'empty':
            await update.message.reply_text(analise['message'])
            return
        
        # Construir mensagem
        mensagem = f"📊 *Análise de Desempenho dos Fornecedores - Últimos {dias} dias*\n\n"
        
        # Métricas
        metricas = analise['metricas']
        mensagem += f"*Resumo:*\n"
        mensagem += f"- Total de recebimentos: {metricas['total_recebimentos']}\n"
        mensagem += f"- Fornecedores ativos: {metricas['total_fornecedores']}\n"
        mensagem += f"- Fornecedores críticos: {metricas['fornecedores_criticos']}\n"
        mensagem += f"- Score médio: {metricas['media_score']}%\n\n"
        
        # Top 5 fornecedores
        fornecedores = analise['fornecedores']
        mensagem += "*Melhores fornecedores:*\n"
        for i, f in enumerate(fornecedores[:5], 1):
            status = "✅" if f['score'] >= 85 else "⚠️"
            mensagem += f"{i}. *{f['nome']}* ({status} {f['score']}%)\n"
            mensagem += f"   Qualidade: {f['qualidade']}% | Pontualidade: {f['pontualidade']}%\n"
            mensagem += f"   Recebimentos: {f['total']}\n"
        
        # Enviar a primeira parte da mensagem se for muito longa
        if len(mensagem) > 3000:
            await update.message.reply_text(mensagem, parse_mode='Markdown')
            mensagem = ""
        
        # Fornecedores críticos (se houver)
        fornecedores_criticos = [f for f in fornecedores if f['score'] < 85]
        if fornecedores_criticos:
            mensagem += "\n*Fornecedores críticos:*\n"
            for i, f in enumerate(fornecedores_criticos[:5], 1):
                mensagem += f"{i}. *{f['nome']}* (⚠️ {f['score']}%)\n"
                mensagem += f"   Qualidade: {f['qualidade']}% | Pontualidade: {f['pontualidade']}%\n"
                mensagem += f"   Aprovados: {f['aprovado']} | Rejeitados: {f['rejeitado']} | Condicionais: {f['condicional']}\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro na análise de fornecedores: {e}")
        await update.message.reply_text(f"Erro ao gerar análise: {str(e)}")

async def produto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa callback de seleção de produto"""
    if not is_authorized(update.callback_query.from_user.id):
        return
    
    query = update.callback_query
    await query.answer()
    
    # Se for solicitação de pesquisa
    if query.data == "search_produto":
        context.user_data["esperando_produto"] = True
        await query.edit_message_text(
            "Digite o nome ou ID do produto que deseja buscar:",
            reply_markup=None
        )
        return
    
    # Se for seleção de produto
    produto_id = query.data.split('_')[1]
    
    try:
        # Usar a função avançada para consultar produto
        produto = consultar_produto(produto_id)
        
        if not produto:
            await query.edit_message_text("Produto não encontrado.")
            return
        
        # Formatar mensagem
        mensagem = f"🔍 *Produto: {produto['nome']}*\n"
        if produto['descricao']:
            mensagem += f"Cliente/Descrição: {produto['descricao']}\n"
        
        # Status de produção
        status_producao = "✅ Disponível para produção" if produto['disponivel_producao'] else "❌ Componentes insuficientes"
        mensagem += f"Status: {status_producao}\n\n"
        
        # Componentes necessários
        mensagem += "*Componentes necessários:*\n"
        for comp in produto['componentes']:
            disponibilidade = "✅" if comp['estoque'] >= comp['quantidade'] else "❌"
            mensagem += f"- {comp['nome']} (Código: {comp['codigo']})\n"
            mensagem += f"  Qtd. necessária: {comp['quantidade']} | Em estoque: {comp['estoque']} {disponibilidade}\n"
        
        await query.edit_message_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao processar callback de produto: {e}")
        await query.edit_message_text(f"Erro ao processar solicitação: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processa mensagens de texto e gera respostas usando AI"""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Eita! Você não tá autorizado a usar este bot. Seu ID é {user_id}")
        return
    
    mensagem = update.message.text
    
    try:
        # Enviando indicador de digitação
        await update.message.chat.send_action(action="typing")
        
        await update.message.reply_text("Só um segundo, estou processando sua pergunta... ⏳")
        
        # Verificar modo de operação do bot
        if is_openai_mode():
            # Modo OpenAI - resposta usando AI
            try:
                # Obter dados do contexto do sistema
                system_context_data = get_system_context_data()
                system_message = format_system_context(system_context_data)
                
                # Obter histórico de mensagens (últimas 30)
                chat_id = update.effective_chat.id
                if 'mensagens' not in context.chat_data:
                    context.chat_data['mensagens'] = []
                
                # Adicionar mensagem atual ao histórico
                context.chat_data['mensagens'].append({
                    "role": "user",
                    "content": mensagem
                })
                
                # Limitar para as últimas 50 mensagens
                messages_history = context.chat_data['mensagens'][-30:]
                
                # Preparar mensagens para a API incluindo o contexto do sistema
                api_messages = [{"role": "system", "content": system_message}]
                api_messages.extend(messages_history)
                
                # Chamada para API da OpenAI
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=api_messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                # Extrair resposta
                reply = response.choices[0].message.content
                
                # Adicionar resposta ao histórico
                context.chat_data['mensagens'].append({
                    "role": "assistant",
                    "content": reply
                })
                
                # Enviar resposta
                await update.message.reply_text(reply, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Erro no modo OPENAI: {str(e)}")
                await update.message.reply_text("Putz, deu algum problema ao processar sua pergunta. Tente de novo mais tarde, beleza?")
                
        elif is_local_mode():
            # Modo LOCAL - resposta direta usando comandos
            resposta = "Oi! Estou no modo LOCAL (sem OpenAI). Da uma olhada nos comandos que posso te ajudar:\n\n"
            resposta += "/help - Ver todos os comandos disponíveis\n"
            resposta += "/estoque - Ver componentes com estoque crítico\n"
            resposta += "/estoque_completo - Ver lista completa de componentes\n"
            resposta += "/transacoes - Ver histórico de transações recentes\n"
            resposta += "/fornecedores - Ver avaliação dos fornecedores\n"
            resposta += "/produtos - Listar produtos disponíveis\n"
            resposta += "/componente [código/nome] - Buscar componente\n"
            resposta += "/produto [id/nome] - Buscar produto\n"
            resposta += "/cliente [nome] - Buscar informações de cliente\n"
            resposta += "/producoes - Listar produções recentes\n"
            
            # Tentativa de responder com informações básicas
            if "estoque" in mensagem.lower():
                await estoque_command(update, context)
                return
            elif "transação" in mensagem.lower() or "transacao" in mensagem.lower() or "transações" in mensagem.lower():
                await transacoes_command(update, context)
                return
            elif "fornecedor" in mensagem.lower():
                await fornecedores_command(update, context)
                return
            elif "produto" in mensagem.lower():
                await produtos_command(update, context)
                return
            elif "produção" in mensagem.lower() or "producao" in mensagem.lower():
                await producoes_command(update, context)
                return
            
            await update.message.reply_text(resposta)
            
        elif is_dual_mode():
            # Modo DUAL - tentar usar OpenAI primeiro e fazer fallback para LOCAL
            try:
                # Obter histórico de mensagens (últimas 50)
                chat_id = update.effective_chat.id
                if 'mensagens' not in context.chat_data:
                    context.chat_data['mensagens'] = []
                
                # Adicionar mensagem atual ao histórico
                context.chat_data['mensagens'].append({
                    "role": "user",
                    "content": mensagem
                })
                
                # Limitar para as últimas 50 mensagens
                messages_history = context.chat_data['mensagens'][-50:]
                
                # Tentar obter resposta usando OpenAI
                system_context_data = get_system_context_data()
                system_message = format_system_context(system_context_data)
                
                # Preparar mensagens para a API incluindo o contexto do sistema
                api_messages = [{"role": "system", "content": system_message}]
                api_messages.extend(messages_history)
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=api_messages,
                    temperature=0.7,
                    max_tokens=500
                )
                
                reply = response.choices[0].message.content
                
                # Adicionar resposta ao histórico
                context.chat_data['mensagens'].append({
                    "role": "assistant",
                    "content": reply
                })
                
                # Enviar resposta
                await update.message.reply_text(reply, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Erro no modo DUAL (OpenAI falhou): {str(e)}")
                logger.info("Fazendo fallback para o modo LOCAL")
                
                # Fazer fallback para o modo LOCAL
                resposta = "Opa! Tive um probleminha com a API do OpenAI, então vou operar no modo LOCAL por enquanto. Esses são os comandos que você pode usar:\n\n"
                resposta += "/help - Ver todos os comandos disponíveis\n"
                resposta += "/estoque - Ver componentes com estoque crítico\n"
                resposta += "/estoque_completo - Lista completa de componentes\n"
                resposta += "/transacoes - Histórico de entradas e saídas\n"
                resposta += "/fornecedores - Ver avaliação dos fornecedores\n"
                resposta += "/produtos - Listar produtos disponíveis\n"
                resposta += "/componente [código/nome] - Buscar componente\n"
                resposta += "/produto [id/nome] - Buscar produto\n"
                resposta += "/cliente [nome] - Buscar informações de cliente\n"
                
                await update.message.reply_text(resposta)
    
    except Exception as e:
        logger.error(f"Erro ao processar a mensagem: {str(e)}")
        await update.message.reply_text(f"Erro ao processar a mensagem: {str(e)}")
        
        # Enviar dados do sistema para ajudar na depuração
        try:
            await update.message.reply_text("Coletando dados do sistema para ajudar na depuração...")
            system_context_data = get_system_context_data()
            await update.message.reply_text("Dados do sistema coletados com sucesso.")
        except Exception as e:
            await update.message.reply_text(f"Erro ao coletar dados do sistema: {str(e)}")

async def cliente_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para buscar informações sobre um cliente específico."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Desculpe, você não está autorizado a usar este bot. ID: {user_id}")
        return

    query = context.args
    
    if not query:
        await update.message.reply_text("Por favor, forneça o nome do cliente. Exemplo: /cliente Nome do Cliente")
        return
    
    nome_cliente = ' '.join(query)
    
    try:
        await update.message.reply_text(f"Buscando informações sobre o cliente: {nome_cliente}...")
        
        cliente_info = consultar_cliente(nome_cliente)
        
        if not cliente_info:
            await update.message.reply_text(f"Não foi encontrado nenhum cliente com o nome '{nome_cliente}'.")
            return
        
        # Formatação da mensagem de resposta
        mensagem = f"📊 *INFORMAÇÕES DO CLIENTE: {cliente_info['nome']}*\n\n"
        mensagem += f"Total de produtos: {cliente_info['total_produtos']}\n"
        mensagem += f"Total de produções: {cliente_info['total_producoes']}\n\n"
        
        # Listar produtos
        mensagem += "*PRODUTOS:*\n"
        for i, produto in enumerate(cliente_info['produtos'][:10], 1):
            mensagem += f"{i}. {produto['nome']} - {produto['producoes']} produções\n"
        
        # Listar produções recentes
        if cliente_info['producoes_recentes']:
            mensagem += "\n*PRODUÇÕES RECENTES:*\n"
            for prod in cliente_info['producoes_recentes'][:5]:
                data = prod['data']
                if isinstance(data, str):
                    data = data.split(' ')[0]  # Extrair apenas a data (sem a hora)
                status = "✅" if prod['status'] == "Concluído" else "⏳"
                mensagem += f"- {prod['produto']} - Qtd: {prod['quantidade']} - Data: {data} {status}\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao buscar cliente: {str(e)}")
        await update.message.reply_text("Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde.")

async def producoes_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista as produções recentes."""
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text(f"Desculpe, você não está autorizado a usar este bot. ID: {user_id}")
        return

    try:
        conn = get_db_connection()
        
        # Buscar produções recentes
        producoes = conn.execute('''
            SELECT p.id, p.quantidade, p.data, p.status, 
                   pr.nome as produto, pr.descricao as cliente,
                   u.nome as usuario
            FROM producoes p
            JOIN produtos pr ON p.produto_id = pr.id
            LEFT JOIN usuarios u ON p.usuario_id = u.id
            ORDER BY p.data DESC
            LIMIT 20
        ''').fetchall()
        
        conn.close()
        
        if not producoes:
            await update.message.reply_text("Não há produções registradas no sistema.")
            return
        
        # Formatação da mensagem de resposta
        mensagem = "📊 *PRODUÇÕES RECENTES*\n\n"
        
        for i, prod in enumerate(producoes, 1):
            data = prod['data']
            if isinstance(data, str):
                data = data.split(' ')[0]  # Extrair apenas a data (sem a hora)
            
            status = "✅" if prod['status'] == "Concluído" else "⏳"
            cliente = f" - Cliente: {prod['cliente']}" if prod['cliente'] else ""
            
            mensagem += f"{i}. *{prod['produto']}*{cliente}\n"
            mensagem += f"   Qtd: {prod['quantidade']} - Data: {data} {status}\n"
            if prod['usuario']:
                mensagem += f"   Responsável: {prod['usuario']}\n"
            mensagem += "\n"
        
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"Erro ao listar produções: {str(e)}")
        await update.message.reply_text("Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com erros do Telegram"""
    logger.error(f"Erro no update {update} causado por {context.error}")

def main():
    """Inicia o bot"""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN não encontrado nas variáveis de ambiente.")
        return
    
    # Criar o aplicativo
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("estoque", estoque_command))
    application.add_handler(CommandHandler("estoque_completo", estoque_completo_command))
    application.add_handler(CommandHandler("transacoes", transacoes_command))
    application.add_handler(CommandHandler("fornecedores", fornecedores_command))
    application.add_handler(CommandHandler("produtos", produtos_command))
    application.add_handler(CommandHandler("componente", componente_command))
    application.add_handler(CommandHandler("produto", produto_command))
    application.add_handler(CommandHandler("analise_estoque", analise_estoque_command))
    application.add_handler(CommandHandler("analise_fornecedores", analise_fornecedores_command))
    application.add_handler(CommandHandler("cliente", cliente_command))
    application.add_handler(CommandHandler("producoes", producoes_command))
    application.add_handler(CallbackQueryHandler(produto_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Adicionar handler de erro
    application.add_error_handler(error_handler)
    
    logger.info(f"Bot iniciado no modo: {os.getenv('BOT_MODE', 'LOCAL')}")
    
    # Iniciar o bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 