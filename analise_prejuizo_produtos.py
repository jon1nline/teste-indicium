import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def carregar_e_preparar_dados():
    vendas = pd.read_csv('vendas_2023_2024.csv')
    custos = pd.read_csv('custos_importacao.csv')
    cambio = pd.read_csv('cotacao_dolar.csv')

    vendas['data_venda'] = pd.to_datetime(vendas['sale_date'], format='%Y-%m-%d', errors='coerce')
    mascara_datas_invalidas = vendas['data_venda'].isna()
    vendas.loc[mascara_datas_invalidas, 'data_venda'] = pd.to_datetime(
        vendas.loc[mascara_datas_invalidas, 'sale_date'],
        format='%d-%m-%Y',
        errors='coerce'
    )
    vendas = vendas.dropna(subset=['data_venda']).copy()
    vendas = vendas.rename(columns={'id_product': 'id_produto', 'total': 'receita_venda'})

    custos['inicio_vigencia'] = pd.to_datetime(custos['start_date'], format='%d/%m/%Y', errors='coerce')
    custos = custos.dropna(subset=['inicio_vigencia']).copy()
    custos = custos.rename(columns={'product_id': 'id_produto', 'usd_price': 'custo_usd'})

    cambio = cambio.rename(columns={cambio.columns[0]: 'taxa_cambio_data', cambio.columns[1]: 'data_hora_cotacao'})
    cambio['data_cambio'] = pd.to_datetime(
        cambio['data_hora_cotacao'].astype(str).str.slice(0, 10),
        format='%Y-%m-%d',
        errors='coerce'
    )
    cambio = cambio.dropna(subset=['data_cambio']).copy()

    return vendas, custos, cambio


def aplicar_cambio_vigente(vendas, cambio):
    cambio = cambio.sort_values('data_cambio').reset_index(drop=True)
    datas_cambio = cambio['data_cambio'].values.astype('datetime64[ns]')
    valores_cambio = cambio['taxa_cambio_data'].astype(float).values

    datas_venda = vendas['data_venda'].values.astype('datetime64[ns]')
    posicoes = np.searchsorted(datas_cambio, datas_venda, side='right') - 1

    vendas['taxa_cambio_data'] = np.where(
        posicoes >= 0,
        valores_cambio[np.clip(posicoes, 0, len(valores_cambio) - 1)],
        np.nan
    )

    return vendas


def aplicar_custo_vigente(vendas, custos):
    vendas['custo_usd'] = np.nan

    for id_produto, indices in vendas.groupby('id_produto').groups.items():
        linhas = np.array(list(indices))
        historico = custos[custos['id_produto'] == id_produto].sort_values('inicio_vigencia')

        if historico.empty:
            continue

        datas_custo = historico['inicio_vigencia'].values.astype('datetime64[ns]')
        valores_custo = historico['custo_usd'].astype(float).values
        datas_venda = vendas.loc[linhas, 'data_venda'].values.astype('datetime64[ns]')

        posicoes = np.searchsorted(datas_custo, datas_venda, side='right') - 1
        validas = posicoes >= 0

        custo_encontrado = np.full(len(linhas), np.nan)
        if validas.any():
            custo_encontrado[validas] = valores_custo[posicoes[validas]]

        vendas.loc[linhas, 'custo_usd'] = custo_encontrado

    return vendas


def calcular_metricas(vendas):
    base = vendas.dropna(subset=['taxa_cambio_data', 'custo_usd']).copy()

    base['custo_total_brl'] = base['custo_usd'] * base['taxa_cambio_data']
    base['prejuizo_venda'] = np.where(
        base['receita_venda'] < base['custo_total_brl'],
        base['custo_total_brl'] - base['receita_venda'],
        0.0
    )

    agregado = base.groupby('id_produto', as_index=False).agg(
        receita_total=('receita_venda', 'sum'),
        prejuizo_total=('prejuizo_venda', 'sum')
    )

    agregado['percentual_perda'] = np.where(
        agregado['receita_total'] > 0,
        (agregado['prejuizo_total'] / agregado['receita_total']) * 100,
        0.0
    )

    return agregado


def formatar_moeda_brl(valor):
    texto = f"{valor:,.2f}"
    texto = texto.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"R$ {texto}"


def gerar_grafico_prejuizo(agregado, caminho_saida='grafico_top10_prejuizo_por_produto.png'):
    dados_prejuizo = agregado[agregado['prejuizo_total'] > 0].copy()
    dados_prejuizo = dados_prejuizo.sort_values('prejuizo_total', ascending=False).head(10)
    dados_prejuizo['rotulo_produto'] = (
        dados_prejuizo['id_produto'].astype(str)
        + ' - '
        + dados_prejuizo['product_name'].fillna('Produto sem nome')
    )
    dados_prejuizo = dados_prejuizo.sort_values('prejuizo_total', ascending=True)

    plt.figure(figsize=(14, 8))
    barras = plt.barh(dados_prejuizo['rotulo_produto'], dados_prejuizo['prejuizo_total'])
    plt.title('Top 10 produtos por prejuízo total')
    plt.xlabel('Prejuízo total (R$)')
    plt.ylabel('Produto (ID - nome)')

    limite_direito = dados_prejuizo['prejuizo_total'].max() * 1.22
    plt.xlim(0, limite_direito)

    for barra, valor in zip(barras, dados_prejuizo['prejuizo_total']):
        plt.text(
            barra.get_width() + (limite_direito * 0.01),
            barra.get_y() + barra.get_height() / 2,
            formatar_moeda_brl(valor),
            va='center',
            fontsize=9
        )

    plt.tight_layout()
    plt.savefig(caminho_saida, dpi=150)
    plt.close()


def responder_objetivo(agregado):
    com_prejuizo = agregado[agregado['prejuizo_total'] > 0].copy()

    maior_prejuizo_abs = com_prejuizo.sort_values(
        ['prejuizo_total', 'id_produto'],
        ascending=[False, True]
    ).iloc[0]

    maior_percentual = agregado.sort_values(
        ['percentual_perda', 'id_produto'],
        ascending=[False, True]
    ).iloc[0]

    mesmo_produto = int(maior_prejuizo_abs['id_produto']) == int(maior_percentual['id_produto'])

    return {
        'id_produto_maior_prejuizo_abs': int(maior_prejuizo_abs['id_produto']),
        'prejuizo_total': float(maior_prejuizo_abs['prejuizo_total']),
        'id_produto_maior_percentual': int(maior_percentual['id_produto']),
        'percentual_perda': float(maior_percentual['percentual_perda']),
        'mesmo_produto': 'Sim' if mesmo_produto else 'Não'
    }


def main():
    vendas, custos, cambio = carregar_e_preparar_dados()
    vendas = aplicar_cambio_vigente(vendas, cambio)
    vendas = aplicar_custo_vigente(vendas, custos)

    agregado = calcular_metricas(vendas)
    nomes_produto = custos[['id_produto', 'product_name']].drop_duplicates(subset=['id_produto'])
    agregado = agregado.merge(nomes_produto, on='id_produto', how='left')
    gerar_grafico_prejuizo(agregado)

    respostas = responder_objetivo(agregado)

    print('Parte 2 — gráfico salvo em: grafico_top10_prejuizo_por_produto.png')
    print('Parte 3 — respostas objetivas:')
    print(f"1) Produto com maior prejuízo absoluto: {respostas['id_produto_maior_prejuizo_abs']} (R$ {respostas['prejuizo_total']:.2f})")
    print(f"2) É o mesmo produto com maior percentual de perda? {respostas['mesmo_produto']}")
    print(f"   - Maior percentual de perda: produto {respostas['id_produto_maior_percentual']} ({respostas['percentual_perda']:.4f}%)")


if __name__ == '__main__':
    main()
