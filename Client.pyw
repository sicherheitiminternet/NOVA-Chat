import tkinter as tk
import socket
import threading
import sys
import psutil
import tkinter.font as tkfont
import subprocess  # für externes File starten
import customtkinter as ctk
from PIL import Image

ctk.set_appearance_mode("dark")   # "dark", "light" oder "system"
ctk.set_default_color_theme("dark-blue")  # modern blau

# Minecraft-Farb-Codes ohne Schwarz (&0)
COLOR_CODES = {
    "&1": "#0000AA",
    "&2": "#00AA00",
    "&3": "#00AAAA",
    "&4": "#AA0000",
    "&5": "#AA00AA",
    "&6": "#FFAA00",
    "&7": "#AAAAAA",
    "&8": "#555555",
    "&9": "#5555FF",
    "&a": "#55FF55",
    "&b": "#55FFFF",
    "&c": "#FF5555",
    "&d": "#FF55FF",
    "&e": "#FFFF55",
    "&f": "#FFFFFF",
}

STYLE_CODES = {
    "&l": "bold",
}


class ChatClient:
    def __init__(self, master, username):
        self.master = master
        self.username = username
        self.settings_window = None
        
        self.master.title(f"💬 Python Chat Client - {self.username}")
        self.master.attributes("-fullscreen", True)
        self.master.resizable(False, False)
        self.bg_color = "#000000"       # Hintergrund Frame
        self.entry_bg = "#1a1a1a"       # Hintergrund Chat/Textfeld
        self.text_color = "white"       # Standard-Textfarbe
        self.font = ("Segoe UI", 12)

        self.border_mode = "blue"   # "blue" oder "rgb"
        self.rgb_running = False
        self.rgb_hue = 0



        
        self.bold_font = tkfont.Font(family="Segoe UI", size=12, weight="bold")

        self.outer_frame = tk.Frame(master, bg="blue")
        self.outer_frame.pack(fill=tk.BOTH, expand=True)

        self.inner_frame = tk.Frame(self.outer_frame, bg=self.bg_color)
        self.inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.settings_icon = tk.PhotoImage(file="Settings-icon.png")

        self.settings_button = tk.Button(
            self.outer_frame,
            image=self.settings_icon,
            bg=self.bg_color,
            activebackground=self.bg_color,
            bd=0,
            cursor="hand2",
            command=self.open_settings_window
        )
        icon_height = self.settings_icon.height()
        self.settings_button.place(
            relx=0.98,
            y=icon_height // 2 + 5,
            anchor="n"
        )
        # Settings-Button beim Start anpassen
        self.settings_button.config(
            bg="#1a1a1a" if self.bg_color == "#000000" else "white",
            activebackground="#1a1a1a" if self.bg_color == "#000000" else "white"
        )

        # Bereich für angepinnte Nachricht
        self.pinned_frame = tk.Frame(self.inner_frame, bg="#1a1a1a", height=70)
        self.pinned_frame.pack(fill=tk.X, pady=(0, 5))
        self.pinned_frame.pack_propagate(False)
        self.pinned_message = tk.Label(
            self.pinned_frame,
            text="Keine angepinnten Nachrichten",
            font=("Segoe UI", 12, "bold"),
            fg="red",
            bg="#1a1a1a",
            anchor="center",
            justify="center",
            wraplength=800
        )
        self.pinned_message.pack(fill=tk.BOTH, expand=True)

        # Chatbereich
        self.chat_area = tk.Text(
            self.inner_frame,
            bg=self.entry_bg,
            fg=self.text_color,
            font=self.font,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tags für Farben
        self.chat_area.tag_config("bold", font=self.bold_font)
        self.chat_area.tag_config("namecolor", foreground="#1100FD")
        self.chat_area.tag_config("default", foreground=self.text_color)
        for code, color in COLOR_CODES.items():
            self.chat_area.tag_config(color, foreground=color)

        # Kontextmenü
        self.chat_area.bind("<Button-3>", self.show_context_menu)
        self.context_menu = tk.Menu(self.master, tearoff=0)
        self.context_menu.add_command(label="Nachricht anpinnen", command=self.pin_selected_message)
        self.context_menu.add_command(label="Angepinnt entfernen", command=self.unpin_message)
        self.context_menu.add_command(label="Nachricht löschen", command=self.delete_selected_message)
        
        # Eingabefeld & Buttons
        self.input_frame = tk.Frame(self.inner_frame, bg=self.bg_color)
        self.input_frame.pack(fill=tk.X, padx=5, pady=(0, 10))

        self.msg_entry = tk.Entry(
            self.input_frame,
            font=self.font,
            bg=self.entry_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief=tk.FLAT
        )
        self.msg_entry.pack(side=tk.LEFT, padx=(0, 10), pady=5, ipady=6, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", self.send_message)

        self.send_button = tk.Label(
            self.input_frame,
            text="Senden",
            font=self.font,
            bg="blue",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2"
        )
        self.send_button.pack(side=tk.LEFT, padx=(0, 10))
        self.send_button.bind("<Button-1>", self.send_message)

        self.close_button = tk.Label(
            self.input_frame,
            text="Schließen",
            font=self.font,
            bg="blue",
            fg="white",
            padx=15,
            pady=5,
            cursor="hand2"
        )
        self.close_button.pack(side=tk.LEFT)
        self.close_button.bind("<Button-1>", self.close_app)

        # Socket-Verbindung
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect(('127.0.0.1', 12345))
            self.client_socket.send(self.username.encode('utf-8'))
        except Exception as e:
            self._append_message(f"❌ Verbindung fehlgeschlagen: {e}", "white")
            return

        threading.Thread(target=self.receive_messages, daemon=True).start()
        self.last_sender = None

        self.copyright_label = tk.Label(
            self.inner_frame,
            text="© 2025 NOVA-Chat",
            font=("Segoe UI", 12, "bold"),
            bg=self.bg_color,
            fg=self.text_color
        )
        self.copyright_label.pack(side="bottom", pady=5)

    def toggle_chat_color(self):
        if self.bg_color == "#000000":  # Schwarz → Weiß
            self.bg_color = "#FFFFFF"
            self.entry_bg = "#EEEEEE"
            self.text_color = "black"
            btn_bg = "#DDDDDD"
            btn_fg = "black"
        else:  # Weiß → Schwarz
            self.bg_color = "#000000"
            self.entry_bg = "#1a1a1a"
            self.text_color = "white"
            btn_bg = "#555555"
            btn_fg = "white"

        # Frames und Textbox
        self.inner_frame.config(bg=self.bg_color)
        self.input_frame.config(bg=self.bg_color)
        self.chat_area.config(bg=self.entry_bg, fg=self.text_color)
        self.msg_entry.config(bg=self.entry_bg, fg=self.text_color, insertbackground=self.text_color)
        self.pinned_frame.config(bg=self.entry_bg)
        self.pinned_message.config(bg=self.entry_bg, fg="red")  # rot bleibt
        
        #Footer
        self.copyright_label.config(bg=self.bg_color, fg=self.text_color)


        # Settings-Button anpassen
        if self.bg_color == "#000000":  # Dark Mode
            self.settings_button.config(
            bg="#1a1a1a",
            activebackground="#1a1a1a"
        )
        else:  # Light Mode
            self.settings_button.config(
                bg="#EEEEEE",
                activebackground="white"
            )



        # Text-Tags
        self.chat_area.tag_config("default", foreground=self.text_color)

    def open_settings_window(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus_force()
            return

        # Neues Fenster erstellen
        self.settings_window = ctk.CTkToplevel(self.master)
        self.settings_window.title("Einstellungen")
        self.settings_window.geometry("320x300")
        self.settings_window.resizable(False, False)
        self.settings_window.transient(self.master)
        self.settings_window.focus_force()

        # Icon für Titel
        settings_pil = Image.open("Settings-icon.png")
        settings_icon = ctk.CTkImage(light_image=settings_pil, dark_image=settings_pil, size=(32, 32))

        title = ctk.CTkLabel(
            self.settings_window,
            text="Einstellungen",
            image=settings_icon,
            compound="left",
            font=ctk.CTkFont(size=18, weight="bold"),
            padx=10
        )
        title.pack(pady=(20, 15))

        # Dark/Light Button
        light_pil = Image.open("Color-icon.png")
        self.light_icon = ctk.CTkImage(light_image=light_pil, dark_image=light_pil, size=(32, 32))
        self.light_button = ctk.CTkButton(
            self.settings_window,
            text="Farbe wechseln",
            command=self.toggle_chat_color,
            image=self.light_icon,
            compound="left",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=220,
            height=40,
            corner_radius=10
        )
        self.light_button.pack(pady=8, padx=10)

        # Rahmen-Button
        border_pil = Image.open("Border-icon.png")
        self.border_icon = ctk.CTkImage(light_image=border_pil, dark_image=border_pil, size=(32, 32))
        self.border_button = ctk.CTkButton(
            self.settings_window,
            text="Rahmen: Blau / RGB",
            command=self.toggle_border_mode,
            image=self.border_icon,
            compound="left",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=220,
            height=40,
            corner_radius=10
        )
        self.border_button.pack(pady=8, padx=10)

        # Schließen-Event
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)

            
    def toggle_border_mode(self):
        if self.border_mode == "blue":
            self.border_mode = "rgb"
            self.rgb_running = True
            self.animate_rgb_border()
        else:
            self.border_mode = "blue"
            self.rgb_running = False
            self.outer_frame.config(bg="blue")


            
    def animate_rgb_border(self):
        if not self.rgb_running:
            return

        # HSV → RGB (smooth)
        self.rgb_hue = (self.rgb_hue + 1) % 360
        r, g, b = self.hsv_to_rgb(self.rgb_hue / 360, 1, 1)
        color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

        self.outer_frame.config(bg=color)
        self.master.after(20, self.animate_rgb_border)
    def hsv_to_rgb(self, h, s, v):
        import colorsys
        return colorsys.hsv_to_rgb(h, s, v)

    def delete_selected_message(self):
        if hasattr(self, "selected_line") and self.selected_line:
            try:
                # Prüfen, ob Owner oder eigene Nachricht
                if self.username.lower() == "owner" or self.selected_line.startswith(f"{self.username}:"):
                    self.client_socket.send(f"DELETE|{self.selected_line}".encode("utf-8"))
                else:
                    self._append_message("❌ Du kannst nur deine eigenen Nachrichten löschen.", "white")
            except Exception as e:
                self._append_message(f"❌ Fehler beim Löschen: {e}", "white")

    def _remove_message(self, message):
        # Finde genau die Zeile im Text-Widget
        index = self.chat_area.search(message, "1.0", tk.END)
        if index:
            line_start = f"{index.split('.')[0]}.0"
            line_end = f"{index.split('.')[0]}.end+1c"
            self.chat_area.config(state=tk.NORMAL)
            self.chat_area.delete(line_start, line_end)
            self.chat_area.config(state=tk.DISABLED)

    # Restlicher Code unverändert...
    def change_bg(self, color):
        self.bg_color = color
        self.inner_frame.config(bg=color)
        self.input_frame.config(bg=color)
        self.entry_bg = "#FFFFFF" if color.lower() == "#ffffff" else "#1a1a1a"
        self.chat_area.config(bg=self.entry_bg)

    def get_text_color(self):
        return "black" if self.entry_bg.lower() == "#ffffff" else "white"

    def show_context_menu(self, event):
        try:
            index = self.chat_area.index(f"@{event.x},{event.y}")
            self.chat_area.tag_remove(tk.SEL, "1.0", tk.END)
            line_start = f"{index.split('.')[0]}.0"
            line_end = f"{index.split('.')[0]}.end"
            self.chat_area.tag_add(tk.SEL, line_start, line_end)
            self.selected_line = self.chat_area.get(line_start, line_end).strip()
            self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Fehler Kontextmenü: {e}")

    def pin_selected_message(self):
        if hasattr(self, "selected_line") and self.selected_line:
            try:
                if ":" not in self.selected_line and self.selected_line.lower().startswith("owner "):
                    self.selected_line = self.selected_line.replace("Owner ", "Owner: ", 1)
                self.client_socket.send(f"PIN|{self.selected_line}".encode("utf-8"))
            except Exception as e:
                self._append_message(f"❌ Fehler beim Anpinnen: {e}", "white")

    def unpin_message(self):
        try:
            self.client_socket.send("PIN|".encode("utf-8"))
        except Exception as e:
            self._append_message(f"❌ Fehler beim Entpinnen: {e}", "white")

    def insert_owner_bold_blue(self, text):
        start = 0
        search_name = "Owner"
        while True:
            idx = text.lower().find(search_name.lower(), start)
            if idx == -1:
                self.chat_area.insert(tk.END, text[start:] + "\n", (self.get_text_color(),))
                break
            if idx > start:
                self.chat_area.insert(tk.END, text[start:idx])
            self.chat_area.insert(tk.END, text[idx:idx + len(search_name)], ("namecolor", "bold"))
            start = idx + len(search_name)

    def _append_message(self, message, name_color="white"):
        self.chat_area.config(state=tk.NORMAL)
        default_color = self.get_text_color()

        def parse_colors(text):
            pos = 0
            active_tags = [default_color]
            while pos < len(text):
                found = False
                if text[pos:pos + 2] == "&l":
                    if "bold" not in active_tags:
                        active_tags.append("bold")
                    pos += 2
                    found = True
                else:
                    for code, color in COLOR_CODES.items():
                        if text[pos:pos + 2] == code:
                            active_tags = [t for t in active_tags if t not in COLOR_CODES.values()]
                            active_tags.append(color)
                            pos += 2
                            found = True
                            break
                if not found:
                    self.chat_area.insert(tk.END, text[pos], tuple(active_tags))
                    pos += 1

        if ":" in message:
            name, text = message.split(":", 1)
            if name != self.last_sender:
                self.chat_area.insert(tk.END, "\n")
            if name.lower() == "owner":
                self.chat_area.insert(tk.END, f"{name}:", ("namecolor", "bold"))
                parse_colors(text)
                self.chat_area.insert(tk.END, "\n")
            else:
                self.chat_area.insert(tk.END, f"{name}:", (default_color,))
                self.chat_area.insert(tk.END, f"{text}\n", (default_color,))
            self.last_sender = name
        else:
            self.insert_owner_bold_blue(message)

        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def receive_messages(self):
        while True:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if msg:
                    # 1️⃣ Prüfen, ob Nachricht gelöscht werden soll
                    if msg.startswith("DELETE|"):
                        msg_to_delete = msg.split("|", 1)[1]
                        self._remove_message(msg_to_delete)
                        continue  # weiter zur nächsten Nachricht

                    # 2️⃣ Prüfen, ob Nachricht angepinnt wird
                    if msg.startswith("PIN|"):
                        pinned_text = msg.split("|", 1)[1]
                        self.pinned_message.config(text=pinned_text)
                    else:
                        # 3️⃣ Normale Nachricht verarbeiten
                        if "|" in msg:
                            color, text = msg.split("|", 1)
                        else:
                            color, text = "white", msg
                        self._append_message(text, name_color=color)
            except:
                break
    def send_message(self, event=None):
        msg = self.msg_entry.get()
        if msg.strip() != "":
            try:
                if self.username.lower() == "owner":
                    full_msg = f"{self.username}: {msg}"
                else:
                    for code in COLOR_CODES.keys():
                        msg = msg.replace(code, "")
                    full_msg = f"{self.username}: {msg}"
                self.client_socket.send(full_msg.encode('utf-8'))
                self.msg_entry.delete(0, tk.END)
            except:
                self._append_message("❌ Fehler beim Senden", "white")

    def close_app(self, event=None):
        # Liste der Skriptnamen, die beendet werden sollen
        targets = ["Server.py", "Musik Player.pyw"]

        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmd = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ""
                    for target in targets:
                        if target in cmd:
                            proc.terminate()
                            proc.wait(timeout=5)
                            print(f"{target} (PID {proc.pid}) beendet.")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"Fehler beim Beenden der Prozesse: {e}")

        # Socket schließen
        try:
            self.client_socket.close()
        except:
            pass

        # GUI schließen
        self.master.destroy()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Kein Benutzername übergeben.")
        sys.exit(1)

    username = sys.argv[1]
    root = tk.Tk()
    app = ChatClient(root, username)
    root.mainloop()
