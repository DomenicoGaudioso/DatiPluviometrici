import os
import pandas as pd
import glob

# Definisci la cartella dove hai i file
BASE_DIR = r"C:\Users\Domen\OneDrive\00_TOLS\GitHub\Idraulica\DatiPluviometrici\EmiliaRomagna"

print("Inizio la fusione dei file Excel...")

# Cerca tutti i file che iniziano per "Piogge_Massime_Raggruppate_"
pattern = os.path.join(BASE_DIR, "Piogge_Massime_Raggruppate_*.xlsx")
lista_file = glob.glob(pattern)

if not lista_file:
    print("Nessun file trovato da unire!")
else:
    # Legge tutti i file e li mette in una lista
    lista_dataframe = [pd.read_excel(file) for file in lista_file]
    
    # Li fonde tutti in un'unica super-tabella
    df_totale = pd.concat(lista_dataframe, ignore_index=True)
    
    # Ordina il file finale prima per Stazione e poi per Anno
    df_totale = df_totale.sort_values(by=['Stazione', 'Anno'])
    
    # Salva il Master Database
    percorso_salvataggio = os.path.join(BASE_DIR, "Master_Database_Pluviometrico.xlsx")
    df_totale.to_excel(percorso_salvataggio, index=False)
    
    print(f"Fusione completata! Creato file unico con {len(df_totale)} righe totali.")
    print(f"Salvato in: {percorso_salvataggio}")