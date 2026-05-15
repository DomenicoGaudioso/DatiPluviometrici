import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.stats import linregress, genextreme
import os
from word_report import genera_relazione_word
from src import (formule_cpp_base, formule_sezione_trapezoidale,
                 hex_to_rgba, tirante_trapezoidale_bisezione)

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Dashboard Idrologica Avanzata", page_icon="ðŸŒ§ï¸", layout="wide")

st.title("ðŸŒ§ï¸ Dashboard Idrologica: Curva di PossibilitÃ  Pluviometrica (CPP)")
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
        st.error(f"âŒ File non trovato in: {os.path.abspath(file_path)}")
        return pd.DataFrame()
    return pd.read_excel(file_path)

df = load_data(PATH_COMPLETO)

if not df.empty:
    # --- SIDEBAR: IMPOSTAZIONI ---
    st.sidebar.header("âš™ï¸ Configurazione Analisi")
    
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
    
    # Se l'utente sceglie piÃ¹ stazioni, spengiamo le fasce di default per non fare confusione
    default_ci = True if len(stazioni_scelte) == 1 else False
    mostra_ci = st.sidebar.checkbox("Mostra Intervalli di Confidenza 95%", value=default_ci)
    
    if mostra_ci and modello_scelto == "GEV (Generalized)":
        st.sidebar.warning("Le fasce di confidenza analitiche sono disponibili solo per il modello di Gumbel.")

    if not stazioni_scelte:
        st.info("Seleziona almeno una stazione dalla barra laterale per iniziare.")
        st.stop()

    df_filtrato = df[df['Stazione'].isin(stazioni_scelte)].copy()
    
    # --- SCHERMATA UNICA IN STILE RELAZIONE ---
    tab_mappa, tab_teoria, tab_cpp, tab_trend, tab_distribuzione, tab_idraulica, tab_export = [
        st.container() for _ in range(7)
    ]

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
        st.subheader("Formule operative")
        st.dataframe(pd.DataFrame(formule_cpp_base()), hide_index=True, use_container_width=True)

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
                            "RÂ²": round(r_value**2, 4), "Anni Dati": N_anni
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
    # TAB 6: SEZIONE IDRAULICA E BATTENTE
    # ==========================================
    with tab_idraulica:
        st.header("Calcolo del Tirante Idrico (Moto Uniforme)")
        st.write("Verifica l'altezza dell'acqua per una portata di progetto assegnata (es. la stima 200-ennale) in una sezione trapezoidale idealizzata del fiume.")
        
        col_inp, col_plot = st.columns([1, 2])
        
        with col_inp:
            st.subheader("Parametri dell'Alveo")
            Q_prog = st.number_input("Portata di Progetto Q (mÂ³/s)", value=250.0, step=10.0)
            b = st.number_input("Larghezza del fondo b (m)", value=15.0, step=1.0)
            z = st.number_input("Pendenza scarpata z (H:V, es. 2 per 2:1)", value=2.0, step=0.5)
            S = st.number_input("Pendenza longitudinale alveo i (m/m)", value=0.002, format="%.4f", step=0.0005)
            Ks = st.number_input("Scabrezza Strickler Ks (m^(1/3)/s)", value=30.0, step=5.0, help="Fiumi naturali: 25-35. Canali in calcestruzzo: 60-70.")
            
        risultato_sezione = tirante_trapezoidale_bisezione(Q_prog, b, z, Ks, S)
        h_calc = risultato_sezione["tirante_m"]
        Area_finale = risultato_sezione["area_m2"]
        Velocita = risultato_sezione["velocita_ms"]
        df_formule_sezione = pd.DataFrame(
            formule_sezione_trapezoidale(risultato_sezione, b, z, Ks, S)
        )
        
        with col_plot:
            st.subheader("Risultati idraulici")
            st.dataframe(pd.DataFrame([
                {"Parametro": "Tirante / battente", "Valore": f"{h_calc:.2f}", "Unita": "m"},
                {"Parametro": "Velocita media", "Valore": f"{Velocita:.2f}", "Unita": "m/s"},
                {"Parametro": "Area bagnata", "Valore": f"{Area_finale:.2f}", "Unita": "m2"},
            ]), hide_index=True, use_container_width=True)
            st.dataframe(df_formule_sezione, hide_index=True, use_container_width=True)

            # --- DISEGNO DELLA SEZIONE CON PLOTLY ---
            fig_sez = go.Figure()
            
            # Geometria del canale (aggiungiamo 2 metri di franco rispetto al livello dell'acqua per visualizzare bene gli argini)
            H_tot = h_calc + 2.0
            x_fondo_sx = -b/2
            x_fondo_dx = b/2
            x_argine_sx = x_fondo_sx - z * H_tot
            x_argine_dx = x_fondo_dx + z * H_tot
            
            x_acqua_sx = x_fondo_sx - z * h_calc
            x_acqua_dx = x_fondo_dx + z * h_calc
            
            # Poligono dell'Acqua (Azzurro semitrasparente)
            fig_sez.add_trace(go.Scatter(
                x=[x_acqua_sx, x_fondo_sx, x_fondo_dx, x_acqua_dx, x_acqua_sx],
                y=[h_calc, 0, 0, h_calc, h_calc],
                fill='toself',
                fillcolor='rgba(0, 191, 255, 0.5)',
                line=dict(color='blue', width=2),
                name='Acqua',
                hoverinfo='skip'
            ))
            
            # Linea del Terreno/Alveo (Marrone scuro)
            fig_sez.add_trace(go.Scatter(
                x=[x_argine_sx, x_fondo_sx, x_fondo_dx, x_argine_dx],
                y=[H_tot, 0, 0, H_tot],
                mode='lines',
                line=dict(color='#8B4513', width=5),
                name='Profilo Alveo',
                hoverinfo='skip'
            ))
            
            # Linea tratteggiata per il Pelo Libero
            fig_sez.add_trace(go.Scatter(
                x=[x_argine_sx, x_argine_dx],
                y=[h_calc, h_calc],
                mode='lines',
                line=dict(color='blue', width=1, dash='dash'),
                name='Pelo Libero'
            ))
            
            # Impostazioni asse per mantenere le proporzioni 1:1 (per non distorcere la pendenza visiva)
            fig_sez.update_layout(
                title="Sezione Trasversale del Fiume",
                xaxis_title="Larghezza (m)",
                yaxis_title="Altezza (m)",
                yaxis=dict(scaleanchor="x", scaleratio=1), # Fondamentale: Mantiene le proporzioni geometriche reali!
                template="plotly_white",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig_sez, use_container_width=True)
    # ==========================================
    # TAB 6: ESPORTA DATI
    # ==========================================
    with tab_export:
        if 'dati_finali_cpp' in locals() and len(dati_finali_cpp) > 0:
            df_parametri_cpp = pd.DataFrame(dati_finali_cpp)
            csv = df_parametri_cpp.to_csv(index=False, sep=';', decimal=',').encode('utf-8')
            st.download_button("Scarica Parametri CPP (CSV)", data=csv, file_name="Parametri_CPP.csv", mime="text/csv")
            formule_word = pd.DataFrame(formule_cpp_base())
            tabelle_word = [("Parametri CPP stimati", df_parametri_cpp)]
            if 'df_formule_sezione' in locals():
                tabelle_word.append(("Formule sezione trapezoidale", df_formule_sezione))
            if 'risultato_sezione' in locals():
                tabelle_word.append(("Risultati idraulici sezione", pd.DataFrame([
                    {"Parametro": "Tirante / battente", "Valore": f"{h_calc:.2f}", "Unita": "m", "Esito/nota": "-"},
                    {"Parametro": "Velocita media", "Valore": f"{Velocita:.2f}", "Unita": "m/s", "Esito/nota": "-"},
                    {"Parametro": "Area bagnata", "Valore": f"{Area_finale:.2f}", "Unita": "m2", "Esito/nota": "-"},
                ])))
            word_bytes = genera_relazione_word(
                "Relazione tecnica - Curva di possibilita pluviometrica",
                "Analisi statistica delle precipitazioni estreme e parametri CPP tabellati.",
                [
                    {"Parametro": "Stazioni selezionate", "Valore": ", ".join(stazioni_scelte), "Unita": "-", "Esito/nota": "-"},
                    {"Parametro": "Tempi di ritorno", "Valore": ", ".join(str(x) for x in tempi_ritorno), "Unita": "anni", "Esito/nota": "-"},
                    {"Parametro": "Modello statistico", "Valore": modello_scelto, "Unita": "-", "Esito/nota": "intervalli 95%" if mostra_ci else "-"},
                    {"Parametro": "Archivio dati", "Valore": NOME_FILE, "Unita": "-", "Esito/nota": CARTELLA},
                ],
                formule_word,
                tabelle_word,
                [
                    "La relazione usa gli stessi parametri stimati e mostrati nella schermata Streamlit.",
                    "Le curve e i grafici interattivi restano disponibili nella UI; il documento Word privilegia formulazione e tabelle verificabili.",
                ],
                figures=[
                    {"title": "Parametro CPP a per tempo di ritorno", "df": df_parametri_cpp, "x": "Tr", "y": "a", "kind": "line", "ylabel": "a [mm/h^n]"},
                    {"title": "Parametro CPP n per tempo di ritorno", "df": df_parametri_cpp, "x": "Tr", "y": "n", "kind": "line", "ylabel": "n [-]"},
                ],
            )
            st.download_button(
                "Scarica relazione Word",
                data=word_bytes,
                file_name="relazione_cpp_pluviometrica.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.info("Per esportare i grafici in alta qualitÃ  (PNG), usa l'icona della macchina fotografica in alto a destra su ogni grafico.")
