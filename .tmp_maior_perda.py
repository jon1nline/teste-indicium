import pandas as pd
import numpy as np

v = pd.read_csv('vendas_2023_2024.csv')
c = pd.read_csv('custos_importacao.csv')
fx = pd.read_csv('cotacao_dolar.csv')

v['data_venda'] = pd.to_datetime(v['sale_date'], format='%Y-%m-%d', errors='coerce')
mask = v['data_venda'].isna()
v.loc[mask, 'data_venda'] = pd.to_datetime(v.loc[mask, 'sale_date'], format='%d-%m-%Y', errors='coerce')
v = v.dropna(subset=['data_venda']).copy()

v = v.rename(columns={'id_product':'id_produto', 'total':'receita_venda'})

c['inicio_vigencia'] = pd.to_datetime(c['start_date'], format='%d/%m/%Y', errors='coerce')
c = c.dropna(subset=['inicio_vigencia']).copy()
c = c.rename(columns={'product_id':'id_produto', 'usd_price':'custo_usd'})

fx = fx.rename(columns={fx.columns[0]:'taxa_cambio_data', fx.columns[1]:'data_hora_cotacao'})
fx['data_cambio'] = pd.to_datetime(fx['data_hora_cotacao'].astype(str).str.slice(0,10), format='%Y-%m-%d', errors='coerce')
fx = fx.dropna(subset=['data_cambio']).copy()

# Câmbio vigente até a data da venda
fx = fx.sort_values('data_cambio').reset_index(drop=True)
fx_dates = fx['data_cambio'].values.astype('datetime64[ns]')
fx_vals = fx['taxa_cambio_data'].astype(float).values
sale_dates = v['data_venda'].values.astype('datetime64[ns]')
pos_fx = np.searchsorted(fx_dates, sale_dates, side='right') - 1
v['taxa_cambio_data'] = np.where(pos_fx >= 0, fx_vals[np.clip(pos_fx, 0, len(fx_vals)-1)], np.nan)

# Custo USD vigente por produto até a data da venda
v['custo_usd'] = np.nan
for pid, idx in v.groupby('id_produto').groups.items():
    rows = np.array(list(idx))
    vc = c[c['id_produto'] == pid].sort_values('inicio_vigencia')
    if vc.empty:
        continue
    c_dates = vc['inicio_vigencia'].values.astype('datetime64[ns]')
    c_vals = vc['custo_usd'].astype(float).values
    s_dates = v.loc[rows, 'data_venda'].values.astype('datetime64[ns]')
    pos_c = np.searchsorted(c_dates, s_dates, side='right') - 1
    valid = pos_c >= 0
    out = np.full(len(rows), np.nan)
    if valid.any():
        out[valid] = c_vals[pos_c[valid]]
    v.loc[rows, 'custo_usd'] = out

base = v.dropna(subset=['taxa_cambio_data','custo_usd']).copy()
base['custo_total_brl'] = base['qtd'] * base['custo_usd'] * base['taxa_cambio_data']
base['perda_venda'] = np.where(base['receita_venda'] < base['custo_total_brl'], base['custo_total_brl'] - base['receita_venda'], 0.0)

agg = base.groupby('id_produto', as_index=False).agg(
    receita_total=('receita_venda','sum'),
    prejuizo_total=('perda_venda','sum')
)
agg['percentual_perda'] = np.where(agg['receita_total']>0, agg['prejuizo_total']/agg['receita_total']*100, 0)

best = agg.sort_values(['percentual_perda','id_produto'], ascending=[False, True]).iloc[0]
print(f"id_produto={int(best['id_produto'])}")
print(f"percentual_perda={best['percentual_perda']:.4f}%")
print(f"receita_total={best['receita_total']:.2f}")
print(f"prejuizo_total={best['prejuizo_total']:.2f}")
