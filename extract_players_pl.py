import os
import requests
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()
headers = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

def extract_full_league():
    # 1. On récupère les IDs des équipes
    teams_url = "https://sportapi7.p.rapidapi.com/api/v1/unique-tournament/17/season/61627/teams"
    response = requests.get(teams_url, headers=headers)
    
    if response.status_code != 200:
        print("Erreur lors de la récupération des équipes.")
        return

    teams = response.json().get('teams', [])
    all_players = []

    print(f"Début de l'extraction pour {len(teams)} équipes...")

    # 2. Boucle sur chaque équipe
    for team in teams:
        t_id = team.get('id')
        t_name = team.get('name')
        print(f"Extraction : {t_name} (ID: {t_id})...")
        
        players_url = f"https://sportapi7.p.rapidapi.com/api/v1/team/{t_id}/players"
        p_response = requests.get(players_url, headers=headers)
        
        if p_response.status_code == 200:
            players_data = p_response.json().get('players', [])
            for item in players_data:
                player = item.get('player', {})
                all_players.append({
                    "player_id": player.get('id'),
                    "team_name": t_name,
                    "player_name": player.get('name'),
                    "nationality": player.get('country', {}).get('name'),
                    "position": player.get('position'),
                    "age": player.get('age') # Optionnel : pour ton analyse
                })
        
        # Petite pause pour respecter les limites de l'API (Rate Limiting)
        time.sleep(0.5)

    # 3. Création du dataset final
    df = pd.DataFrame(all_players)
    df.to_csv("premier_league_players_2026.csv", index=False)
    
    print("-" * 30)
    print(f"TERMINÉ ! Fichier créé avec {len(df)} joueurs.")
    print(f"Nombre de nationalités différentes : {df['nationality'].nunique()}")

if __name__ == "__main__":
    extract_full_league()