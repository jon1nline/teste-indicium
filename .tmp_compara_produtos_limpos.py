import pandas as pd
import numpy as np

# Resultado anterior registrado
anterior = {
    'id_produto': 83,
    'percentual_perda': 0.3670,
    'prejuizo_total': 162871.86
}

v = pd.read_csv('vendas_2023_2024.csv')
c = pd.read_csv('custos_importacao.csv')
fx = pd.read_csv('cotacao_dolar.csv')
p = pd.read_csv('produtos_limpos.csv')

# Preparação de datas
dt1 = pd.to_datetime(v['sale_date'], format='%Y-%m-%d', errors='coerce')
dt2 = pd.to_datetime(v['sale_date'], format='%d-%m-%Y', errors='coerce')
v['data_venda'] = dt1.fillna(dt2)
v = v.dropna(subset=['data_venda']).copy()
v = v.rename(columns={'id_product':'id_produto', 'total':'receita_venda'})

c['inicio_vigencia'] = pd.to_datetime(c['start_date'], format='%d/%m/%Y', errors='coerce')
c = c.dropna(subset=['inicio_vigencia']).copy()
c = c.rename(columns={'product_id':'id_produto', 'usd_price':'custo_usd'})

fx = fx.rename(columns={fx.columns[0]:'taxa_cambio_data', fx.columns[1]:'data_hora_cotacao'})
fx['data_cambio'] = pd.to_datetime(fx['data_hora_cotacao'].astype(str).str.slice(0,10), format='%Y-%m-%d', errors='coerce')
fx = fx.dropna(subset=['data_cambio']).sort_values('data_cambio').reset_index(drop=True)

# Câmbio vigente até data da venda
fx_dates = fx['data_cambio'].values.astype('datetime64[ns]')
fx_vals = fx['taxa_cambio_data'].astype(float).values
sale_dates = v['data_venda'].values.astype('datetime64[ns]')
pos_fx = np.searchsorted(fx_dates, sale_dates, side='right') - 1
v['taxa_cambio_data'] = np.where(pos_fx >= 0, fx_vals[np.clip(pos_fx, 0, len(fx_vals)-1)], np.nan)

# Custo USD vigente por produto
v['custo_usd'] = np.nan
for pid, idx in v.groupby('id_produto').groups.items():
    hist = c[c['id_produto'] == pid].sort_values('inicio_vigencia')
    if hist.empty:
        continue
    c_dates = hist['inicio_vigencia'].values.astype('datetime64[ns]')
    c_vals = hist['custo_usd'].astype(float).values
    s_dates = v.loc[list(idx), 'data_venda'].values.astype('datetime64[ns]')
    pos = np.searchsorted(c_dates, s_dates, side='right') - 1
    out = np.full(len(pos), np.nan)
    ok = pos >= 0
    out[ok] = c_vals[pos[ok]]
    v.loc[list(idx), 'custo_usd'] = out

base = v.dropna(subset=['taxa_cambio_data', 'custo_usd']).copy()
base['custo_brl'] = base['custo_usd'] * base['taxa_cambio_data']
base['prejuizo_venda'] = np.where(base['receita_venda'] < base['custo_brl'], base['custo_brl'] - base['receita_venda'], 0.0)

agg = base.groupby('id_produto', as_index=False).agg(
    receita_total=('receita_venda', 'sum'),
    prejuizo_total=('prejuizo_venda', 'sum')
)
agg['percentual_perda'] = np.where(agg['receita_total'] > 0, agg['prejuizo_total'] / agg['receita_total'] * 100, 0.0)

# Enriquecimento com produtos_limpos
p = p.rename(columns={'code':'id_produto', 'name':'nome_produto'})
agg = agg.merge(p[['id_produto','nome_produto','actual_category']], on='id_produto', how='left')

atual = agg.sort_values(['percentual_perda', 'id_produto'], ascending=[False, True]).iloc[0]

print('RESULTADO_ATUAL')
print(f"id_produto={int(atual['id_produto'])}")
print(f"nome_produto={atual['nome_produto']}")
print(f"categoria={atual['actual_category']}")
print(f"percentual_perda={atual['percentual_perda']:.4f}%")
print(f"prejuizo_total={atual['prejuizo_total']:.2f}")

mesmo_id = int(atual['id_produto']) == anterior['id_produto']
delta_pct = float(atual['percentual_perda']) - anterior['percentual_perda']
delta_prej = float(atual['prejuizo_total']) - anterior['prejuizo_total']

print('\nCOMPARACAO_ANTERIOR_X_ATUAL')
print(f"mesmo_id={mesmo_id}")
print(f"delta_percentual_perda={delta_pct:.6f}")
print(f"delta_prejuizo_total={delta_prej:.6f}")
