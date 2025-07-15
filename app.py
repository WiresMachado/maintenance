import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io

st.set_page_config(page_title="Análise de Consumo de Peças", layout="wide")
st.title("📊 Análise de Consumo e Durabilidade de Peças")

# === Upload dos arquivos ===
st.sidebar.header("🔽 Upload de Arquivos")
caracteristica_file = st.sidebar.file_uploader("Tabela Caracteristica", type="xlsx")
chassi_file = st.sidebar.file_uploader("Tabela Chassi", type="xlsx")

if caracteristica_file and chassi_file:
    df_caracteristica = pd.read_excel(caracteristica_file, engine="openpyxl")
    df_chassi = pd.read_excel(chassi_file, engine="openpyxl")

    with st.spinner("Processando dados..."):
        # === TAXA CONSUMO ===
        df_chassi_base = df_chassi.copy()
        bins = np.arange(0, df_chassi_base['Hectare'].max() + 1000, 1000)
        labels = [f"{int(b)} – {int(b + 1000)}" for b in bins[:-1]]
        df_chassi_base['Faixa hectare'] = pd.cut(df_chassi_base['Hectare'], bins=bins, labels=labels, right=False)
        df_chassi_base = df_chassi_base.dropna(subset=['Faixa hectare'])

        df_taxa_base = df_chassi_base.groupby(['Faixa hectare', 'Código'])['Chassi'].nunique().reset_index().rename(columns={'Chassi': 'Qtd chassi'})
        df_taxa = df_taxa_base.merge(
            df_caracteristica[['Código', 'Família', 'Proporção', 'Qtd/proporção', 'Descrição']],
            on='Código',
            how='left'
        )

        df_consumo = df_chassi_base.groupby(['Faixa hectare', 'Código'])[['Qtd consumido']].sum().reset_index()
        df_taxa = df_taxa.merge(df_consumo, on=['Faixa hectare', 'Código'], how='left')

        df_chassi_unico = df_chassi_base[['Faixa hectare', 'Código', 'Chassi', 'Linha']].drop_duplicates()
        df_chassi_unico = df_chassi_unico.merge(df_caracteristica[['Código', 'Proporção', 'Qtd/proporção']], on='Código', how='left')

        df_chassi_unico['Qtd por chassi'] = np.where(
            df_chassi_unico['Proporção'] == 'Linha',
            df_chassi_unico['Qtd/proporção'] * df_chassi_unico['Linha'],
            df_chassi_unico['Qtd/proporção']
        )

        df_qtd_max_final = df_chassi_unico.groupby(['Faixa hectare', 'Código'])['Qtd por chassi'].sum().reset_index().rename(columns={'Qtd por chassi': 'Qtd máxima'})
        df_taxa = df_taxa.merge(df_qtd_max_final, on=['Faixa hectare', 'Código'], how='left')

        df_taxa['% Consumo'] = df_taxa['Qtd consumido'] / df_taxa['Qtd máxima']
        df_taxa = df_taxa.replace([np.inf, -np.inf], np.nan).dropna(subset=['% Consumo'])
        df_taxa['% Consumo'] = df_taxa['% Consumo'].round(2)

        colunas_taxa = [
            'Faixa hectare', 'Qtd chassi', 'Família', 'Proporção', 'Qtd/proporção',
            'Qtd máxima', 'Código', 'Descrição', 'Qtd consumido', '% Consumo'
        ]
        df_taxa_saida = df_taxa[colunas_taxa]

        # === DURABILIDADE ===
        df_chassi_cod = df_chassi[['Código', 'Chassi', 'Linha']].drop_duplicates()
        df_chassi_cod = df_chassi_cod.merge(df_caracteristica[['Código', 'Proporção', 'Qtd/proporção']], on='Código', how='left')

        df_chassi_cod['Qtd por chassi'] = np.where(
            df_chassi_cod['Proporção'] == 'Linha',
            df_chassi_cod['Qtd/proporção'] * df_chassi_cod['Linha'],
            df_chassi_cod['Qtd/proporção']
        )

        df_qtd_max = df_chassi_cod.groupby('Código')['Qtd por chassi'].sum().reset_index().rename(columns={'Qtd por chassi': 'Qtd máxima'})
        df_qtd_chassi = df_chassi_cod.groupby('Código').agg({
            'Chassi': pd.Series.nunique,
            'Linha': 'sum'
        }).reset_index().rename(columns={'Chassi': 'Qtd chassi', 'Linha': 'Linha total'})

        df_consumo = df_chassi.groupby('Código')['Qtd consumido'].sum().reset_index()
        df_max_hectare = df_chassi.groupby('Chassi')['Hectare'].max().reset_index()
        df_chassi_codigo = df_chassi[['Código', 'Chassi']].drop_duplicates()
        df_hectares = df_chassi_codigo.merge(df_max_hectare, on='Chassi', how='left')
        df_hectares_total = df_hectares.groupby('Código')['Hectare'].sum().reset_index().rename(columns={'Hectare': 'Hectare acumulado'})

        df_durab = df_qtd_chassi.merge(df_qtd_max, on='Código')
        df_durab = df_durab.merge(df_consumo, on='Código')
        df_durab = df_durab.merge(df_hectares_total, on='Código')
        df_durab = df_durab.merge(df_caracteristica[['Código', 'Família', 'Proporção', 'Qtd/proporção', 'Descrição']], on='Código')

        df_durab['% Consumo'] = df_durab['Qtd consumido'] / df_durab['Qtd máxima']
        df_durab = df_durab.replace([np.inf, -np.inf], np.nan).dropna(subset=['% Consumo', 'Qtd máxima', 'Hectare acumulado'])
        df_durab['Consumo hectare'] = (df_durab['Hectare acumulado'] / df_durab['% Consumo']) / df_durab['Qtd máxima']
        df_durab['% Consumo'] = df_durab['% Consumo'].round(2)
        df_durab['Consumo hectare'] = df_durab['Consumo hectare'].round(2)

        colunas_durab = [
            'Qtd chassi', 'Família', 'Proporção', 'Qtd/proporção',
            'Qtd máxima', 'Código', 'Descrição', 'Qtd consumido',
            '% Consumo', 'Consumo hectare'
        ]
        df_durab_saida = df_durab[colunas_durab]

    st.success("✅ Processamento concluído!")

    # === Exportação ===
    st.markdown("### 📄 Exportação de Resultados")
    col1, col2 = st.columns(2)
    with col1:
        buffer1 = io.BytesIO()
        df_taxa_saida.to_excel(buffer1, index=False, engine='openpyxl')
        buffer1.seek(0)
        st.download_button(
            label="📅 Baixar Taxa Consumo",
            data=buffer1,
            file_name="Taxa consumo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        buffer2 = io.BytesIO()
        df_durab_saida.to_excel(buffer2, index=False, engine='openpyxl')
        buffer2.seek(0)
        st.download_button(
            label="📅 Baixar Durabilidade",
            data=buffer2,
            file_name="Durabilidade.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # === Filtros ===
    st.markdown("### 🔍 Filtros")
    codigo = st.text_input("Filtrar por código da peça")
    familia = st.selectbox("Filtrar por família", options=[''] + sorted(df_taxa_saida['Família'].dropna().unique().tolist()))
    proporcao = st.selectbox("Filtrar por proporção", options=[''] + sorted(df_taxa_saida['Proporção'].dropna().unique().tolist()))

    df_filtro = df_taxa_saida.copy()
    df_filtro['Peça'] = df_filtro['Código'].astype(str) + ' – ' + df_filtro['Descrição']
    df_filtro['% Consumo (%)'] = df_filtro['% Consumo'] * 100

    if codigo:
        df_filtro = df_filtro[df_filtro['Código'].astype(str).str.contains(codigo.strip())]
    if familia:
        df_filtro = df_filtro[df_filtro['Família'] == familia]
    if proporcao:
        df_filtro = df_filtro[df_filtro['Proporção'] == proporcao]

    eixo_y = "Família" if familia == '' else "Peça"

    if not df_filtro.empty:
        st.plotly_chart(
            px.density_heatmap(
                df_filtro,
                x="Faixa hectare",
                y=eixo_y,
                z="% Consumo (%)",
                text_auto=".2f",
                color_continuous_scale=[(0.0, "green"), (0.5, "yellow"), (1.0, "red")],
                labels={"% Consumo (%)": "% Consumo"},
                title="Mapa de Calor – % Consumo por Faixa de Hectare"
            ),
            use_container_width=True
        )

    df_durab_plot = df_durab_saida.copy()
    df_durab_plot['Peça'] = df_durab_plot['Código'].astype(str) + ' – ' + df_durab_plot['Descrição']

    if codigo:
        df_durab_plot = df_durab_plot[df_durab_plot['Código'].astype(str).str.contains(codigo.strip())]
    if familia:
        df_durab_plot = df_durab_plot[df_durab_plot['Família'] == familia]
    if proporcao:
        df_durab_plot = df_durab_plot[df_durab_plot['Proporção'] == proporcao]

    eixo_x = "Família" if familia == '' else "Peça"

    if not df_durab_plot.empty:
        df_plot = df_durab_plot.copy()
        if eixo_x == "Família":
            df_plot = df_plot.groupby("Família", as_index=False)["Consumo hectare"].mean()
        df_plot = df_plot.sort_values(by="Consumo hectare", ascending=False)

        st.plotly_chart(
            px.bar(
                df_plot,
                x=eixo_x,
                y="Consumo hectare",
                title="Consumo por Hectare – Peças ou Famílias",
                labels={"Consumo hectare": "Consumo por Hectare"},
                text_auto=".2f",
                color="Consumo hectare",
                color_continuous_scale=[(0.0, "red"), (0.5, "yellow"), (1.0, "green")]
            ),
            use_container_width=True
        )


 #.\venv\Scripts\Activate.ps1
 # streamlit run app.py    