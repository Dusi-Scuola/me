import os
import json
import asyncio
import requests
from twscrape import API, gather

# ---- CONFIGURAZIONE ----
X_USERNAME = "nOt_lAbx"  # Inserisci l'account X da monitorare
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK") 

# Credenziali dell'account "finto/burner" di X necessarie per twscrape
TW_USER = os.environ.get("TW_USERNAME")
TW_PASS = os.environ.get("TW_PASSWORD")
TW_EMAIL = os.environ.get("TW_EMAIL")
TW_EMAIL_PASS = os.environ.get("TW_EMAIL_PASSWORD") # Opzionale, metti una stringa vuota se non serve

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

async def fetch_latest_tweet():
    """Recupera l'ultimo post usando twscrape loggando l'account finto."""
    api = API()
    
    # Inizializza automaticamente l'account se non ancora configurato nel database locale di twscrape
    if TW_USER and TW_PASS and TW_EMAIL:
        await api.pool.add_account(TW_USER, TW_PASS, TW_EMAIL, TW_EMAIL_PASS or "")
        await api.pool.login_all()
    else:
        print("Attenzione: Credenziali TW_USERNAME, TW_PASSWORD o TW_EMAIL mancanti.")
        
    try:
        print(f"Controllo i post di @{X_USERNAME} con twscrape...")
        
        # Recupera l'ID numerico dell'utente da monitorare
        user_info = await api.user_by_username(X_USERNAME)
        if not user_info:
            print(f"Impossibile trovare l'utente @{X_USERNAME}")
            return None
            
        # Recupera gli ultimi 2 tweet (inclusi i retweet/risposte)
        tweets_data = await gather(api.user_tweets_and_replies(user_info.id, limit=2))
        
        if tweets_data:
            # Prende il tweet più recente
            latest_tweet = tweets_data[0]
            return str(latest_tweet.id)
            
    except Exception as e:
        print(f"Errore nello scraping di X con twscrape: {e}")
    return None

def send_to_discord(text_content):
    """Invia un messaggio di testo generico a Discord via Webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("Errore: DISCORD_WEBHOOK non configurato nei segreti di GitHub.")
        return False
        
    payload = {"content": text_content}
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    
    if response.status_code in:
        print("Messaggio inviato a Discord con successo.")
        return True
    else:
        print(f"Errore nell'invio a Discord: {response.status_code}")
        return False

async def main():
    current_latest_id = await fetch_latest_tweet()
    if not current_latest_id:
        print("Nessun post trovato o errore di connessione.")
        return

    # Carica la cronologia salvata
    stored_last_id, stored_second_last_id = load_stored_posts()
    print(f"Rilevato su X: {current_latest_id} | Salvati -> Ultimo: {stored_last_id}, Penultimo: {stored_second_last_id}")

    # Se non c'è nessuna cronologia precedente, inizializza il file e invia il post
    if stored_last_id is None:
        tweet_url = f"https://x.com/{X_USERNAME}/status/{current_latest_id}"
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
                save_posts(stored_second_last_id, None)
                print("Rilevata eliminazione. Struttura dati aggiornata correttamente.")
                
        # CASO 2: È un post completamente nuovo
        else:
            tweet_url = f"https://x.com/{X_USERNAME}/status/{current_latest_id}"
            msg = f"📢 **Nuovo post da @{X_USERNAME}!**\n{tweet_url}"
            if send_to_discord(msg):
                save_posts(current_latest_id, stored_last_id)
                print("Nuovo post inviato e cronologia aggiornata.")
    else:
        print("Nessun cambiamento rilevato su X.")

if __name__ == "__main__":
    # Avvia il loop asincrono richiesto da twscrape
    asyncio.run(main())
