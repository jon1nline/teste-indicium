import pandas as pd
import re
import unicodedata

# Carregamento da base bruta de dados dos produtos
df_produtos = pd.read_csv('produtos_raw.csv')

def normalizar_produtos(df):
    df_clean = df.copy()

    # Mapeamento baseado em palavras-chave para lidar com ruídos
    def limpar_categoria(txt):
        if not isinstance(txt, str):
            return "indefinido"

        txt_norm = unicodedata.normalize('NFKD', txt)
        txt_norm = ''.join(ch for ch in txt_norm if not unicodedata.combining(ch))
        txt_norm = txt_norm.lower()
        txt_norm = re.sub(r'[^a-z]', '', txt_norm)

        # Utilizando radicais para identificar a categoria correta, mesmo com erros de grafia.
        if re.search(r'eletr|eltr|eletroni|eletrun|eletronisc|eletronicoz', txt_norm):
            return 'eletrônicos'
        if re.search(r'propul|prop', txt_norm):
            return 'propulsão'
        if re.search(r'ancor|encor', txt_norm):
            return 'ancoragem'
        return 'indefinido'

    df_clean['actual_category'] = df_clean['actual_category'].apply(limpar_categoria)

    # O campo 'price' pode vir em formatos diferentes (com vírgula ou ponto decimal).
    # A função abaixo normaliza para número sem perder centavos.
    def limpar_preco(valor):
        if pd.isna(valor):
            return None

        texto = str(valor).replace('R$', '').strip()
        texto = re.sub(r'\s+', '', texto)

        if ',' in texto and '.' in texto:
            if texto.rfind(',') > texto.rfind('.'):
                texto = texto.replace('.', '').replace(',', '.')
            else:
                texto = texto.replace(',', '')
        elif ',' in texto:
            texto = texto.replace(',', '.')

        try:
            return float(texto)
        except ValueError:
            return None

    df_clean['price'] = df_clean['price'].apply(limpar_preco)

    # Considerando duplicatas de produtos com o mesmo 'code',
    # será mantida apenas a primeira ocorrência.
    linhas_antes = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset=['code'], keep='first')
    linhas_depois = len(df_clean)
    
    print(f"Normalização concluída. Duplicatas removidas: {linhas_antes - linhas_depois}")
    return df_clean

# Execução do processo
df_produtos_clean = normalizar_produtos(df_produtos)

# Geração de arquivo final limpo
arquivo_saida = 'produtos_limpos.csv'
df_produtos_clean.to_csv(arquivo_saida, index=False, encoding='utf-8')
print(f"Arquivo gerado: {arquivo_saida}")

# Visualização do resultado para o Gabriel com limitação de 5 linhas
print(df_produtos_clean.head())