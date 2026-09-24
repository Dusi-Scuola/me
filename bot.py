import os
import json
import requests
from ntscraper import Nitter

# ---- CONFIGURAZIONE ----
X_USERNAME = "nOt_lAbx"  # Inserisci l'account X da monitorare
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK") 

DB_FILE = "last_tweet.json"

def load_stored_posts():
    """Carica l'ultimo e il penultimo ID salvati."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                data = json.load(f)
                return data.get("last_id"), data.get("second_last_id")
            except:
                return None, None
    return None, None

def save_posts(last_id, second_last_id):
    """Salva la nuova coppia di ID nel file locale."""
    with open(DB_FILE, "w") as f:
        json.dump({"last_id": last_id, "second_last_id": second_last_id}, f)

def fetch_latest_tweet():
    """Recupera l'ultimo post senza API usando NTSraper."""
    try:
        scraper = Nitter()
        print(f"Controllo i post di @{X_USERNAME}...")
        tweets_data = scraper.get_tweets(X_USERNAME, mode='user', number=2)
        
        if tweets_data and tweets_data.get('tweets'):
            latest = tweets_data['tweets'][0]
            link = latest.get('link', '')
            if 'status/' in link:
                tweet_id = link.split('status/')[-1].split('#')[0]
                return tweet_id
    except Exception as e:
        print(f"Errore nello scraping di X: {e}")
    return None

def send_to_discord(text_content):
    """Invia un messaggio di testo generico a Discord."""
    if not DISCORD_WEBHOOK_URL:
        print("Errore: DISCORD_WEBHOOK non configurato nei segreti di GitHub.")
        return False
        
    payload = {"content": text_content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    
    # CORRETTO: Controlla se la risposta è 200 o 204 (successo dei Webhook)
    if response.status_code in:
        print("Messaggio inviato a Discord con successo.")
        return True
    else:
        print(f"Errore nell'invio a Discord: {response.status_code}")
        return False


def main():
    current_latest_id = fetch_latest_tweet()
    if not current_latest_id:
        print("Nessun post trovato o errore di connessione.")
        return

    # Carica la cronologia salvata
    stored_last_id, stored_second_last_id = load_stored_posts()
    print(f"Rilevato su X: {current_latest_id} | Salvati -> Ultimo: {stored_last_id}, Penultimo: {stored_second_last_id}")

    # Se non c'è nessuna cronologia precedente, inizializza il file e invia il post
    if stored_last_id is None:
        tweet_url = f"https://x.com{X_USERNAME}/status/{current_latest_id}"
        msg = f"📢 **Nuovo post da @{X_USERNAME}!**\n{tweet_url}"
        if send_to_discord(msg):
            save_posts(current_latest_id, None)
        return

    # Se l'ultimo post rilevato è diverso da quello memorizzato, c'è stato un cambiamento
    if current_latest_id != stored_last_id:
        
        # CASO 1: Il post rilevato è uguale al PENULTIMO salvato -> L'ultimo post è stato eliminato!
        if current_latest_id == stored_second_last_id:
            msg = f"🗑️ **L'ultimo post di @{X_USERNAME} (ID: `{stored_last_id}`) è stato eliminato.**"
            if send_to_discord(msg):
                # Il post più recente diventa quello che prima era penultimo, e il penultimo diventa vuoto (None)
                save_posts(stored_second_last_id, None)
                print("Rilevata eliminazione. Struttura dati aggiornata correttamente.")
                
        # CASO 2: È un post completamente nuovo (diverso sia dall'ultimo che dal penultimo)
        else:
            tweet_url = f"https://x.com{X_USERNAME}/status/{current_latest_id}"
            msg = f"📢 **Nuovo post da @{X_USERNAME}!**\n{tweet_url}"
            if send_to_discord(msg):
                # Quello che era l'ultimo diventa il penultimo, e il nuovo diventa l'ultimo
                save_posts(current_latest_id, stored_last_id)
                print("Nuovo post inviato e cronologia aggiornata.")
    else:
        print("Nessun cambiamento rilevato su X.")

if __name__ == "__main__":
    main()
