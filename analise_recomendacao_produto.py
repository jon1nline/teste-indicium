import numpy as np
import pandas as pd

ARQUIVO_VENDAS = 'vendas_2023_2024.csv'
ARQUIVO_PRODUTOS = 'produtos_limpos.csv'
ARQUIVO_MATRIZ = 'matriz_interacao_usuario_produto.csv'
ARQUIVO_TOP5 = 'top5_produtos_similares_gps_vortex.csv'
PRODUTO_REFERENCIA = 'GPS Garmin Vortex Maré Drift'


def carregar_dados():
    vendas = pd.read_csv(ARQUIVO_VENDAS)
    produtos = pd.read_csv(ARQUIVO_PRODUTOS)
    return vendas, produtos


def obter_id_produto_referencia(produtos, nome_produto):
    alvo = produtos[produtos['name'].str.lower() == nome_produto.lower()]
    if alvo.empty:
        raise ValueError(f'Produto de referência não encontrado: {nome_produto}')
    return int(alvo.iloc[0]['code'])


def construir_matriz_binaria(vendas):
    base = vendas[['id_client', 'id_product']].drop_duplicates().copy()
    base['interacao'] = 1

    matriz = base.pivot_table(
        index='id_client',
        columns='id_product',
        values='interacao',
        aggfunc='max',
        fill_value=0
    )

    return matriz


def calcular_similaridade_cosseno_produto(matriz):
    # Vetores de produto por cliente: transpose => linhas são produtos
    produto_cliente = matriz.T.astype(float)

    X = produto_cliente.values
    normas = np.linalg.norm(X, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    X_norm = X / normas

    sim = X_norm @ X_norm.T

    similaridade = pd.DataFrame(
        sim,
        index=produto_cliente.index,
        columns=produto_cliente.index
    )

    return similaridade


def gerar_top5_similares(similaridade, produtos, id_ref):
    if id_ref not in similaridade.index:
        raise ValueError(f'Produto de referência {id_ref} não existe na matriz de similaridade.')

    ranking = (
        similaridade.loc[id_ref]
        .drop(labels=[id_ref], errors='ignore')
        .sort_values(ascending=False)
        .head(5)
        .reset_index()
    )
    ranking.columns = ['id_produto', 'similaridade_cosseno']

    ranking = ranking.merge(
        produtos.rename(columns={'code': 'id_produto', 'name': 'nome_produto'})[['id_produto', 'nome_produto']],
        on='id_produto',
        how='left'
    )

    ranking = ranking[['id_produto', 'nome_produto', 'similaridade_cosseno']]

    return ranking


def main():
    vendas, produtos = carregar_dados()
    id_ref = obter_id_produto_referencia(produtos, PRODUTO_REFERENCIA)

    matriz = construir_matriz_binaria(vendas)
    similaridade = calcular_similaridade_cosseno_produto(matriz)
    top5 = gerar_top5_similares(similaridade, produtos, id_ref)

    matriz.to_csv(ARQUIVO_MATRIZ, encoding='utf-8')
    top5.to_csv(ARQUIVO_TOP5, index=False, encoding='utf-8')

    print(f'Produto de referência: {PRODUTO_REFERENCIA}')
    print(f'id_produto referência: {id_ref}')
    print(f'Arquivo gerado: {ARQUIVO_MATRIZ}')
    print(f'Arquivo gerado: {ARQUIVO_TOP5}')
    print('\nTop 5 produtos similares:')
    print(top5.to_string(index=False))


if __name__ == '__main__':
    main()
