import pandas as pd
import numpy as np

v = pd.read_csv('vendas_2023_2024.csv')
c = pd.read_csv('custos_importacao.csv')
fx = pd.read_csv('cotacao_dolar.csv')

v['data_venda'] = pd.to_datetime(v['sale_date'], format='%Y-%m-%d', errors='coerce')
m = v['data_venda'].isna()
v.loc[m, 'data_venda'] = pd.to_datetime(v.loc[m, 'sale_date'], format='%d-%m-%Y', errors='coerce')
v = v.dropna(subset=['data_venda']).copy().rename(columns={'id_product':'id_produto','total':'receita_venda'})

c['inicio_vigencia'] = pd.to_datetime(c['start_date'], format='%d/%m/%Y', errors='coerce')
c = c.dropna(subset=['inicio_vigencia']).copy().rename(columns={'product_id':'id_produto','usd_price':'custo_usd'})

fx = fx.rename(columns={fx.columns[0]:'taxa', fx.columns[1]:'dh'})
fx['data_cambio'] = pd.to_datetime(fx['dh'].astype(str).str[:10], errors='coerce')
fx = fx.dropna(subset=['data_cambio']).sort_values('data_cambio').reset_index(drop=True)
fx_dates = fx['data_cambio'].values.astype('datetime64[ns]')
fx_vals = fx['taxa'].astype(float).values

sale_dates = v['data_venda'].values.astype('datetime64[ns]')
pos_fx = np.searchsorted(fx_dates, sale_dates, side='right') - 1
v['taxa'] = np.where(pos_fx>=0, fx_vals[np.clip(pos_fx,0,len(fx_vals)-1)], np.nan)

v['custo_usd']=np.nan
for pid, idx in v.groupby('id_produto').groups.items():
    hist = c[c['id_produto']==pid].sort_values('inicio_vigencia')
    if hist.empty: continue
    d=hist['inicio_vigencia'].values.astype('datetime64[ns]')
    val=hist['custo_usd'].astype(float).values
    s=v.loc[list(idx),'data_venda'].values.astype('datetime64[ns]')
    p=np.searchsorted(d,s,side='right')-1
    out=np.full(len(s), np.nan)
    ok=p>=0
    out[ok]=val[p[ok]]
    v.loc[list(idx),'custo_usd']=out

b=v.dropna(subset=['taxa','custo_usd']).copy()
b['custo_unit_brl']=b['custo_usd']*b['taxa']
b['custo_total_brl_qtd']=b['qtd']*b['custo_unit_brl']

print('receita media', b['receita_venda'].mean())
print('custo unit medio', b['custo_unit_brl'].mean())
print('custo total(qtd) medio', b['custo_total_brl_qtd'].mean())
print('qtd media', b['qtd'].mean())

# top abs com qtd
b['perda_qtd']=np.where(b['receita_venda']<b['custo_total_brl_qtd'], b['custo_total_brl_qtd']-b['receita_venda'],0)
agg1=b.groupby('id_produto',as_index=False).agg(rec=('receita_venda','sum'),prej=('perda_qtd','sum'))
agg1['pct']=np.where(agg1['rec']>0,agg1['prej']/agg1['rec']*100,0)
print('top_qtd', agg1.sort_values('prej',ascending=False).head(1).to_dict('records')[0])

# top sem qtd
b['perda_unit']=np.where(b['receita_venda']<b['custo_unit_brl'], b['custo_unit_brl']-b['receita_venda'],0)
agg2=b.groupby('id_produto',as_index=False).agg(rec=('receita_venda','sum'),prej=('perda_unit','sum'))
agg2['pct']=np.where(agg2['rec']>0,agg2['prej']/agg2['rec']*100,0)
print('top_unit', agg2.sort_values('prej',ascending=False).head(1).to_dict('records')[0])
