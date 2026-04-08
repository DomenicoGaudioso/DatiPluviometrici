import os
import requests
import time

# --- CONFIGURAZIONE FISSA ---
# Inseriamo la "r" prima delle virgolette per far leggere correttamente i backslash di Windows
DOWNLOAD_DIR = r"C:\Users\Domen\OneDrive\00_TOLS\GitHub\Idraulica\DatiPluviometrici"
BASE_URL = "https://www.arpae.it/it/temi-ambientali/meteo/report-meteo/annali-idrologici/"
START_YEAR = 1916
END_YEAR = 2024

def download_annali():
    # Crea la cartella se per caso non esiste già nel tuo OneDrive/GitHub
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    print(f"=== SCARICATORE ANNALI IDROLOGICI EMILIA-ROMAGNA ===")
    print(f"Inizio ricerca massiva annali dal {START_YEAR} al {END_YEAR}...")
    print(f"Cartella di destinazione impostata su: {DOWNLOAD_DIR}\n")
    
    for year in range(START_YEAR, END_YEAR + 1):
        # Elenco delle possibili varianti di nomenclatura utilizzate nel tempo
        possible_filenames = [
            f"annali-idrologici-{year}.zip",
            f"annali-idrologici-{year}.pdf",
            f"annale-idrologico-{year}.zip",
            f"annale-idrologico-{year}.pdf",
            f"annali-idrologici-{year}",
            f"annali_idrologici_{year}.zip",
            f"annali_idrologici_{year}.pdf",
            f"annale_idrologico_{year}.zip",
            f"annale_idrologico_{year}.pdf",
            f"annale_{year}_parte_prima.zip",
            f"annale_{year}_parte_prima.pdf",
            f"annale-{year}-parte-prima.zip",
            f"annale-{year}-parte-prima.pdf",
            f"annale_{year}_parte_prima-2.zip",
            f"annale_{year}_parte_1.zip",
            f"annale_{year}_parte_1.pdf",
            f"annale_{year}_parte1.zip",
            f"annale_{year}_parte1.pdf",
            f"annale-{year}.zip",
            f"annale-{year}.pdf",
            f"annale_{year}.zip",
            f"annale_{year}.pdf",
            f"{year}.zip",
            f"{year}.pdf"
        ]
        
        file_scaricato = False
        
        for filename in possible_filenames:
            url = f"{BASE_URL}{filename}"
            
            try:
                response = requests.get(url, stream=True, timeout=10)
                
                if response.status_code == 200 and 'text/html' not in response.headers.get('Content-Type', ''):
                    print(f"[{year}] TROVATO: {filename}")
                    
                    save_name = filename
                    if not filename.endswith(('.zip', '.pdf')):
                        content_type = response.headers.get('Content-Type', '')
                        if 'zip' in content_type or 'compressed' in content_type:
                            save_name += ".zip"
                        elif 'pdf' in content_type:
                            save_name += ".pdf"
                        else:
                            save_name += ".bin"
                            
                    # Unisce il tuo percorso fisso con il nome del file trovato
                    file_path = os.path.join(DOWNLOAD_DIR, save_name)
                    
                    with open(file_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=8192):
                            file.write(chunk)
                            
                    print(f"  └─> Salvato in: {file_path}")
                    file_scaricato = True
                    break 
                    
            except requests.RequestException:
                pass
        
        if not file_scaricato:
            print(f"[{year}] X NESSUN FILE TROVATO tra le varianti testate.")
            
        time.sleep(1.5)

if __name__ == "__main__":
    download_annali()
    print("\nScript completato con successo!")