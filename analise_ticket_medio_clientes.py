import pandas as pd
import matplotlib.pyplot as plt


def carregar_dados():
    vendas = pd.read_csv('vendas_2023_2024.csv')
    produtos = pd.read_csv('produtos_limpos.csv')
    clientes = pd.read_json('clientes_crm.json')
    return vendas, produtos, clientes


def preparar_dimensao_produtos(produtos):
    produtos_dim = produtos.copy()

    produtos_dim = produtos_dim.rename(columns={'code': 'id_produto', 'name': 'nome_produto'})
    produtos_dim['categoria_limpa'] = produtos_dim['actual_category'].fillna('indefinido')

    produtos_dim = produtos_dim.sort_values('id_produto').drop_duplicates(subset=['id_produto'], keep='first')

    return produtos_dim[['id_produto', 'nome_produto', 'categoria_limpa']]


def calcular_metricas_clientes(vendas, produtos_dim):
    base = vendas.rename(columns={'id_client': 'id_cliente', 'id_product': 'id_produto'})
    base = base.merge(produtos_dim, on='id_produto', how='left')

    base['categoria_limpa'] = base['categoria_limpa'].fillna('indefinido')

    metricas = base.groupby('id_cliente', as_index=False).agg(
        faturamento_total=('total', 'sum'),
        frequencia=('id', 'nunique'),
        diversidade_categorias=('categoria_limpa', 'nunique')
    )

    metricas['ticket_medio'] = metricas['faturamento_total'] / metricas['frequencia']

    metricas = metricas[['id_cliente', 'faturamento_total', 'frequencia', 'ticket_medio', 'diversidade_categorias']]

    return metricas


def gerar_ranking_elite(metricas):
    elite = metricas[metricas['diversidade_categorias'] >= 3].copy()
    elite = elite.sort_values(['ticket_medio', 'id_cliente'], ascending=[False, True]).reset_index(drop=True)
    return elite


def calcular_qtd_por_categoria_no_top10(vendas, produtos_dim, top10_clientes):
    base = vendas.rename(columns={'id_client': 'id_cliente', 'id_product': 'id_produto'})
    base = base.merge(produtos_dim, on='id_produto', how='left')
    base['categoria_limpa'] = base['categoria_limpa'].fillna('indefinido')

    base_top10 = base[base['id_cliente'].isin(top10_clientes['id_cliente'])].copy()

    categorias = base_top10.groupby('categoria_limpa', as_index=False).agg(
        qtd_total=('qtd', 'sum')
    )
    categorias = categorias.sort_values('qtd_total', ascending=False).reset_index(drop=True)

    return categorias


def gerar_grafico_top10_ticket(top10_clientes, caminho_saida='grafico_top10_ticket_medio_elite.png'):
    dados = top10_clientes.sort_values('ticket_medio', ascending=True).copy()
    if 'nome_cliente' in dados.columns:
        dados['rotulo_cliente'] = dados['nome_cliente'].fillna('Cliente ' + dados['id_cliente'].astype(str))
    else:
        dados['rotulo_cliente'] = 'Cliente ' + dados['id_cliente'].astype(str)

    plt.figure(figsize=(11, 6))
    barras = plt.barh(dados['rotulo_cliente'], dados['ticket_medio'])
    plt.title('Top 10 clientes por Ticket Médio (Elite: 3+ categorias)')
    plt.xlabel('Ticket Médio (R$)')
    plt.ylabel('Cliente')

    max_val = dados['ticket_medio'].max()
    plt.xlim(0, max_val * 1.15)

    for barra, valor in zip(barras, dados['ticket_medio']):
        plt.text(
            barra.get_width() + (max_val * 0.01),
            barra.get_y() + barra.get_height() / 2,
            f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
            va='center',
            fontsize=9
        )

    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=150)
    plt.close()


def gerar_grafico_qtd_categoria(categorias, caminho_saida='grafico_qtd_categoria_top10_clientes.png'):
    dados = categorias.sort_values('qtd_total', ascending=True).copy()

    plt.figure(figsize=(10, 5))
    barras = plt.barh(dados['categoria_limpa'], dados['qtd_total'])
    plt.title('Quantidade total de itens por categoria (Top 10 clientes por Ticket Médio)')
    plt.xlabel('Quantidade de itens (sum(qtd))')
    plt.ylabel('Categoria')

    max_val = dados['qtd_total'].max()
    plt.xlim(0, max_val * 1.15)

    for barra, valor in zip(barras, dados['qtd_total']):
        plt.text(
            barra.get_width() + (max_val * 0.01),
            barra.get_y() + barra.get_height() / 2,
            f'{int(valor)}',
            va='center',
            fontsize=10
        )

    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=150)
    plt.close()


def main():
    vendas, produtos, clientes = carregar_dados()
    produtos_dim = preparar_dimensao_produtos(produtos)
    clientes_dim = clientes.rename(columns={'code': 'id_cliente', 'full_name': 'nome_cliente'})
    clientes_dim = clientes_dim[['id_cliente', 'nome_cliente']].drop_duplicates(subset=['id_cliente'])

    metricas = calcular_metricas_clientes(vendas, produtos_dim)
    metricas = metricas.merge(clientes_dim, on='id_cliente', how='left')
    ranking_elite = gerar_ranking_elite(metricas)
    top10_clientes = ranking_elite.head(10).copy()
    categorias_top10 = calcular_qtd_por_categoria_no_top10(vendas, produtos_dim, top10_clientes)

    categoria_lider = categorias_top10.iloc[0]

    metricas.to_csv('metricas_clientes.csv', index=False, encoding='utf-8')
    ranking_elite.to_csv('ranking_clientes_elite.csv', index=False, encoding='utf-8')
    top10_clientes.to_csv('top10_clientes_ticket_medio.csv', index=False, encoding='utf-8')
    categorias_top10.to_csv('categorias_top10_clientes_qtd.csv', index=False, encoding='utf-8')

    gerar_grafico_top10_ticket(top10_clientes)
    gerar_grafico_qtd_categoria(categorias_top10)

    print('Arquivo gerado: metricas_clientes.csv')
    print('Arquivo gerado: ranking_clientes_elite.csv')
    print('Arquivo gerado: top10_clientes_ticket_medio.csv')
    print('Arquivo gerado: categorias_top10_clientes_qtd.csv')
    print('Gráfico gerado: grafico_top10_ticket_medio_elite.png')
    print('Gráfico gerado: grafico_qtd_categoria_top10_clientes.png')
    print('\nCategoria com maior quantidade total de itens no Top 10:')
    print(f"- {categoria_lider['categoria_limpa']} (sum(qtd) = {int(categoria_lider['qtd_total'])})")


if __name__ == '__main__':
    main()
