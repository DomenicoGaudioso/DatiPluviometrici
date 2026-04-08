import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import linregress, genextreme
import os

# --- FUNZIONE HELPER PER LA TRASPARENZA ---
def hex_to_rgba(hex_color, opacity=0.1):
    """Converte un colore HEX in RGBA per Plotly per garantire la trasparenza delle fasce."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {opacity})'
    return hex_color

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Dashboard Idrologica Avanzata", page_icon="🌧️", layout="wide")

st.title("🌧️ Dashboard Idrologica: Curva di Possibilità Pluviometrica (CPP)")
st.markdown("Strumento avanzato per l'analisi spaziale, statistica e climatica delle precipitazioni estreme.")

# --- GESTIONE PERCORSO FILE ---
NOME_FILE = "Master_Database_Pluviometrico.xlsx"
CARTELLA = "EmiliaRomagna"
PATH_COMPLETO = os.path.join(CARTELLA, NOME_FILE)

COORDINATE_ER = {
    "Bologna": (44.4949, 11.3426), "Parma": (44.8015, 10.3279),
    "Modena": (44.6471, 10.9252), "Reggio": (44.6983, 10.6312),
    "Ravenna": (44.4184, 12.1973), "Rimini": (44.0621, 12.5606),
    "Ferrara": (44.8381, 11.6198), "Forli": (44.2227, 12.0407),
    "Piacenza": (45.0526, 9.6930), "Cesena": (44.1391, 12.2432)
}

@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        st.error(f"❌ File non trovato in: {os.path.abspath(file_path)}")
        return pd.DataFrame()
    return pd.read_excel(file_path)

df = load_data(PATH_COMPLETO)

if not df.empty:
    # --- SIDEBAR: IMPOSTAZIONI ---
    st.sidebar.header("⚙️ Configurazione Analisi")
    
    stazioni_disponibili = sorted(df['Stazione'].dropna().unique())
    stazioni_scelte = st.sidebar.multiselect(
        "1. Scegli le Stazioni (Confronto)", 
        options=stazioni_disponibili,
        default=[stazioni_disponibili[0]] if stazioni_disponibili else []
    )
    
    tempi_ritorno = st.sidebar.multiselect(
        "2. Tempi di Ritorno (Anni)",
        options=[10, 20, 30, 50, 100, 200, 500],
        default=[50, 200]
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Modello Statistico")
    modello_scelto = st.sidebar.radio("Distribuzione dei Valori Estremi:", ["Gumbel (EVI)", "GEV (Generalized)"])
    
    # Se l'utente sceglie più stazioni, spengiamo le fasce di default per non fare confusione
    default_ci = True if len(stazioni_scelte) == 1 else False
    mostra_ci = st.sidebar.checkbox("Mostra Intervalli di Confidenza 95%", value=default_ci)
    
    if mostra_ci and modello_scelto == "GEV (Generalized)":
        st.sidebar.warning("Le fasce di confidenza analitiche sono disponibili solo per il modello di Gumbel.")

    if not stazioni_scelte:
        st.info("Seleziona almeno una stazione dalla barra laterale per iniziare.")
        st.stop()

    df_filtrato = df[df['Stazione'].isin(stazioni_scelte)].copy()
    
    # --- LAYOUT A SCHEDE ---
    tab_mappa, tab_teoria, tab_cpp, tab_trend, tab_distribuzione, tab_export = st.tabs([
        "🗺️ Mappa", "📖 Teoria Idrologica", "📈 CPP & Modelli", 
        "⏳ Trend Storici", "📊 Outlier", "📥 Esporta Dati"
    ])

    # ==========================================
    # TAB 1: MAPPA
    # ==========================================
    with tab_mappa:
        st.header("Localizzazione Stazioni")
        dati_mappa = []
        for staz in stazioni_scelte:
            lat, lon = None, None
            for key, coords in COORDINATE_ER.items():
                if key.lower() in staz.lower():
                    lat, lon = coords
                    break
            if not lat:
                lat, lon = 44.5 + np.random.uniform(-0.3, 0.3), 11.0 + np.random.uniform(-0.5, 0.5)
            dati_mappa.append({"Stazione": staz, "lat": lat, "lon": lon})
            
        st.map(pd.DataFrame(dati_mappa), zoom=7)

    # ==========================================
    # TAB 2: TEORIA
    # ==========================================
    with tab_teoria:
        st.header("Fondamenti Teorici")
        st.latex(r"h(t) = a \cdot t^n")
        col1, col2 = st.columns(2)
        with col1:
            st.info("**Distribuzione di Gumbel (EVI)**")
            st.latex(r"y_T = -\ln\left(-\ln\left(1 - \frac{1}{Tr}\right)\right) \implies h_T = u + \frac{y_T}{\alpha}")
        with col2:
            st.success("**Distribuzione GEV**")
            st.latex(r"H(x) = \exp\left\{-\left[1 + \xi\left(\frac{x-\mu}{\sigma}\right)\right]^{-1/\xi}\right\}")

    # ==========================================
    # TAB 3: CPP E MODELLI
    # ==========================================
    with tab_cpp:
        if tempi_ritorno:
            durate_ore = [1, 3, 6, 12, 24]
            colonne = ['1h_mm', '3h_mm', '6h_mm', '12h_mm', '24h_mm']
            
            fig_cpp = go.Figure()
            t_line = np.linspace(1, 24, 100)
            dati_finali_cpp = []
            colori_stazioni = px.colors.qualitative.G10 

            for idx, stazione in enumerate(stazioni_scelte):
                colore_hex = colori_stazioni[idx % len(colori_stazioni)]
                colore_rgba_area = hex_to_rgba(colore_hex, opacity=0.15) 
                
                df_staz = df_filtrato[df_filtrato['Stazione'] == stazione]
                N_anni = len(df_staz)
                
                # --- AGGIUNTA DELLA NUVOLA DEI PUNTI STORICI REALI ---
                for d, col in zip(durate_ore, colonne):
                    fig_cpp.add_trace(go.Scatter(
                        x=[d] * N_anni, 
                        y=df_staz[col], 
                        mode='markers',
                        marker=dict(color='gray', opacity=0.3, size=5),
                        name=f'Dati Storici {stazione}' if d == 1 else "",
                        showlegend=True if (d == 1 and idx == 0) else False,
                        hoverinfo='y+text',
                        text=df_staz['Anno'].astype(str) + " (" + df_staz[col].astype(str) + " mm)"
                    ))
                
                h_stimate_dict = {Tr: [] for Tr in tempi_ritorno}
                h_err_dict = {Tr: [] for Tr in tempi_ritorno} 
                
                # Calcoli statistici
                for col in colonne:
                    dati_serie = df_staz[col].dropna()
                    if len(dati_serie) > 2:
                        if modello_scelto == "Gumbel (EVI)":
                            media, dev_std = dati_serie.mean(), dati_serie.std()
                            alpha = np.pi / (dev_std * np.sqrt(6))
                            u = media - (0.5772 / alpha)
                            
                            for Tr in tempi_ritorno:
                                y_Tr = -np.log(-np.log(1 - 1/Tr))
                                h_Tr = u + (y_Tr / alpha)
                                h_stimate_dict[Tr].append(h_Tr)
                                
                                K = (y_Tr - 0.5772) / (np.pi / np.sqrt(6))
                                var_h = (dev_std**2 / N_anni) * (1 + 1.1396 * K + 1.1000 * K**2)
                                h_err_dict[Tr].append(1.96 * np.sqrt(var_h))
                                
                        elif modello_scelto == "GEV (Generalized)":
                            shape, loc, scale = genextreme.fit(dati_serie)
                            for Tr in tempi_ritorno:
                                h_stimate_dict[Tr].append(genextreme.ppf(1 - 1/Tr, shape, loc=loc, scale=scale))
                                h_err_dict[Tr].append(0)
                
                # Generazione curve
                for Tr in tempi_ritorno:
                    if len(h_stimate_dict[Tr]) == 5:
                        h_vals = np.array(h_stimate_dict[Tr])
                        slope, intercept, r_value, _, _ = linregress(np.log(durate_ore), np.log(h_vals))
                        
                        n_param, a_param = slope, np.exp(intercept)
                        dati_finali_cpp.append({
                            "Stazione": stazione, "Tr": Tr, 
                            "a": round(a_param, 2), "n": round(n_param, 3), 
                            "R²": round(r_value**2, 4), "Anni Dati": N_anni
                        })
                        
                        h_line = a_param * (t_line ** n_param)
                        nome_traccia = f"{stazione} - Tr {Tr}"
                        
                        # PLOT AREE DI CONFIDENZA TRASPARENTI
                        if mostra_ci and modello_scelto == "Gumbel (EVI)":
                            err_vals = np.array(h_err_dict[Tr])
                            upper_bound = a_param * (t_line ** n_param) + np.interp(t_line, durate_ore, err_vals)
                            lower_bound = a_param * (t_line ** n_param) - np.interp(t_line, durate_ore, err_vals)
                            
                            fig_cpp.add_trace(go.Scatter(x=t_line, y=upper_bound, mode='lines', line=dict(width=0), showlegend=False, hoverinfo='skip'))
                            fig_cpp.add_trace(go.Scatter(
                                x=t_line, y=lower_bound, mode='lines', line=dict(width=0),
                                fill='tonexty', fillcolor=colore_rgba_area,
                                showlegend=False, hoverinfo='skip'
                            ))

                        # PLOT CURVE E PUNTI CALCOLATI
                        fig_cpp.add_trace(go.Scatter(x=t_line, y=h_line, mode='lines', name=nome_traccia, line=dict(color=colore_hex, width=3)))
                        fig_cpp.add_trace(go.Scatter(x=durate_ore, y=h_vals, mode='markers', name=f"Punti {stazione}", marker=dict(color=colore_hex, symbol='x', size=8), showlegend=False))

            col_res, col_plot = st.columns([1, 2])
            with col_res:
                st.write(f"### Parametri $a$ e $n$")
                st.dataframe(pd.DataFrame(dati_finali_cpp), hide_index=True, use_container_width=True)

            with col_plot:
                fig_cpp.update_layout(xaxis_title="Durata t (ore)", yaxis_title="Precipitazione h (mm)", template="plotly_white", height=600)
                if st.checkbox("Visualizza assi in scala Log-Log (Linearizza le curve)"):
                    fig_cpp.update_xaxes(type="log")
                    fig_cpp.update_yaxes(type="log")
                st.plotly_chart(fig_cpp, use_container_width=True)
        else:
            st.warning("Seleziona almeno un Tempo di Ritorno per avviare il calcolo.")

    # ==========================================
    # TAB 4: TREND STORICI
    # ==========================================
    with tab_trend:
        durata_trend = st.radio("Seleziona la durata da analizzare:", ['1h_mm', '3h_mm', '6h_mm', '12h_mm', '24h_mm'], horizontal=True)
        df_trend = df_filtrato.dropna(subset=['Anno', durata_trend]).sort_values(by='Anno')
        if not df_trend.empty:
            fig_trend = px.scatter(df_trend, x='Anno', y=durata_trend, color='Stazione', trendline="ols",
                                   title=f"Andamento e linee di tendenza per piogge di {durata_trend.split('_')[0]}")
            fig_trend.update_traces(mode='lines+markers')
            st.plotly_chart(fig_trend, use_container_width=True)

    # ==========================================
    # TAB 5: DISTRIBUZIONE E OUTLIER
    # ==========================================
    with tab_distribuzione:
        df_melted = df_filtrato.melt(id_vars=['Anno', 'Stazione'], value_vars=['1h_mm', '3h_mm', '6h_mm', '12h_mm', '24h_mm'], var_name='Durata', value_name='Millimetri')
        fig_box = px.box(df_melted, x='Durata', y='Millimetri', color='Stazione', points="outliers",
                         title="Confronto Boxplot: Mediane e Nubifragi anomali (Outlier)")
        st.plotly_chart(fig_box, use_container_width=True)

    # ==========================================
    # TAB 6: ESPORTA DATI
    # ==========================================
    with tab_export:
        if 'dati_finali_cpp' in locals() and len(dati_finali_cpp) > 0:
            csv = pd.DataFrame(dati_finali_cpp).to_csv(index=False, sep=';', decimal=',').encode('utf-8')
            st.download_button("Scarica Parametri CPP (CSV)", data=csv, file_name="Parametri_CPP.csv", mime="text/csv")
            st.info("Per esportare i grafici in alta qualità (PNG), usa l'icona della macchina fotografica in alto a destra su ogni grafico.")