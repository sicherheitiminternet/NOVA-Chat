import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import vlc
import os
from mutagen import File
import json
from supabase import create_client

# =====================
# Supabase Setup
# =====================
SUPABASE_URL = "https://vaxelbftwysyecnwwbpq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZheGVsYmZ0d3lzeWVjbnd3YnBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY3NjI3NDgsImV4cCI6MjA4MjMzODc0OH0.cEE1dJ8I1bJ0m9cR3ezpVGILApQN_crxWpsrwe7hXi8"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OWNER_USERNAME = "Owner"
USER_JSON_FILE = "current_user.json"
FIRST_RUN_FILE = "first_run.json"



# =====================
# CustomTkinter Setup
# =====================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# =====================
# VLC Player
# =====================
player = vlc.MediaPlayer()

# =====================
# Lokale Mapping-Datei
# =====================
LOCAL_MAP_FILE = "local_paths.json"
if os.path.exists(LOCAL_MAP_FILE):
    with open(LOCAL_MAP_FILE, "r", encoding="utf-8") as f:
        local_path_map = json.load(f)
else:
    local_path_map = {}

def save_local_map():
    with open(LOCAL_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(local_path_map, f, ensure_ascii=False, indent=4)

# =====================
# Globale Variablen
# =====================
playlist = []
repeat_enabled = False
CURRENT_USER_ID = None  # wird automatisch aus JSON gesetzt

# =====================
# User-ID aus JSON laden
# =====================
USER_JSON = "current_user.json"
if os.path.exists(USER_JSON):
    with open(USER_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        CURRENT_USER_ID = data.get("user_id")
else:
    messagebox.showerror("Fehler", "Keine eingeloggten User gefunden! Bitte zuerst Login ausführen.")
    exit()

# =====================
# Songfunktionen
# =====================
def get_display_title(song_path, max_length=45):
    audio = File(song_path, easy=True)
    title = None
    if audio:
        title = audio.get("title", [None])[0]
    if not title:
        display = os.path.basename(song_path)
        for ext in [".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".alac", ".wma", ".aiff", ".ape", ".opus", ".mpc"]:
            if display.lower().endswith(ext):
                display = display[: -len(ext)]
                break
        title = display
    if len(title) > max_length:
        title = title[:max_length - 3] + "..."
    return title

def add_music():
    files = filedialog.askopenfilenames(
        title="Musik auswählen",
        filetypes=[("Audio Dateien", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.alac *.wma *.aiff *.ape *.opus *.mpc")]
    )
    for file in files:
        titel = get_display_title(file)
        if titel not in local_path_map:
            local_path_map[titel] = file
            save_local_map()
        if titel not in playlist:
            playlist.append(titel)
            song_list.insert("end", titel)
        # Supabase speichern (nur Titel + User-ID)
        supabase.table("songs").insert({
            "user_id": CURRENT_USER_ID,
            "titel": titel
        }).execute()

def play_selected_song(event=None):
    selection = song_list.curselection()
    if not selection:
        return
    titel = playlist[selection[0]]
    song_path = local_path_map.get(titel)
    if not song_path or not os.path.exists(song_path):
        messagebox.showerror("Fehler", "Die Musikdatei existiert lokal nicht mehr!")
        return
    media = vlc.Media(song_path)
    if repeat_enabled:
        media.add_option("input-repeat=-1")
    player.set_media(media)
    player.play()
    current_song.set(f"🎵 {titel}")

def play_music():
    if playlist:
        play_selected_song()

def pause_music():
    player.pause()

def stop_music():
    player.stop()
    current_song.set("Aktueller Song: -")

def set_volume(value):
    player.audio_set_volume(int(value))

def toggle_repeat():
    global repeat_enabled
    repeat_enabled = not repeat_enabled
    repeat_button.configure(
        text="🔁 Wiederholen: AN" if repeat_enabled else "🔁 Wiederholen: AUS"
    )
    try:
        selection = song_list.curselection()
        if selection:
            play_selected_song()
    except Exception as e:
        print(f"Fehler beim Neustarten des Songs: {e}")

def remove_selected_song():
    selection = song_list.curselection()
    if not selection:
        return
    index = selection[0]
    titel = playlist.pop(index)
    song_list.delete(index)
    # Lokal entfernen
    local_path_map.pop(titel, None)
    save_local_map()
    # Supabase löschen
    supabase.table("songs").delete().eq("user_id", CURRENT_USER_ID).eq("titel", titel).execute()
    # Player stoppen falls gerade gespielt
    if player.get_media() and player.get_media().get_mrl() == vlc.Media(local_path_map.get(titel, "")).get_mrl():
        stop_music()

def load_songs_from_db():
    playlist.clear()
    song_list.delete(0, "end")
    result = supabase.table("songs").select("titel").eq("user_id", CURRENT_USER_ID).execute()
    for row in result.data:
        titel = row["titel"]
        if titel in local_path_map:
            playlist.append(titel)
            song_list.insert("end", titel)

# =====================
# Hauptfenster
# =====================
root = ctk.CTk()
root.title("Musik Player")
root.geometry("600x550")
root.resizable(False, False)

current_song = ctk.StringVar(value="Aktueller Song: -")
label_current = ctk.CTkLabel(root, textvariable=current_song, font=("Arial", 16))
label_current.pack(pady=10)

info_texts = [
    "Musik Player",
    "Titel werden automatisch erkannt",
    "Playlist wird in DB gespeichert",
    "🔁 = Endlos-Wiederholung",
    "Doppelklick auf Song zum Abspielen"
]
info_index = 0
label_info = ctk.CTkLabel(root, text=info_texts[info_index], font=("Arial", 14, "bold"), text_color="cyan")
label_info.pack(pady=5)

def switch_info():
    global info_index
    info_index = (info_index + 1) % len(info_texts)
    label_info.configure(text=info_texts[info_index])
    root.after(4000, switch_info)

root.after(4000, switch_info)

song_list = tk.Listbox(root, height=15, bg="#1e1e1e", fg="white", selectbackground="#1f6aa5", activestyle="none")
song_list.pack(pady=10, fill="both", padx=20)
song_list.bind("<Double-Button-1>", play_selected_song)

frame_buttons = ctk.CTkFrame(root)
frame_buttons.pack(pady=10)

ctk.CTkButton(frame_buttons, text="🎵 Musik hinzufügen", command=add_music).grid(row=0, column=0, padx=5)
ctk.CTkButton(frame_buttons, text="❌ Entfernen", command=remove_selected_song).grid(row=0, column=1, padx=5)
ctk.CTkButton(frame_buttons, text="▶ Play", command=play_music).grid(row=0, column=2, padx=5)
ctk.CTkButton(frame_buttons, text="⏸ Pause", command=pause_music).grid(row=0, column=3, padx=5)
ctk.CTkButton(frame_buttons, text="⏹ Stop", command=stop_music).grid(row=0, column=4, padx=5)

repeat_button = ctk.CTkButton(frame_buttons, text="🔁 Wiederholen: AUS", command=toggle_repeat)
repeat_button.grid(row=1, column=0, columnspan=5, pady=8)

volume_slider = ctk.CTkSlider(root, from_=0, to=100, command=set_volume)
volume_slider.set(50)
volume_slider.pack(pady=10, fill="x", padx=20)


# =====================
# Footer
# =====================
footer = ctk.CTkLabel(root, text="© 2025 NOVA-Chat", font=("Segoe UI", 14, "bold"), text_color="white")
footer.pack(side="bottom", pady=5)


# =====================
# Songs beim Start laden
# =====================
load_songs_from_db()

# =====================
# Start
# =====================
root.mainloop()