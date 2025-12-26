import vlc
import time
import os

# === Pfad zur Audiodatei anpassen ===
AUDIO_FILE = "song.mp3"

# Eingabevalidierung: Existiert die Datei?
if not os.path.isfile(AUDIO_FILE):
    print(f"Fehler: Datei '{AUDIO_FILE}' nicht gefunden.")
    exit(1)

try:
    # VLC-Instanz und Player erstellen
    instance = vlc.Instance()
    player = instance.media_player_new()

    # Media laden
    media = instance.media_new(AUDIO_FILE)
    player.set_media(media)

    # Wiedergabe starten
    player.play()
    print(f"Spiele '{AUDIO_FILE}' in Endlosschleife... (Strg+C zum Beenden)")

    # Endlosschleife: Wenn Song fertig, neu starten
    while True:
        state = player.get_state()
        if state == vlc.State.Ended:
            player.stop()
            player.play()
        time.sleep(0.1)  # CPU-Last gering halten

except KeyboardInterrupt:
    print("\nWiedergabe beendet.")
    player.stop()
except Exception as e:
    print(f"Fehler: {e}")
