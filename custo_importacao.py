import json
import pandas as pd

# Carregamento do arquivo JSON
with open('custos_importacao.json', 'r', encoding='utf-8') as f:
    dados_brutos = json.load(f)

# Processamento e Achatamento dos dados aninhados para criar um novo registro para cada combinação de produto e histórico de preços
registros_processados = []

for produto in dados_brutos:
    # Extração os dados fixos do produto
    p_id = produto.get('product_id')
    p_name = produto.get('product_name')
    p_category = produto.get('category')
    
    # Percorremos a lista aninhada de preços históricos para criar um registro para cada entrada.
    for historico in produto.get('historic_data', []):
        registros_processados.append({
            'product_id': p_id,
            'product_name': p_name,
            'category': p_category,
            'start_date': historico.get('start_date'),
            'usd_price': historico.get('usd_price')
        })

#O arquivo será gerado seguindo o dicionário de dados proposto, 
# garantindo que colunas numéricas como usd_price estejam livres de símbolos de moeda e 
# prontas para o casting de float no banco de dados.
df_custos_final = pd.DataFrame(registros_processados)
df_custos_final.to_csv('custos_importacao.csv', index=False, encoding='utf-8')

print("Arquivo 'custos_importacao.csv'com os dados organizados foi gerado com sucesso!")