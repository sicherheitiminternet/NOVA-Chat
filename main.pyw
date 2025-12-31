import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
from supabase import create_client
import bcrypt
import json
import sys
import os
import webbrowser  # für anklickbare Links
from tkinter import scrolledtext


# ----- Supabase Setup -----
SUPABASE_URL = "https://vaxelbftwysyecnwwbpq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZheGVsYmZ0d3lzeWVjbnd3YnBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY3NjI3NDgsImV4cCI6MjA4MjMzODc0OH0.cEE1dJ8I1bJ0m9cR3ezpVGILApQN_crxWpsrwe7hXi8"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OWNER_USERNAME = "Owner"
USER_JSON_FILE = "current_user.json"
FIRST_RUN_FILE = "first_run.json"

login_btn = None
reg_btn = None
del_btn = None

# ----- DB-Funktionen -----
def register_user(username, password):
    if username == OWNER_USERNAME:
        return False
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        supabase.table("users").insert({
            "username": username,
            "password": password_hash,
            "banned": False,
            "is_admin": False
        }).execute()
        return True
    except Exception:
        return False

def check_login(username, password):
    result = supabase.table("users").select("id, password, banned, ban_reason, ban_expiry").eq("username", username).execute()
    data = result.data
    if not data:
        return None, False, None, None

    user = data[0]
    db_password = user["password"]
    banned = user["banned"]
    reason = user.get("ban_reason")
    expiry = user.get("ban_expiry")
    user_id = user["id"]

    # Passwort korrekt?
    if not bcrypt.checkpw(password.encode(), db_password.encode()):
        return None, False, None, None

    # Prüfen, ob gebannt
    if banned:
        # expiry eventuell in datetime konvertieren
        from datetime import datetime
        if expiry is None:
            expiry_val = "permanent"
        else:
            try:
                expiry_dt = datetime.fromisoformat(expiry)
                if expiry_dt >= datetime.max.replace(year=9999):
                    expiry_val = "permanent"
                else:
                    expiry_val = expiry
            except:
                expiry_val = expiry
        return None, True, reason, expiry_val

    # Alles ok
    return user_id, False, None, None

def delete_user(username):
    supabase.table("users").delete().eq("username", username).execute()

def ban_user(username, duration=None, reason="Kein Grund angegeben."):
    from datetime import datetime, timedelta

    expiry = datetime.max if duration is None else datetime.now() + duration

    supabase.table("users").update({
        "banned": True,
        "ban_reason": reason,
        "ban_expiry": expiry.isoformat()  # wichtig: ISO-Format für Strings in DB
    }).eq("username", username).execute()

def unban_user(username):
    supabase.table("users").update({"banned": False}).eq("username", username).execute()

def reset_password(username, new_password):
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    supabase.table("users").update({"password": password_hash}).eq("username", username).execute()

def get_all_users():
    result = supabase.table("users").select("username, banned, is_admin").execute()
    return result.data

def is_admin(username):
    result = supabase.table("users").select("is_admin").eq("username", username).execute()
    data = result.data
    return data and data[0]["is_admin"]

# ----- Login/Register/Delete GUI -----
def show_login():
    global login_win, user_entry, pass_entry
    global login_btn, reg_btn, del_btn  # Buttons global für First-Run-Popup

    login_win = tk.Tk()
    login_win.title("Login")
    login_win.geometry("350x260")
    login_win.resizable(False, False)

    tk.Label(login_win, text="Benutzername:").pack(pady=(20, 5))
    user_entry = tk.Entry(login_win)
    user_entry.pack()

    tk.Label(login_win, text="Passwort:").pack(pady=(10, 5))
    pass_entry = tk.Entry(login_win, show="*")
    pass_entry.pack()

    btn_frame = tk.Frame(login_win)
    btn_frame.pack(pady=15)

    # --- Buttons erstellen ---
    login_btn = tk.Button(btn_frame, text="Anmelden", width=12, command=do_login)
    login_btn.grid(row=0, column=0, padx=5)
    reg_btn = tk.Button(btn_frame, text="Registrieren", width=12, command=show_register)
    reg_btn.grid(row=0, column=1, padx=5)
    del_btn = tk.Button(btn_frame, text="Account löschen", width=15, command=show_delete_account)
    del_btn.grid(row=1, column=0, columnspan=2, pady=10)

    # Buttons vorerst deaktivieren, bis First Run abgeschlossen
    login_btn.config(state="disabled")
    reg_btn.config(state="disabled")
    del_btn.config(state="disabled")

    add_footer(login_win)

    # Enter-Taste zum Login
    login_win.bind("<Return>", lambda event: do_login())

    # --- First Run Popup ---
    def show_first_run_popup():
        popup = tk.Toplevel(login_win)
        popup.title("Wichtige Information")
        popup.geometry("400x300")
        popup.resizable(False, False)
        popup.grab_set()  # blockiert Interaktion mit Login

        tk.Label(popup, text="Wenn du fortfährst, stimmst du unseren AGBs, der Datenschutzerklärung und den Chat-Regeln zu:",
                 wraplength=380, justify="left").pack(pady=10)

        def open_agb(): webbrowser.open("agb.html")
        def open_privacy(): webbrowser.open("datenschutz.html")
        def open_chat_rules(): webbrowser.open("chat_rules.html")  # neues File
        
        agb_link = tk.Label(popup, text="AGB", fg="blue", cursor="hand2")
        agb_link.pack()
        agb_link.bind("<Button-1>", lambda e: open_agb())

        privacy_link = tk.Label(popup, text="Datenschutzerklärung", fg="blue", cursor="hand2")
        privacy_link.pack()
        privacy_link.bind("<Button-1>", lambda e: open_privacy())
        
        chat_link = tk.Label(popup, text="Chat-Regeln", fg="blue", cursor="hand2")
        chat_link.pack()
        chat_link.bind("<Button-1>", lambda e: open_chat_rules())

        agree_var = tk.BooleanVar()
        tk.Checkbutton(popup, text="Ich stimme zu", variable=agree_var).pack(pady=10)


        def proceed():
            if not agree_var.get():
                messagebox.showerror("Fehler", "Du musst den Bedingungen zustimmen, um fortzufahren.")
                return
            with open(FIRST_RUN_FILE, "w", encoding="utf-8") as f:
                json.dump({"first_run_done": True}, f)
            popup.destroy()
            # Buttons freigeben
            login_btn.config(state="normal")
            reg_btn.config(state="normal")
            del_btn.config(state="normal")

        tk.Button(popup, text="Fortfahren", width=15, command=proceed).pack(pady=20)

    # First Run check
    if not os.path.exists(FIRST_RUN_FILE):
        show_first_run_popup()
    else:
        # Wenn schon First Run gemacht, Buttons direkt aktivieren
        login_btn.config(state="normal")
        reg_btn.config(state="normal")
        del_btn.config(state="normal")

    login_win.mainloop()

def do_login():
    username = user_entry.get().strip()
    password = pass_entry.get().strip()

    if not username or not password:
        messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
        return

    user_id, banned, reason, expiry = check_login(username, password)

    if banned:
        msg = "Du wurdest gebannt ❌"
        if reason:
            msg += f"\nGrund: {reason}"
        if expiry:
            # Prüfen, ob permanent
            if expiry == "permanent" or expiry == datetime.max.isoformat():
                msg += "\nBis: permanent"
            else:
                msg += f"\nBis: {expiry}"
        messagebox.showerror("Gebannt", msg)
        return

    if user_id:
        login_win.destroy()
        start_hub(username, user_id)
    else:
        messagebox.showerror("Fehler", "Benutzername oder Passwort ist falsch.")
        
def show_register():
    reg_win = tk.Toplevel()
    reg_win.title("Registrieren")
    reg_win.geometry("350x260")
    reg_win.resizable(False, False)

    tk.Label(reg_win, text="Benutzername:").pack(pady=(20, 5))
    reg_user_entry = tk.Entry(reg_win)
    reg_user_entry.pack()
    tk.Label(reg_win, text="Passwort:").pack(pady=(10, 5))
    reg_pass_entry = tk.Entry(reg_win, show="*")
    reg_pass_entry.pack()

    tk.Label(reg_win, text="Passwort bestätigen:").pack(pady=(10, 5))
    reg_pass_confirm_entry = tk.Entry(reg_win, show="*")
    reg_pass_confirm_entry.pack()

    def do_register_inner():
        u = reg_user_entry.get().strip()
        p = reg_pass_entry.get().strip()
        pc = reg_pass_confirm_entry.get().strip()
        if not u or not p:
            messagebox.showerror("Fehler", "Felder dürfen nicht leer sein.")
            return
        if p != pc:
            messagebox.showerror("Fehler", "Passwörter stimmen nicht überein.")
            return
        if register_user(u, p):
            messagebox.showinfo("Erfolg", "Account erstellt!")
            reg_win.destroy()
        else:
            messagebox.showerror("Fehler", "Benutzername existiert oder ist Owner.")

    tk.Button(reg_win, text="Registrieren", width=17, command=do_register_inner).pack(pady=15)
    add_footer(reg_win)

def show_delete_account():
    del_win = tk.Toplevel()
    del_win.title("Account löschen")
    del_win.geometry("350x260")
    del_win.resizable(False, False)

    tk.Label(del_win, text="Benutzername:").pack(pady=(20, 5))
    del_user_entry = tk.Entry(del_win)
    del_user_entry.pack()
    tk.Label(del_win, text="Passwort:").pack(pady=(10, 5))
    del_pass_entry = tk.Entry(del_win, show="*")
    del_pass_entry.pack()

    def do_delete_inner():
        u = del_user_entry.get().strip()
        p = del_pass_entry.get().strip()
        user_id, banned = check_login(u, p)
        if not user_id:
            messagebox.showerror("Fehler", "Benutzername oder Passwort ist falsch.")
            return
        delete_user(u)
        messagebox.showinfo("Erledigt", "Account wurde gelöscht.")
        del_win.destroy()

    tk.Button(del_win, text="Account löschen", width=17, command=do_delete_inner).pack(pady=15)
    add_footer(del_win)

# ----- Hub + Owner-Konsole -----
def start_hub(username, user_id):
    global hub_win
    hub_win = tk.Tk()
    hub_win.title(f"Hub - Willkommen {username}")
    is_owner = username == "Owner"
    hub_win.geometry("800x600" if is_owner else "600x400")
    hub_win.resizable(False, False)
    hub_win.grab_set()

    main_frame = tk.Frame(hub_win)
    main_frame.pack(fill="both", expand=True)

    tk.Label(main_frame, text=f"Hallo, {username}!\nWähle eine Option:", font=("Arial", 14)).pack(pady=20)

    # Combobox
    tk.Label(main_frame, text="Wähle ein Programm:", font=("Arial", 12)).pack(pady=(10, 5))
    combo = ttk.Combobox(main_frame, values=["Chat", "Musik Player"], state="readonly")  
    combo.pack(pady=5)
    combo.current(0)

    def launch_selected_program(username_param, user_id_param):
        choice = combo.get()
        if choice == "Chat":
            start_external_client(username_param)
            start_external_server()
        elif choice == "Musik Player":
            start_external_MusikPlayer(user_id_param)

    tk.Button(main_frame, text="Starten", width=20,
              command=lambda: launch_selected_program(username, user_id)).pack(pady=10)


    # Neuigkeiten-Button
    tk.Button(
        main_frame,
        text="Neuigkeiten",
        width=20,
        font=("Arial", 10, "bold"),
        bg="blue",
        fg="white",
        activebackground="blue",
        activeforeground="white",
        command=open_blank_window
    ).place(relx=1.0, y=20, anchor="ne", x=-10)
    
    
    
    tk.Button(
        main_frame,
        text="Feedback",
        width=20,
        font=("Arial", 10, "bold"),
        bg="green",
        fg="white",
        activebackground="green",
        activeforeground="white",
        command=lambda: start_external_feedback(username)  # Username vom Hub übergeben
    ).place(relx=1.0, y=60, anchor="ne", x=-10)



    if is_owner:
        console(main_frame)  # falls du die Owner-Konsole nutzen willst

    add_footer(hub_win)
    hub_win.mainloop()


def open_blank_window():
    news_win = tk.Toplevel(hub_win)
    news_win.title("Neuigkeiten")
    news_win.geometry("600x300")
    news_win.resizable(False, False)
    news_win.grab_set()

    tk.Label(news_win, text="Neuigkeiten", font=("Arial", 18, "bold")).pack(pady=(20, 5))
    tk.Frame(news_win, height=4, bd=0, bg="black").pack(fill="x", padx=20, pady=(0, 10))

    scroll_text = scrolledtext.ScrolledText(news_win, wrap=tk.WORD, font=("Arial", 12))
    scroll_text.pack(fill="both", expand=True, padx=10, pady=10)

    scroll_text.insert(tk.END, "- Neuer Hub.\n\n")
    scroll_text.insert(tk.END, "- Musik Player ist jetzt direkt im Hub zu finden.\n\n")
    scroll_text.insert(tk.END, "- Viele Neue Neuerungen wo sie selbst entdecken können.\n\n")
    for _ in range(10):
        scroll_text.insert(tk.END, "- Hier kann etwas angezeigt werden!\n\n")
    scroll_text.config(state=tk.DISABLED)


# ----- Funktionen zum Starten externer Skripte -----
def start_external_client(username):
    subprocess.Popen([sys.executable, "Client.pyw", username])

def start_external_server():
    subprocess.Popen([sys.executable, os.path.join(os.getcwd(), "Server.py")])

def start_external_MusikPlayer(user_id):
    subprocess.Popen([sys.executable, os.path.join(os.getcwd(), "Musik_Player.pyw"), str(user_id)])

def start_external_feedback(username):
    # Pfad zum externen Script (z. B. im gleichen Verzeichnis)
    script_path = os.path.join(os.getcwd(), "feedback.pyw")
    # Das Script mit dem aktuellen Python-Interpreter starten und Username als Argument übergeben
    subprocess.Popen([sys.executable, script_path, username])



# ----- Footer -----
def add_footer(window):
    tk.Label(
        window,
        text="© 2025 NOVA-Chat",
        font=("Segoe UI", 10, "bold"),
        fg="black"
    ).pack(side="bottom", fill="x")

def console(parent_frame):
    console_frame = tk.Frame(parent_frame, bg="#222222")
    console_frame.pack(side="bottom", fill="x", padx=10, pady=5)
    console_entry = tk.Entry(console_frame, font=("Consolas", 12), bg="#111111", fg="white", insertbackground="white")
    console_entry.pack(fill="x", expand=True, padx=5, pady=5)
    help_label = tk.Label(parent_frame, text="", fg="red", bg=parent_frame.cget("bg"), font=("Arial", 12, "bold"))
    help_label.pack(side="bottom", pady=(0, 5))

    def parse_duration_to_expiry(duration_parts):
        now = datetime.now()
        total_seconds = 0
        years = 0
        months = 0
        pattern = re.compile(r"(\d+)([smhdwMy])")
        for part in duration_parts:
            match = pattern.fullmatch(part)
            if not match:
                return None
            value, unit = match.groups()
            value = int(value)
            if unit == "s": total_seconds += value
            elif unit == "m": total_seconds += value*60
            elif unit == "h": total_seconds += value*3600
            elif unit == "d": total_seconds += value*86400
            elif unit == "w": total_seconds += value*7*86400
            elif unit == "M": months += value
            elif unit == "y": years += value

        try:
            year = now.year + years
            month = now.month + months
            while month > 12:
                year += 1
                month -= 12
            day = min(now.day, calendar.monthrange(year, month)[1])
            expiry_date = datetime(year, month, day, now.hour, now.minute, now.second)
            expiry_date += timedelta(seconds=total_seconds)
            return expiry_date
        except:
            return None

    def handle_console(event=None):
        cmd = console_entry.get().strip()
        help_label.config(text="", fg="red")

        # --- /ban ---
        if cmd.startswith("/ban"):
            parts = cmd.split()
            if "|" in cmd:
                args, reason = cmd.split("|",1)
                args = args.strip().split()[1:]
                reason = reason.strip()
            else:
                args = parts[1:]
                reason = "Kein Grund angegeben."
            name_parts = []
            duration_parts = []
            for part in args:
                if re.fullmatch(r"\d+[smhdwMy]", part):
                    duration_parts.append(part)
                else:
                    if duration_parts:
                        help_label.config(text="Dauer muss am Ende stehen.")
                        console_entry.delete(0, tk.END)
                        return
                    name_parts.append(part)
            name = " ".join(name_parts)
            if not name:
                help_label.config(text="Syntax: /ban Name [Dauer] [optional: Grund]")
                return
            expiry = parse_duration_to_expiry(duration_parts) if duration_parts else datetime.max
            if expiry is None:
                help_label.config(text="Ungültiges Zeitformat.")
                return
            try:
                supabase.table("users").update({
                    "banned": True,
                    "ban_reason": reason,
                    "ban_expiry": expiry.isoformat()
                }).eq("username", name).execute()
                help_label.config(text=f"{name} wurde {'permanent' if expiry==datetime.max else 'bis '+expiry.strftime('%Y-%m-%d %H:%M:%S')} gebannt. Grund: {reason}", fg="red")
            except Exception as e:
                help_label.config(text=f"Fehler: {e}")
            console_entry.delete(0, tk.END)

        # --- /unban ---
        elif cmd.startswith("/unban"):
            parts = cmd.split()
            name = " ".join(parts[1:])
            if not name:
                help_label.config(text="Syntax: /unban Name")
                console_entry.delete(0, tk.END)
                return
            try:
                supabase.table("users").update({
                    "banned": False,
                    "ban_reason": None,
                    "ban_expiry": None
                }).eq("username", name).execute()
                help_label.config(text=f"{name} wurde entbannt.", fg="green")
            except Exception as e:
                help_label.config(text=f"Fehler: {e}")
            console_entry.delete(0, tk.END)

        # --- /listbans ---
        elif cmd.startswith("/listbans"):
            result = supabase.table("users").select("username, ban_reason, ban_expiry").eq("banned", True).execute()
            data = result.data
            if not data:
                help_label.config(text="Keine gebannten Benutzer.", fg="red")
            else:
                lines = [f"{u['username']}: {u.get('ban_reason','Kein Grund')} ({u.get('ban_expiry','permanent')})" for u in data]
                help_label.config(text="\n".join(lines), fg="blue")
            console_entry.delete(0, tk.END)

        # --- /rename ---
        elif cmd.startswith("/rename"):
            parts = cmd.split()
            if len(parts) < 3:
                help_label.config(text="Syntax: /rename alterName neuerName")
                console_entry.delete(0, tk.END)
                return
            old_name = parts[1]
            new_name = " ".join(parts[2:])
            try:
                # Check if old_name exists
                result = supabase.table("users").select("*").eq("username", old_name).execute()
                if not result.data:
                    help_label.config(text=f"{old_name} existiert nicht.")
                else:
                    # Check if new_name exists
                    result2 = supabase.table("users").select("*").eq("username", new_name).execute()
                    if result2.data:
                        help_label.config(text=f"{new_name} existiert bereits.")
                    else:
                        supabase.table("users").update({"username": new_name}).eq("username", old_name).execute()
                        help_label.config(text=f"{old_name} wurde zu {new_name} umbenannt.", fg="green")
            except Exception as e:
                help_label.config(text=f"Fehler: {e}")
            console_entry.delete(0, tk.END)

        # --- /resetpassword ---
        elif cmd.startswith("/resetpassword"):
            parts = cmd.split()
            if len(parts) < 3:
                help_label.config(text="Syntax: /resetpassword benutzername neuesPasswort")
            else:
                username = parts[1]
                new_password = " ".join(parts[2:])

                try:
                    result = supabase.table("users").select("id").eq("username", username).execute()
                    if not result.data:
                        help_label.config(text=f"{username} existiert nicht.")
                    else:
                        password_hash = bcrypt.hashpw(
                            new_password.encode("utf-8"),
                            bcrypt.gensalt()
                        ).decode("utf-8")

                        supabase.table("users").update({
                            "password": password_hash
                        }).eq("username", username).execute()

                        help_label.config(
                            text=f"Passwort von {username} wurde sicher zurückgesetzt 🔐",
                            fg="green"
                        )
                except Exception as e:
                    help_label.config(text=f"Fehler: {e}")
        # --- /deleteuser ---
        elif cmd.startswith("/deleteuser"):
            parts = cmd.split()
            if len(parts) < 2:
                help_label.config(text="Syntax: /deleteuser benutzername")
                console_entry.delete(0, tk.END)
                return
            username_to_delete = parts[1]
            try:
                result = supabase.table("users").select("id").eq("username", username_to_delete).execute()
                if not result.data:
                    help_label.config(text=f"{username_to_delete} existiert nicht.")
                else:
                    supabase.table("users").delete().eq("username", username_to_delete).execute()
                    help_label.config(text=f"{username_to_delete} wurde gelöscht ✅", fg="green")
            except Exception as e:
                help_label.config(text=f"Fehler: {e}")
            console_entry.delete(0, tk.END)

        # --- /help ---
        elif cmd.startswith("/help"):
            commands = {
                "/ban": "Bannen eines Benutzers",
                "/unban": "Entbannen eines Benutzers",
                "/rename": "Benutzer umbenennen",
                "/resetpassword": "Passwort zurücksetzen",
                "/listbans": "Gebannte Benutzer anzeigen",
                "/deleteuser": "Benutzer Löschen", 
                "/help": "Hilfe anzeigen"
            }
            parts = cmd.split()
            if len(parts) == 1:
                help_label.config(text="Verfügbare Befehle:\n" + "\n".join(commands.keys()))
            else:
                help_label.config(text=commands.get(parts[1], "Unbekannter Befehl"))

        else:
            help_label.config(
                text="Unbekannter Befehl. /help für Hilfe"
            )
    
            # ✅ NUR EINMAL, GANZ AM ENDE
        console_entry.delete(0, tk.END)

    console_entry.bind("<Return>", handle_console)

    
# ----- Main -----
if __name__ == "__main__":
    show_login()
