# 🌧️ Idro-Dashboard: Analisi Precipitazioni Estreme e CPP

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.20%2B-red)
![Plotly](https://img.shields.io/badge/Plotly-Interactive-brightgreen)
![SciPy](https://img.shields.io/badge/SciPy-Stats-lightgrey)

Una suite completa in Python per l'estrazione automatizzata dei dati dagli Annali Idrologici (ARPAE/Servizio Idrografico) e una **Dashboard Web Interattiva** per l'analisi statistica avanzata delle precipitazioni massime e la costruzione delle Curve di Possibilità Pluviometrica (CPP).

## 🚀 Caratteristiche Principali

Questo progetto si divide in due moduli fondamentali:

1. **Motore di Estrazione Dati (Data Engineering)**
   - Lettura automatica dei PDF degli Annali Idrologici.
   - Analisi testuale nativa per i PDF vettoriali (es. 2024).
   - *[Opzionale]* Motore OCR (Tesseract) per le scansioni storiche (es. 1916, 1923).
   - Raggruppamento e pulizia dei dati con esportazione in un `Master_Database_Pluviometrico.xlsx`.

2. **Dashboard Idrologica (Data Science & Web App)**
   - **Mappa Interattiva:** Localizzazione geografica delle stazioni pluviometriche.
   - **Calcolo CPP:** Interpolazione dei parametri $a$ e $n$ per vari Tempi di Ritorno (Tr).
   - **Modelli Statistici:** Scelta dinamica tra Distribuzione di Gumbel (EVI) e GEV (Generalized Extreme Value).
   - **Intervalli di Confidenza:** Visualizzazione rigorosa dell'incertezza statistica (Fasce al 95%).
   - **Trend Climatici:** Analisi grafica delle serie storiche per individuare l'aumento di intensità degli eventi estremi.
   - **Esportazione:** Download istantaneo dei parametri in `.csv` per l'uso in software di modellazione idraulica (HEC-RAS, SWMM).

---

## 📂 Struttura del Progetto

```text
Idraulica_DatiPluviometrici/
│
├── app.py                            # Applicazione web Streamlit (Dashboard)
├── elabora_annali.py                 # Script per l'estrazione dati dai PDF
├── unisci_excel.py                   # Script per unificare i file Excel annuali
│
├── EmiliaRomagna/                    # Cartella di archiviazione dati
│   └── Master_Database_Pluviometrico.xlsx  # Database unificato (Input della Dashboard)
│
└── README.md                         # Questo file
```

---

## 🛠️ Installazione e Prerequisiti

Assicurati di avere **Python 3.9 o superiore** installato sul tuo sistema. 

Apri il terminale e installa le librerie necessarie eseguendo questo comando:

```bash
pip install streamlit pandas numpy scipy plotly openpyxl pdfplumber
```

*(Nota: Se intendi utilizzare l'estrazione OCR per i PDF storici, sarà necessario installare anche Tesseract-OCR sul tuo sistema e le librerie `pytesseract` o `easyocr`).*

---

## 🖥️ Come usare la Dashboard

1. **Prepara i Dati:** Assicurati che il file `Master_Database_Pluviometrico.xlsx` sia posizionato all'interno della cartella `EmiliaRomagna/`.
2. **Avvia l'App:** Apri il terminale nella cartella principale del progetto e lancia il comando:
   ```bash
   streamlit run app.py
   ```
3. **Esplora:** Il browser si aprirà automaticamente (solitamente all'indirizzo `http://localhost:8501`). Usa la barra laterale per selezionare le stazioni, i Tempi di Ritorno e il modello statistico desiderato.

---

## 📚 Background Teorico

L'applicazione si basa sulle metodologie standard dell'ingegneria idrologica italiana:
- La stima dei valori estremi per una data durata $t$ avviene tramite il **Metodo dei Momenti** applicato alla distribuzione di **Gumbel**, calcolando la variabile ridotta $y_T$.
- L'equazione della curva di probabilità pluviometrica è definita dal monomio $h(t) = a \cdot t^n$.
- I parametri $a$ e $n$ vengono ricavati tramite **regressione lineare** applicata ai logaritmi delle durate (1h, 3h, 6h, 12h, 24h) e delle altezze di pioggia stimate.

---

## 👨‍💻 Autore e Licenza
Sviluppato per automatizzare e modernizzare l'approccio allo studio delle serie idrologiche storiche. 
Sentiti libero di clonare, modificare e integrare questo strumento nei tuoi flussi di lavoro ingegneristici!
