import tkinter as tk
from tkinter import messagebox
from tkinter import font
from tkinter import scrolledtext
from tkinter import ttk   # <-- DAS hinzufügen
import json
import subprocess
from datetime import datetime, timedelta
import re
import calendar
import os



# --- Pfade & Dateien ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_FILE = os.path.join(BASE_DIR, "users.json")
BAN_FILE = os.path.join(BASE_DIR, "banned.json")

root = tk.Tk()
root.withdraw()

# --- Datei-Handling ---
def ensure_files_exist():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w") as f:
            json.dump({}, f)
    if not os.path.exists(BAN_FILE):
        with open(BAN_FILE, "w") as f:
            json.dump([], f)

def load_users():
    ensure_files_exist()
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(USER_FILE, "w") as f:
            json.dump({}, f)  
        return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

def load_banned():
    ensure_files_exist()
    try:
        with open(BAN_FILE, "r") as f:
            data = json.load(f)
            banned = {}
            for entry in data:
                expiry = entry['expiry']
                reason = entry.get('reason', 'Kein Grund angegeben.')
                if isinstance(expiry, str):
                    try:
                        expiry = datetime.fromisoformat(expiry)
                    except Exception:
                        expiry = datetime.max
                banned[entry['username']] = {'expiry': expiry, 'reason': reason}
            return banned
    except json.JSONDecodeError:
        with open(BAN_FILE, "w") as f:
            json.dump([], f)
        return {}

def save_banned(banned):
    with open(BAN_FILE, "w") as f:
        data = [{
            'username': username,
            'expiry': info['expiry'].isoformat() if isinstance(info['expiry'], datetime) else info['expiry'],
            'reason': info.get('reason', 'Kein Grund angegeben.')
        } for username, info in banned.items()]
        json.dump(data, f)

users = load_users()
banned_users = load_banned()

# --- Login/Register/Delete User ---
def check_login(username, password):
    return username in users and users[username] == password


def register_user(username, password):
    if username in users or username in banned_users:
        return False
    users[username] = password
    save_users(users)
    return True


def delete_user(username):
    if username in users:
        users.pop(username)
        save_users(users)

# --- Schalter & Gründe ---
system_enabled = True
system_reason = "Wartungsarbeiten. \nBitte wende dich an den Owner."

login_enabled = True
login_reason = "Der Login ist im Moment deaktiviert.\nBitte wende dich an den Owner."

registration_enabled = True
register_reason = "Die Registrierung ist im Moment deaktiviert.\nBitte wende dich an den Owner"

delete_enabled = True
delete_reason = "Die Account-Löschung ist im Moment deaktiviert.\nBitte wende dich an den Owner."

# --- Prüffunktion ---
def check_allowed(action, username=None):
    """Prüft, ob eine Aktion erlaubt ist. Gibt (True, "") zurück, wenn erlaubt, sonst (False, Grund)."""
    if not system_enabled and username != "Owner":
        return False, system_reason
    if action == "login":
        if not login_enabled and username != "Owner":
            return False, login_reason
    elif action == "register":
        if not registration_enabled:
            return False, register_reason
    elif action == "delete":
        if not delete_enabled:
            return False, delete_reason
    return True, ""

# --- Login Fenster ---
def show_login():
    global login_win, user_entry, pass_entry

    login_win = tk.Toplevel(root)
    login_win.title("Login")
    login_win.geometry("350x260")
    login_win.resizable(False, False)
    login_win.grab_set()

    tk.Label(login_win, text="Benutzername:").pack(pady=(20, 5))
    user_entry = tk.Entry(login_win)
    user_entry.pack()

    tk.Label(login_win, text="Passwort:").pack(pady=(10, 5))
    pass_entry = tk.Entry(login_win)
    pass_entry.pack()

    def update_pass_visibility(event=None):
        if user_entry.get().strip() == "Owner":
            pass_entry.config(show="*")
        else:
            pass_entry.config(show="")

    user_entry.bind("<KeyRelease>", update_pass_visibility)

    btn_frame = tk.Frame(login_win)
    btn_frame.pack(pady=15)

    tk.Button(btn_frame, text="Anmelden", width=15, command=do_login).grid(row=0, column=0, padx=5)
    tk.Button(btn_frame, text="Registrieren", width=15, command=show_register).grid(row=0, column=1, padx=5)
    tk.Button(btn_frame, text="Account löschen", width=15, command=show_delete_account).grid(
        row=1, column=0, columnspan=2, pady=5
    )

    add_footer(login_win)
    login_win.bind("<Return>", do_login)

def do_login(event=None):
    global login_win
    username = user_entry.get().strip()
    password = pass_entry.get().strip()

    # Prüfen, ob Login erlaubt ist
    allowed, reason = check_allowed("login", username)
    if not allowed:
        messagebox.showerror("Login deaktiviert", reason)
        return


    if not username or not password:
        messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
        return

    # Gebannte Benutzer prüfen
    if username in banned_users:
        entry = banned_users[username]
        expiry = entry['expiry']
        reason = entry.get('reason', 'Kein Grund angegeben.')
        now = datetime.now()
        if isinstance(expiry, str):
            try:
                expiry = datetime.fromisoformat(expiry)
            except:
                expiry = datetime.max
        if now < expiry:
            msg = (
                f"Du wurdest permanent gebannt.\nGrund: {reason}"
                if expiry == datetime.max
                else f"Du bist bis {expiry.strftime('%Y-%m-%d %H:%M:%S')} gebannt.\nGrund: {reason}"
            )
            messagebox.showerror("Gebannt", msg)
            return
        else:
            banned_users.pop(username)
            save_banned(banned_users)

    if username not in users:
        messagebox.showerror("Fehler", "Benutzername existiert nicht.")
    elif users[username] != password:
        messagebox.showerror("Fehler", "Passwort ist falsch.")
    else:
        login_win.destroy()
        start_hub(username)


# --- Register Fenster ---
def show_register():
    global reg_win, reg_user_entry, reg_pass_entry, reg_pass_confirm_entry

    allowed, reason = check_allowed("register")
    if not allowed:
        messagebox.showerror("Registrierung deaktiviert", reason)
        return


    def do_register():
        u = reg_user_entry.get().strip()
        p = reg_pass_entry.get().strip()
        p_confirm = reg_pass_confirm_entry.get().strip()

        if not u:
            messagebox.showerror("Fehler", "Benutzername darf nicht leer sein.")
            return
    
        if not p:
            messagebox.showerror("Fehler", "Passwort darf nicht leer sein.")
            return
    
        if p != p_confirm:
            messagebox.showerror("Fehler", "Passwörter stimmen nicht überein.")
            return

        if u in banned_users:
            entry = banned_users[u]
            expiry = entry['expiry']
            reason = entry.get('reason', 'Kein Grund angegeben.')
            now = datetime.now()
            msg = (
                f"Du wurdest permanent gebannt.\nGrund: {reason}"
                if expiry == datetime.max
                else f"Du bist bis {expiry.strftime('%Y-%m-%d %H:%M:%S')} gebannt.\nGrund: {reason}"
            )
            messagebox.showerror("Gebannt", msg)
            return

        if u in users:
            messagebox.showerror("Fehler", "Benutzername existiert bereits.")
            return

        users[u] = p
        save_users(users)
        messagebox.showinfo("Erfolg", "Account erstellt! Du kannst dich jetzt anmelden.")
        reg_win.destroy()
        show_login()

    # --- Fenster Aufbau ---
    reg_win = tk.Toplevel()
    reg_win.title("Registrieren")
    reg_win.geometry("350x260")
    reg_win.resizable(False, False)
    reg_win.grab_set()

    tk.Label(reg_win, text="Benutzername:").pack(pady=(20, 5))
    reg_user_entry = tk.Entry(reg_win)
    reg_user_entry.pack()

    tk.Label(reg_win, text="Passwort:").pack(pady=(10, 5))
    reg_pass_entry = tk.Entry(reg_win)
    reg_pass_entry.pack()

    tk.Label(reg_win, text="Passwort bestätigen:").pack(pady=(10, 5))
    reg_pass_confirm_entry = tk.Entry(reg_win)
    reg_pass_confirm_entry.pack()

    def update_reg_pass_visibility(event=None):
        if reg_user_entry.get().strip() == "Owner":
            reg_pass_entry.config(show="*")
            reg_pass_confirm_entry.config(show="*")
        else:
            reg_pass_entry.config(show="")
            reg_pass_confirm_entry.config(show="")

    reg_user_entry.bind("<KeyRelease>", update_reg_pass_visibility)

    tk.Button(reg_win, text="Registrieren", width=17, command=do_register).pack(pady=15)
    add_footer(reg_win)

# --- Account Löschen Fenster ---
def show_delete_account():
    allowed, reason = check_allowed("delete")
    if not allowed:
        messagebox.showerror("Account löschen deaktiviert", reason)
        return


    # --- Fenster Aufbau ---
    del_win = tk.Toplevel()
    del_win.title("Account löschen")
    del_win.geometry("350x260")
    del_win.resizable(False, False)
    del_win.grab_set()

    tk.Label(del_win, text="Benutzername:").pack(pady=(20, 5))
    del_user_entry = tk.Entry(del_win)
    del_user_entry.pack()

    tk.Label(del_win, text="Passwort:").pack(pady=(10, 5))
    del_pass_entry = tk.Entry(del_win, show="*")
    del_pass_entry.pack()

    def do_delete():
        u = del_user_entry.get().strip()
        p = del_pass_entry.get().strip()

        if not u or not p:
            messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
            return

        # Zuerst prüfen, ob Benutzer gebannt ist
        if u in banned_users:
            entry = banned_users[u]
            expiry = entry['expiry']
            reason = entry.get('reason', 'Kein Grund angegeben.')
            msg = (
                f"Du wurdest permanent gebannt.\nGrund: {reason}"
                if expiry == datetime.max
                else f"Du bist bis {expiry.strftime('%Y-%m-%d %H:%M:%S')} gebannt.\nGrund: {reason}"
            )
            messagebox.showerror("Gebannt", f"Dieser Account kann nicht gelöscht werden.\n{msg}")
            return

        if u not in users:
            messagebox.showerror("Fehler", "Benutzername existiert nicht.")
            return

        if users[u] != p:
            messagebox.showerror("Fehler", "Passwort ist falsch.")
            return

        if messagebox.askyesno("Sicher?", "Willst du diesen Account wirklich löschen?"):
            delete_user(u)
            messagebox.showinfo("Erledigt", "Account wurde gelöscht.")
            del_win.destroy()

    # Sichtbarkeit der Passwörter abhängig vom Benutzernamen
    def update_del_pass_visibility(event=None):
        if del_user_entry.get().strip() == "Owner":
            del_pass_entry.config(show="*")
        else:
            del_pass_entry.config(show="")

    del_user_entry.bind("<KeyRelease>", update_del_pass_visibility)

    tk.Button(del_win, text="Account löschen", width=17, command=do_delete).pack(pady=15)
    add_footer(del_win)

# --- Hub Fenster ---
def start_hub(username):
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

    # Beispiel Combobox
    tk.Label(main_frame, text="Wähle ein Programm:", font=("Arial", 12)).pack(pady=(10, 5))
    combo = ttk.Combobox(main_frame, values=["Uhr", "Stopuhr", "Timer", "Planer", "Dateimanager", "Taschenrechner"])
    combo.pack(pady=5)
    combo.current(0)  # Standardmäßig erstes Element auswählen

    def launch_selected_program():
        choice = combo.get()
        if choice == "Uhr":
            start_external_clock()
        elif choice == "Stopuhr":
            start_external_Stopuhr()
        elif choice == "Timer":
            start_external_Timer()
        elif choice == "Planer":
            start_external_planer()
        elif choice == "Dateimanager":
            start_external_Dateimanager()
        elif choice == "Taschenrechner":
            start_external_taschenrechner()

    tk.Button(main_frame, text="Starten", width=20, command=launch_selected_program).pack(pady=10)

    # Der alte einzelne Button-Code kann entfernt werden, wenn du alles über die Combobox steuern willst

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

    if is_owner:
        console(main_frame)

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

    scroll_text.insert(tk.END, "- Der Dateimanager ist wieder verfügbar.\n\n")
    scroll_text.insert(tk.END, "- Es wurden zwei neue Programme hinzugefügt.\n")
    scroll_text.insert(tk.END, "- Ihr könnt sie über die neuen Buttons Stopuhr und Timer ansehen und benutzen.\n\n")
    scroll_text.insert(tk.END, "- Der Taschenrechner ist wieder verfügbar.\n\n")
    scroll_text.insert(tk.END, "")
    for _ in range(10):
        scroll_text.insert(tk.END, "- Hier kann etwas angezeigt werden!\n\n")
    scroll_text.config(state=tk.DISABLED)

def start_external_taschenrechner():
    subprocess.Popen(["pythonw", "Taschenrechner.pyw"])


def start_external_clock():
    subprocess.Popen(["pythonw", "Uhr.pyw"])


def start_external_Timer():
    subprocess.Popen(["pythonw", "Timer.pyw"])


def start_external_Stopuhr():
    subprocess.Popen(["pythonw", "Stopuhr.pyw"])


def start_external_planer():
    subprocess.Popen(["pythonw", "Planer.pyw"])


def start_external_Dateimanager():
    subprocess.Popen(["pythonw", "Dateimanager.pyw"])


def add_footer(window):
    tk.Label(
        window,
        text="© 2025 Robin Krieg",
        font=("Segoe UI", 10, "bold"),
        fg="black"
    ).pack(side="bottom", fill="x")


# --- Owner Konsole ---
def console(parent_frame):
    global users, banned_users
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
            if unit == "s":
                total_seconds += value
            elif unit == "m":
                total_seconds += value * 60
            elif unit == "h":
                total_seconds += value * 3600
            elif unit == "d":
                total_seconds += value * 86400
            elif unit == "w":
                total_seconds += value * 7 * 86400
            elif unit == "M":
                months += value
            elif unit == "y":
                years += value

        try:
            # Jahr und Monat addieren
            year = now.year + years
            month = now.month + months
            while month > 12:
                year += 1
                month -= 12

            # Tag anpassen, damit er im Zielmonat gültig ist
            day = min(now.day, calendar.monthrange(year, month)[1])

            expiry_date = datetime(year, month, day, now.hour, now.minute, now.second, now.microsecond)
            expiry_date += timedelta(seconds=total_seconds)
            return expiry_date
        except Exception:
            return None


    def handle_console(event=None):
        cmd = console_entry.get().strip()
        help_label.config(text="", fg="red")

        # --- /ban ---
        if cmd.startswith("/ban"):
            if "|" in cmd:
                parts = cmd.split("|", 1)
                args = parts[0].strip().split()[1:]
                reason = parts[1].strip()
            else:
                args = cmd.split()[1:]
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
                help_label.config(text="Syntax: /ban Name [Dauer...] [optional: Grund]")
                return
            if name in banned_users:
                help_label.config(text=f"{name} ist bereits gebannt.")
                return
            expiry = parse_duration_to_expiry(duration_parts) if duration_parts else datetime.max
            if expiry is None:
                help_label.config(text="Ungültiges Zeitformat.")
                return
            banned_users[name] = {"expiry": expiry, "reason": reason}
            save_banned(banned_users)
            help_label.config(text=f"{name} wurde {'permanent' if expiry==datetime.max else 'bis '+expiry.strftime('%Y-%m-%d %H:%M:%S')} gebannt. Grund: {reason}", fg="red")
            console_entry.delete(0, tk.END)

        # --- /unban ---
        elif cmd.startswith("/unban"):
            parts = cmd.split()
            name = " ".join(parts[1:])
            if not name:
                help_label.config(text="Syntax: /unban Name")
                console_entry.delete(0, tk.END)
                return
            if name not in banned_users:
                help_label.config(text=f"{name} ist nicht gebannt.")
            else:
                banned_users.pop(name)
                save_banned(banned_users)
                help_label.config(text=f"{name} wurde entbannt.", fg="green")
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
            if old_name not in users:
                help_label.config(text=f"{old_name} existiert nicht.")
            elif new_name in users:
                help_label.config(text=f"{new_name} existiert bereits.")
            else:
                users[new_name] = users.pop(old_name)
                save_users(users)
                help_label.config(text=f"{old_name} wurde zu {new_name} umbenannt.")
            console_entry.delete(0, tk.END)

        # --- /resetpassword ---
        elif cmd.startswith("/resetpassword"):
            parts = cmd.split()
            if len(parts) < 3:
                help_label.config(text="Syntax: /resetpassword benutzername neuesPasswort")
                console_entry.delete(0, tk.END)
                return
            username = parts[1]
            new_password = " ".join(parts[2:])
            if username not in users:
                help_label.config(text=f"{username} existiert nicht.")
            else:
                users[username] = new_password
                save_users(users)
                help_label.config(text=f"Passwort von {username} zurückgesetzt.", fg="green")
            console_entry.delete(0, tk.END)

        # --- /listbans ---
        elif cmd.startswith("/listbans"):
            if not banned_users:
                help_label.config(text="Keine gebannten Benutzer.", fg="red")
            else:
                help_label.config(text="Gebannte Benutzer:\n" + "\n".join(banned_users), fg="blue")
            console_entry.delete(0, tk.END)

        # --- /help ---
        elif cmd.startswith("/help"):
            commands = {
                "/ban": "Bannen eines Benutzers: /ban Name [Dauer...] [optional: Grund]",
                "/unban": "Entbannen eines Benutzers: /unban benutzername",
                "/rename": "Benutzer umbenennen: /rename alterName neuerName",
                "/resetpassword": "Passwort zurücksetzen: /resetpassword benutzername neuesPasswort",
                "/listbans": "Liste aller gebannten Benutzer: /listbans",
                "/help": "Zeigt alle Befehle: /help [befehl]"
            }
            parts = cmd.split()
            if len(parts) == 1:
                help_text = "Verfügbare Befehle:\n" + "\n".join(commands.keys())
            elif len(parts) == 2:
                help_text = commands.get(parts[1], f"Keine Beschreibung für {parts[1]}")
            help_label.config(text=help_text)
            console_entry.delete(0, tk.END)

        else:
            help_label.config(text="Unbekannter Befehl. Befehle: /ban, /unban, /rename, /resetpassword, /listbans, /help")
            console_entry.delete(0, tk.END)

    console_entry.bind("<Return>", handle_console)


if __name__ == "__main__":
    show_login()      # Toplevel wird erstellt
    root.mainloop()   # wichtig, damit die GUI läuft