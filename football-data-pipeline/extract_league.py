import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("RAPIDAPI_KEY")

url = "https://sportapi7.p.rapidapi.com/api/v1/category/1/unique-tournaments" 

headers = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

def extract_tournaments():
    print("Analyse de la structure SportAPI...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        all_tournaments = []
        
        # On descend dans la structure : groups -> uniqueTournaments
        groups = data.get('groups', [])
        for group in groups:
            # C'est ici qu'on ajoute la couche manquante !
            tournaments = group.get('uniqueTournaments', [])
            
            for t in tournaments:
                all_tournaments.append({
                    "id": t.get('id'),
                    "name": t.get('name'),
                    "slug": t.get('slug'),
                    "category_name": t.get('category', {}).get('name'),
                    "country_code": t.get('category', {}).get('alpha2'), # Ex: EN pour England
                    "sport": t.get('category', {}).get('sport', {}).get('name')
                })
        
        df = pd.DataFrame(all_tournaments)
        
        if not df.empty:
            print(f"Succès ! {len(df)} tournois trouvés.")
            print(df.head())
            df.to_csv("england_tournaments.csv", index=False)
            print("\nFichier 'england_tournaments.csv' créé.")
        else:
            print("Le tableau est encore vide, vérifie la clé 'uniqueTournaments'.")
    else:
        print(f"Erreur : {response.status_code}")

if __name__ == "__main__":
    extract_tournaments()