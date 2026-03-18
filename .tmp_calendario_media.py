import pandas as pd

v = pd.read_csv('vendas_2023_2024.csv')

# Parse de datas em dois formatos
d1 = pd.to_datetime(v['sale_date'], format='%Y-%m-%d', errors='coerce')
d2 = pd.to_datetime(v['sale_date'], format='%d-%m-%Y', errors='coerce')
v['data_venda'] = d1.fillna(d2)
v = v.dropna(subset=['data_venda']).copy()

# Vendas diárias (somente dias com registro)
vendas_diarias = v.groupby(v['data_venda'].dt.date, as_index=False)['total'].sum()
vendas_diarias.columns = ['data_venda', 'valor_venda_dia']
vendas_diarias['data_venda'] = pd.to_datetime(vendas_diarias['data_venda'])

# Dimensão calendário completa
inicio = vendas_diarias['data_venda'].min()
fim = vendas_diarias['data_venda'].max()
cal = pd.DataFrame({'data_venda': pd.date_range(inicio, fim, freq='D')})

# Left join para incluir dias sem venda como zero
base = cal.merge(vendas_diarias, on='data_venda', how='left')
base['valor_venda_dia'] = base['valor_venda_dia'].fillna(0.0)

# Dia da semana em português (segunda=0 ... domingo=6)
mapa = {
    0: 'Segunda-feira',
    1: 'Terça-feira',
    2: 'Quarta-feira',
    3: 'Quinta-feira',
    4: 'Sexta-feira',
    5: 'Sábado',
    6: 'Domingo'
}
base['dia_semana_pt'] = base['data_venda'].dt.weekday.map(mapa)

# Export para dashboard
base.to_csv('calendario_com_vendas.csv', index=False, encoding='utf-8')

media = base.groupby('dia_semana_pt', as_index=False)['valor_venda_dia'].mean()
media = media.rename(columns={'valor_venda_dia': 'media_venda'})
media['ordem'] = media['dia_semana_pt'].map({
    'Segunda-feira':1,'Terça-feira':2,'Quarta-feira':3,'Quinta-feira':4,
    'Sexta-feira':5,'Sábado':6,'Domingo':7
})
media = media.sort_values('ordem')

pior = media.sort_values(['media_venda','ordem']).iloc[0]

print('Arquivo gerado: calendario_com_vendas.csv')
print('MEDIAS:')
for _, r in media.iterrows():
    print(f"{r['dia_semana_pt']}={r['media_venda']:.2f}")
print('PIOR_DIA:')
print(f"dia={pior['dia_semana_pt']}")
print(f"media={pior['media_venda']:.2f}")
