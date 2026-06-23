import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

headers = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

# On tente le chemin direct pour cette statistique
# Structure : .../top-players/bigChancesCreated
url = "https://sportapi7.p.rapidapi.com/api/v1/unique-tournament/17/season/61627/top-players/bigChancesCreated"

def extract_playmakers():
    print("Extraction des créateurs d'occasions...")
    response = requests.get(url, headers=headers)
    
    print(f"Statut : {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        players = data.get('topPlayers', {}).get('bigChancesCreated', [])
        
        extracted_data = []
        for item in players:
            player = item.get('player', {})
            extracted_data.append({
                "name": player.get('name'),
                "nationality": player.get('country', {}).get('name'),
                "team": item.get('team', {}).get('name'),
                "big_chances_created": item.get('statistics', {}).get('bigChancesCreated'),
                "rating": item.get('rating')
            })
            
        df = pd.DataFrame(extracted_data)
        print(df.head())
        df.to_csv("pl_playmakers.csv", index=False)
        print("Fichier 'pl_playmakers.csv' créé !")
    else:
        print(f"Erreur : {response.text}")

if __name__ == "__main__":
    extract_playmakers()