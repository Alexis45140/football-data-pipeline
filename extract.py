import os
import requests
from dotenv import load_dotenv

load_dotenv()
headers = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
    "x-rapidapi-host": "sportapi7.p.rapidapi.com"
}

# L'URL qui a répondu 200
url = "https://sportapi7.p.rapidapi.com/api/v1/category/1/unique-tournaments" 

response = requests.get(url, headers=headers)
if response.status_code == 200:
    print("--- STRUCTURE DU JSON REÇU ---")
    # On affiche le début pour voir si c'est une liste [] ou un dictionnaire {}
    print(str(response.json())[:500]) 
else:
    print("Erreur de connexion.")