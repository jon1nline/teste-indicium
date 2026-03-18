import json
from pathlib import Path

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


st.set_page_config(page_title='Dashboard - Análises de Vendas', layout='wide')

BASE_DIR = Path(__file__).resolve().parent


def carregar_csv(nome_arquivo):
    caminho = BASE_DIR / nome_arquivo
    if not caminho.exists():
        return None
    return pd.read_csv(caminho)


def carregar_json(nome_arquivo):
    caminho = BASE_DIR / nome_arquivo
    if not caminho.exists():
        return None
    return pd.read_json(caminho)


def moeda_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def secao_resumo():
    st.title('Dashboard Executivo - Vendas, Custos e Recomendação')
    st.caption('Consolidação das análises realizadas no projeto')

    metricas_clientes = carregar_csv('metricas_clientes.csv')
    ranking_similaridade = carregar_csv('ranking_similaridade_gps_vortex.csv')
    previsao = carregar_csv('previsao_jan_2024_motor_popa.csv')

    c1, c2, c3 = st.columns(3)

    if metricas_clientes is not None:
        c1.metric('Clientes analisados', int(metricas_clientes['id_cliente'].nunique()))
    else:
        c1.metric('Clientes analisados', 'N/A')

    if ranking_similaridade is not None and not ranking_similaridade.empty:
        top1 = ranking_similaridade.iloc[0]
        c2.metric('Produto recomendado p/ GPS Vortex', f"ID {int(top1['id_produto'])}")
    else:
        c2.metric('Produto recomendado p/ GPS Vortex', 'N/A')

    if previsao is not None and not previsao.empty:
        mae = (previsao['qtd_real'] - previsao['qtd_prevista_mm7']).abs().mean()
        c3.metric('MAE baseline (jan/2024)', f"{mae:.4f}")
    else:
        c3.metric('MAE baseline (jan/2024)', 'N/A')


def secao_prejuizo_produtos():
    st.subheader('1) Prejuízo por Produto (Top 10)')

    caminho_img = BASE_DIR / 'grafico_top10_prejuizo_por_produto.png'
    if caminho_img.exists():
        st.image(str(caminho_img), use_container_width=True)
    else:
        st.warning('Arquivo grafico_top10_prejuizo_por_produto.png não encontrado.')


def secao_clientes_elite():
    st.subheader('2) Clientes Elite e Categorias')

    top10_clientes = carregar_csv('top10_clientes_ticket_medio.csv')
    categorias_top10 = carregar_csv('categorias_top10_clientes_qtd.csv')
    clientes_crm = carregar_json('clientes_crm.json')

    if top10_clientes is not None and 'nome_cliente' not in top10_clientes.columns and clientes_crm is not None:
        clientes_dim = clientes_crm.rename(columns={'code': 'id_cliente', 'full_name': 'nome_cliente'})
        clientes_dim = clientes_dim[['id_cliente', 'nome_cliente']].drop_duplicates(subset=['id_cliente'])
        top10_clientes = top10_clientes.merge(clientes_dim, on='id_cliente', how='left')

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('**Top 10 clientes por Ticket Médio (3+ categorias)**')
        if top10_clientes is not None:
            colunas_exibicao = ['id_cliente', 'nome_cliente', 'faturamento_total', 'frequencia', 'ticket_medio', 'diversidade_categorias']
            colunas_exibicao = [c for c in colunas_exibicao if c in top10_clientes.columns]
            top10_exibicao = top10_clientes[colunas_exibicao].copy()
            st.dataframe(top10_exibicao, use_container_width=True)

            fig, ax = plt.subplots(figsize=(8, 5))
            dados = top10_clientes.sort_values('ticket_medio', ascending=True)
            rotulo = dados['nome_cliente'].fillna('Cliente ' + dados['id_cliente'].astype(str)) if 'nome_cliente' in dados.columns else dados['id_cliente'].astype(str)
            ax.barh(rotulo, dados['ticket_medio'])
            ax.set_xlabel('Ticket Médio (R$)')
            ax.set_ylabel('Cliente')
            ax.set_title('Top 10 clientes por Ticket Médio')
            st.pyplot(fig)
        else:
            st.warning('Arquivo top10_clientes_ticket_medio.csv não encontrado.')

    with col2:
        st.markdown('**Categoria com maior volume de itens no Top 10**')
        if categorias_top10 is not None and not categorias_top10.empty:
            st.dataframe(categorias_top10, use_container_width=True)

            lider = categorias_top10.sort_values('qtd_total', ascending=False).iloc[0]
            st.success(
                f"Categoria líder: **{lider['categoria_limpa']}** | "
                f"sum(qtd) = **{int(lider['qtd_total'])}**"
            )

            fig2, ax2 = plt.subplots(figsize=(8, 5))
            dados2 = categorias_top10.sort_values('qtd_total', ascending=True)
            ax2.barh(dados2['categoria_limpa'], dados2['qtd_total'])
            ax2.set_xlabel('Quantidade total de itens (sum(qtd))')
            ax2.set_ylabel('Categoria')
            ax2.set_title('Itens por categoria (Top 10 clientes)')
            st.pyplot(fig2)
        else:
            st.warning('Arquivo categorias_top10_clientes_qtd.csv não encontrado.')


def secao_dia_semana():
    st.subheader('3) Média de Vendas por Dia da Semana (com dias zerados)')

    calendario = carregar_csv('calendario_com_vendas.csv')
    if calendario is None or calendario.empty:
        st.warning('Arquivo calendario_com_vendas.csv não encontrado.')
        return

    ordem = {
        'Segunda-feira': 1,
        'Terça-feira': 2,
        'Quarta-feira': 3,
        'Quinta-feira': 4,
        'Sexta-feira': 5,
        'Sábado': 6,
        'Domingo': 7,
    }

    medias = (
        calendario.groupby('dia_semana_pt', as_index=False)['valor_venda_dia']
        .mean()
        .rename(columns={'valor_venda_dia': 'media_venda'})
    )
    medias['ordem'] = medias['dia_semana_pt'].map(ordem)
    medias = medias.sort_values('ordem')

    pior = medias.sort_values('media_venda').iloc[0]
    st.info(
        f"Pior média histórica: **{pior['dia_semana_pt']}** - "
        f"**{moeda_brl(float(pior['media_venda']))}**"
    )

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(medias['dia_semana_pt'], medias['media_venda'])
    ax.set_ylabel('Média de venda diária (R$)')
    ax.set_xlabel('Dia da semana')
    ax.set_title('Média por dia da semana (incluindo dias sem venda)')
    ax.tick_params(axis='x', rotation=20)
    st.pyplot(fig)


def secao_previsao_baseline():
    st.subheader('4) Previsão Baseline - Motor de Popa Yamaha Evo Dash 155HP')

    previsao = carregar_csv('previsao_jan_2024_motor_popa.csv')
    if previsao is None or previsao.empty:
        st.warning('Arquivo previsao_jan_2024_motor_popa.csv não encontrado.')
        return

    previsao['data'] = pd.to_datetime(previsao['data'])
    previsao = previsao.sort_values('data')

    mae = (previsao['qtd_real'] - previsao['qtd_prevista_mm7']).abs().mean()
    media_real = previsao['qtd_real'].mean()

    c1, c2 = st.columns(2)
    c1.metric('MAE (jan/2024)', f"{mae:.4f}")
    c2.metric('Média real diária', f"{media_real:.4f}")

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(previsao['data'], previsao['qtd_real'], label='Real', marker='o', linewidth=1)
    ax.plot(previsao['data'], previsao['qtd_prevista_mm7'], label='Prevista (MM7)', marker='x', linewidth=1)
    ax.set_title('Previsão diária - Janeiro/2024')
    ax.set_xlabel('Data')
    ax.set_ylabel('Quantidade')
    ax.legend()
    st.pyplot(fig)


def secao_recomendacao():
    st.subheader('5) Recomendação por Similaridade de Compra')

    ranking = carregar_csv('ranking_similaridade_gps_vortex.csv')
    if ranking is None or ranking.empty:
        st.warning('Arquivo ranking_similaridade_gps_vortex.csv não encontrado.')
        return

    st.markdown('Produto de referência: **GPS Garmin Vortex Maré Drift**')
    st.dataframe(ranking, use_container_width=True)

    top1 = ranking.iloc[0]
    st.success(
        f"Melhor recomendação: **ID {int(top1['id_produto'])} - {top1['nome_produto']}** "
        f"(similaridade: {top1['similaridade_cosseno']:.6f})"
    )


def secao_notas():
    st.subheader('Notas da metodologia')
    st.markdown(
        '- Valores de prejuízo usam custo em R$ conforme regra definida no projeto.\n'
        '- Clientes Elite: diversidade de categorias >= 3.\n'
        '- Baseline de previsão: média móvel de 7 dias sem data leakage.\n'
        '- Recomendação: matriz binária usuário-item + similaridade de cosseno produto×produto.'
    )


def main():
    secao_resumo()
    st.divider()

    secao_prejuizo_produtos()
    st.divider()

    secao_clientes_elite()
    st.divider()

    secao_dia_semana()
    st.divider()

    secao_previsao_baseline()
    st.divider()

    secao_recomendacao()
    st.divider()

    secao_notas()


if __name__ == '__main__':
    main()
