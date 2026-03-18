import pandas as pd
import numpy as np

PRODUTO_NOME = 'Motor de Popa Yamaha Evo Dash 155HP'
ARQUIVO_VENDAS = 'vendas_2023_2024.csv'
ARQUIVO_PRODUTOS = 'produtos_limpos.csv'
ARQUIVO_SAIDA = 'previsao_jan_2024_motor_popa.csv'


def parse_data_mista(serie):
    d1 = pd.to_datetime(serie, format='%Y-%m-%d', errors='coerce')
    d2 = pd.to_datetime(serie, format='%d-%m-%Y', errors='coerce')
    return d1.fillna(d2)


def obter_id_produto(produtos, nome_produto):
    alvo = produtos[produtos['name'].str.lower() == nome_produto.lower()]
    if alvo.empty:
        raise ValueError(f'Produto não encontrado: {nome_produto}')
    return int(alvo.iloc[0]['code'])


def preparar_serie_diaria(vendas, id_produto):
    vendas = vendas.copy()
    vendas['data_venda'] = parse_data_mista(vendas['sale_date'])
    vendas = vendas.dropna(subset=['data_venda'])

    vendas_produto = vendas[vendas['id_product'] == id_produto].copy()

    diario = (
        vendas_produto
        .groupby(vendas_produto['data_venda'].dt.date, as_index=False)['qtd']
        .sum()
        .rename(columns={'qtd': 'qtd_real'})
    )
    diario['data'] = pd.to_datetime(diario['data_venda'])
    diario = diario.drop(columns=['data_venda'])

    data_inicio = diario['data'].min()
    data_fim_teste = pd.Timestamp('2024-01-31')

    calendario = pd.DataFrame({'data': pd.date_range(data_inicio, data_fim_teste, freq='D')})
    serie = calendario.merge(diario, on='data', how='left')
    serie['qtd_real'] = serie['qtd_real'].fillna(0.0)

    return serie


def prever_media_movel_7_dias(serie):
    treino_fim = pd.Timestamp('2023-12-31')
    teste_inicio = pd.Timestamp('2024-01-01')
    teste_fim = pd.Timestamp('2024-01-31')

    treino = serie[serie['data'] <= treino_fim].copy()
    teste = serie[(serie['data'] >= teste_inicio) & (serie['data'] <= teste_fim)].copy()

    if treino.empty:
        raise ValueError('Período de treino ficou vazio. Verifique os dados.')

    previsoes = []

    # Walk-forward sem data leakage:
    # para cada dia de teste, usa apenas os 7 dias anteriores ao dia previsto.
    for data_alvo in teste['data']:
        historico = serie[serie['data'] < data_alvo].sort_values('data').tail(7)
        if historico.empty:
            pred = 0.0
        else:
            pred = float(historico['qtd_real'].mean())

        real = float(serie.loc[serie['data'] == data_alvo, 'qtd_real'].iloc[0])
        previsoes.append({
            'data': data_alvo,
            'qtd_real': real,
            'qtd_prevista_mm7': pred,
            'erro_absoluto': abs(real - pred)
        })

    resultado = pd.DataFrame(previsoes)
    mae = float(resultado['erro_absoluto'].mean())

    return resultado, mae


def main():
    vendas = pd.read_csv(ARQUIVO_VENDAS)
    produtos = pd.read_csv(ARQUIVO_PRODUTOS)

    id_produto = obter_id_produto(produtos, PRODUTO_NOME)
    serie = preparar_serie_diaria(vendas, id_produto)
    previsao_jan, mae = prever_media_movel_7_dias(serie)

    previsao_jan.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')

    media_real_teste = float(previsao_jan['qtd_real'].mean())
    mae_relativo_media = float(mae / media_real_teste) if media_real_teste > 0 else np.nan

    print(f'Produto alvo: {PRODUTO_NOME}')
    print(f'id_produto: {id_produto}')
    print('Treino: até 2023-12-31')
    print('Teste: 2024-01-01 a 2024-01-31')
    print(f'MAE (qtd): {mae:.4f}')
    print(f'Média real diária no teste (qtd): {media_real_teste:.4f}')
    print(f'MAE / média real: {mae_relativo_media:.4f}')
    print(f'Arquivo gerado: {ARQUIVO_SAIDA}')


if __name__ == '__main__':
    main()
