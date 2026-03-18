import numpy as np
import pandas as pd

ARQ_VENDAS = 'vendas_2023_2024.csv'
ARQ_PRODUTOS = 'produtos_limpos.csv'
PRODUTO_REFERENCIA = 'GPS Garmin Vortex Maré Drift'
ARQ_MATRIZ = 'matriz_usuario_item_binaria.csv'
ARQ_RANKING = 'ranking_similaridade_gps_vortex.csv'


def carregar_bases():
    vendas = pd.read_csv(ARQ_VENDAS)
    produtos = pd.read_csv(ARQ_PRODUTOS)
    return vendas, produtos


def obter_produto_referencia(produtos, nome_produto):
    filtro = produtos['name'].str.lower() == nome_produto.lower()
    alvo = produtos.loc[filtro, ['code', 'name']]

    if alvo.empty:
        raise ValueError(f'Produto não encontrado: {nome_produto}')

    id_produto = int(alvo.iloc[0]['code'])
    nome = str(alvo.iloc[0]['name'])
    return id_produto, nome


def construir_matriz_usuario_item(vendas):
    interacoes = vendas[['id_client', 'id_product']].drop_duplicates().copy()
    interacoes['valor'] = 1

    matriz = interacoes.pivot_table(
        index='id_client',
        columns='id_product',
        values='valor',
        aggfunc='max',
        fill_value=0
    )

    matriz = matriz.sort_index().sort_index(axis=1)
    return matriz


def calcular_similaridade_cosseno_produto(matriz_usuario_item):
    # Produto x Cliente
    produto_cliente = matriz_usuario_item.T.astype(float)
    X = produto_cliente.to_numpy()

    norma = np.linalg.norm(X, axis=1, keepdims=True)
    norma[norma == 0] = 1.0
    X_norm = X / norma

    similaridade = X_norm @ X_norm.T

    return pd.DataFrame(
        similaridade,
        index=produto_cliente.index,
        columns=produto_cliente.index
    )


def gerar_ranking_produtos_similares(similaridade_produtos, produtos, id_produto_ref, top_n=5):
    if id_produto_ref not in similaridade_produtos.index:
        raise ValueError(f'O produto de referência {id_produto_ref} não está na matriz de similaridade.')

    ranking = (
        similaridade_produtos.loc[id_produto_ref]
        .drop(labels=[id_produto_ref], errors='ignore')
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    ranking.columns = ['id_produto', 'similaridade_cosseno']

    nomes = produtos.rename(columns={'code': 'id_produto', 'name': 'nome_produto'})
    ranking = ranking.merge(nomes[['id_produto', 'nome_produto']], on='id_produto', how='left')

    return ranking[['id_produto', 'nome_produto', 'similaridade_cosseno']]


def main():
    vendas, produtos = carregar_bases()
    id_ref, nome_ref = obter_produto_referencia(produtos, PRODUTO_REFERENCIA)

    matriz_usuario_item = construir_matriz_usuario_item(vendas)
    similaridade_produtos = calcular_similaridade_cosseno_produto(matriz_usuario_item)
    ranking_top5 = gerar_ranking_produtos_similares(similaridade_produtos, produtos, id_ref, top_n=5)

    matriz_usuario_item.to_csv(ARQ_MATRIZ, encoding='utf-8')
    ranking_top5.to_csv(ARQ_RANKING, index=False, encoding='utf-8')

    print('Matriz usuário-item criada com sucesso.')
    print(f'Arquivo: {ARQ_MATRIZ}')
    print('Similaridade de cosseno produto x produto calculada.')
    print(f'Produto de referência: {nome_ref} (id={id_ref})')
    print(f'Ranking Top 5 salvo em: {ARQ_RANKING}')
    print('\nTop 5 produtos similares:')
    print(ranking_top5.to_string(index=False))


if __name__ == '__main__':
    main()
