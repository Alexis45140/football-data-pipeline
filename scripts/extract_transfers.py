import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

headers = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
    "x-rapidapi-host": "free-api-live-football-data.p.rapidapi.com"
}

def extract_top_transfers(total_pages=10):
    url = "https://free-api-live-football-data.p.rapidapi.com/football-get-all-transfers"
    all_transfers = []

    for page in range(1, total_pages + 1):
        print(f"📡 Récupération de la page {page}...")
        response = requests.get(url, headers=headers, params={"page": str(page)})

        if response.status_code == 200:
            data = response.json()
            transfers = data.get('response', {}).get('transfers', [])

            for t in transfers:
                fee_data = t.get('fee', {})
                fee_value = 0
                if isinstance(fee_data, dict):
                    fee_value = fee_data.get('value', 0)

                record = {
                    "joueur": t.get('name'),
                    "club_depart": t.get('fromClub'),
                    "club_arrivee": t.get('toClub'),
                    "montant": fee_value,
                    "date_transfert": t.get('transferDate'),
                    "type_transfert": t.get('transferType', {}).get('text', 'N/A')
                }
                all_transfers.append(record)
        else:
            print(f"❌ Erreur API : {response.status_code}")

    df = pd.DataFrame(all_transfers)

    if not df.empty:
        print("\n✅ Aperçu des données :")
        print(df[['joueur', 'club_depart', 'club_arrivee']].head())
        df.to_csv("seeds/transferts_football.csv", index=False, encoding='utf-8-sig')
        print(f"\nFichier sauvegardé : {len(df)} lignes.")
    else:
        print("⚠️ Aucune donnée récupérée.")

if __name__ == "__main__":
    extract_top_transfers(total_pages=10)