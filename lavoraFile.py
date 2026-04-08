import os
import re
import pandas as pd
import pdfplumber

# --- CONFIGURAZIONE FISSA ---
BASE_DIR = r"C:\Users\Domen\OneDrive\00_TOLS\GitHub\Idraulica\DatiPluviometrici\EmiliaRomagna"

def is_digital_pdf(pdf_path):
    """Verifica se il PDF è nativo digitale (testo selezionabile)."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Controlla le prime 3 pagine per capire se c'è testo reale
            for i in range(min(3, len(pdf.pages))):
                text = pdf.pages[i].extract_text()
                if text and len(text.strip()) > 50:
                    return True 
    except Exception:
        pass
    return False

def extract_text_native(pdf_path):
    """Estrae il testo dai PDF vettoriali."""
    testo_completo = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text:
                testo_completo += f"\n{text}"
    return testo_completo

def parse_dati_pluviometrici(testo, anno_riferimento):
    """Cerca le stazioni e i 5 valori di pioggia massima nel testo."""
    dati_estratti = []
    
    # Regex per trovare: Nome Stazione + 5 numeri (1h, 3h, 6h, 12h, 24h)
    pattern_flessibile = r"([A-Z][A-Za-z\s\']+?)\s+(\d{1,3}[,.]?\d*)\s+(\d{1,3}[,.]?\d*)\s+(\d{1,3}[,.]?\d*)\s+(\d{1,3}[,.]?\d*)\s+(\d{1,3}[,.]?\d*)"
    parole_da_ignorare = ['pagina', 'stazione', 'durata', 'ore', 'anno', 'precipitazioni', 'massime', 'totale']

    for match in re.finditer(pattern_flessibile, testo):
        stazione = match.group(1).strip()
        
        if len(stazione) > 2 and not any(parola in stazione.lower() for parola in parole_da_ignorare):
            try:
                v_1h = float(match.group(2).replace(',', '.'))
                v_3h = float(match.group(3).replace(',', '.'))
                v_6h = float(match.group(4).replace(',', '.'))
                v_12h = float(match.group(5).replace(',', '.'))
                v_24h = float(match.group(6).replace(',', '.'))
                
                dati_estratti.append({
                    "Anno": anno_riferimento,
                    "Stazione": stazione,
                    "1h_mm": v_1h,
                    "3h_mm": v_3h,
                    "6h_mm": v_6h,
                    "12h_mm": v_12h,
                    "24h_mm": v_24h
                })
            except ValueError:
                continue
                
    return dati_estratti

def main():
    print("=== MOTORE DI ESTRAZIONE ANNALI IDROLOGICI (SALVATAGGIO PER ANNO) ===")
    
    pdf_files = [f for f in os.listdir(BASE_DIR) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("Nessun file PDF trovato nella cartella specificata.")
        return

    # FASE 1: Raggruppiamo i nomi dei file per anno prima di aprirli
    file_per_anno = {}
    for filename in pdf_files:
        match_anno = re.search(r'(19|20)\d{2}', filename)
        anno = match_anno.group(0) if match_anno else "Anno_Ignoto"
        
        if anno not in file_per_anno:
            file_per_anno[anno] = []
        file_per_anno[anno].append(filename)

    print(f"\nTrovati {len(pdf_files)} file PDF suddivisi in {len(file_per_anno)} annate.\n")

    # FASE 2: Elaboriamo un anno alla volta e salviamo l'Excel immediatamente
    for anno, lista_files in file_per_anno.items():
        print(f"=== Elaborazione Anno: {anno} ({len(lista_files)} file) ===")
        dati_anno_corrente = []
        
        # Leggiamo tutti i PDF di questo specifico anno
        for filename in lista_files:
            pdf_path = os.path.join(BASE_DIR, filename)
            print(f"  -> Analisi di: {filename}")
            
            if is_digital_pdf(pdf_path):
                print("     [V] Vettoriale rilevato. Estrazione nativa istantanea...")
                testo = extract_text_native(pdf_path)
                dati_estratti = parse_dati_pluviometrici(testo, anno)
                print(f"         Trovate {len(dati_estratti)} letture valide.")
                dati_anno_corrente.extend(dati_estratti)
            else:
                print("     [X] Scansione rilevata. Salto il file come richiesto.")
        
        # FASE 3: Appena finiti i file di quest'anno, creiamo subito l'Excel
        if dati_anno_corrente:
            df = pd.DataFrame(dati_anno_corrente)
            
            # Rimuove righe duplicate
            df = df.drop_duplicates(subset=['Stazione'], keep='last')
            # Ordina in ordine alfabetico per città
            df = df.sort_values(by='Stazione')
            
            excel_path = os.path.join(BASE_DIR, f"Piogge_Massime_Raggruppate_{anno}.xlsx")
            df.to_excel(excel_path, index=False)
            print(f"  [OK] SALVATO SU DISCO: {excel_path} (Stazioni inserite: {len(df)})\n")
        else:
            print(f"  [!] Nessun dato estratto per l'anno {anno}.\n")

if __name__ == "__main__":
    main()
    print("Elaborazione totale completata!")