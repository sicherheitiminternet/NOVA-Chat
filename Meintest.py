import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext
import os
import subprocess
import sqlite3
from datetime import datetime

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

# --- Datenbank & Funktionen ---
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(BASE_DIR, "users.db")
    ADMIN_USERNAME = "Owner"

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Benutzername TEXT UNIQUE,
        Passwort TEXT,
        Gebannt TEXT DEFAULT 'Nein'
    )
    """)
    conn.commit()

    banned_users = {}  # Temporär in-memory, kann man mit DB erweitern
    users = {}

    def load_users():
        cursor.execute("SELECT Benutzername, Passwort, Gebannt FROM users")
        for user, pw, gebannt in cursor.fetchall():
            users[user] = pw
            if gebannt == "Ja":
                banned_users[user] = {"expiry": datetime.max, "reason": "Automatisches Bann"}

    load_users()

    def save_users(users_dict):
        # In DB schreiben (nur Passwort, Benutzer existiert bereits)
        for user, pw in users_dict.items():
            cursor.execute("INSERT OR IGNORE INTO users (Benutzername, Passwort) VALUES (?, ?)", (user, pw))
            cursor.execute("UPDATE users SET Passwort=? WHERE Benutzername=?", (pw, user))
        conn.commit()

    def delete_user(username):
        cursor.execute("DELETE FROM users WHERE Benutzername=?", (username,))
        conn.commit()
        return cursor.rowcount > 0

    def ban_user(username):
        cursor.execute("UPDATE users SET Gebannt='Ja' WHERE Benutzername=?", (username,))
        conn.commit()
        banned_users[username] = {"expiry": datetime.max, "reason": "Automatisches Bann"}

    def unban_user(username):
        cursor.execute("UPDATE users SET Gebannt='Nein' WHERE Benutzername=?", (username,))
        conn.commit()
        banned_users.pop(username, None)

    def check_login(username, password):
        cursor.execute("SELECT Passwort, Gebannt FROM users WHERE Benutzername=?", (username,))
        result = cursor.fetchone()
        if result is None:
            return False, None
        db_password, gebannt = result
        if gebannt == "Ja":
            return False, True
        return password == db_password, False

except Exception as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Fehler beim Start", f"Ein Fehler ist aufgetreten:\n{e}")
    exit()

# --- GUI Funktionen ---
def add_footer(win):
    tk.Label(win, text="© 2025 Robin Krieg", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(side="bottom", pady=5)

def do_login(event=None):
    username = user_entry.get().strip()
    password = pass_entry.get().strip()

    allowed, reason = check_allowed("login", username)
    if not allowed:
        messagebox.showerror("Login deaktiviert", reason)
        return

    if not username or not password:
        messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
        return

    if username in banned_users:
        entry = banned_users[username]
        expiry = entry['expiry']
        reason = entry.get('reason', 'Kein Grund angegeben.')
        now = datetime.now()
        if now < expiry:
            msg = f"Du wurdest permanent gebannt.\nGrund: {reason}" if expiry == datetime.max else f"Du bist bis {expiry.strftime('%Y-%m-%d %H:%M:%S')} gebannt.\nGrund: {reason}"
            messagebox.showerror("Gebannt", msg)
            return
        else:
            banned_users.pop(username)

    login_ok, banned = check_login(username, password)
    if banned:
        messagebox.showerror("Gebannt", "Du wurdest gebannt!")
    elif login_ok:
        login_win.destroy()
        start_hub(username)
    else:
        messagebox.showerror("Fehler", "Benutzername oder Passwort ist falsch.")

def show_login():
    global login_win, user_entry, pass_entry
    login_win = tk.Tk()
    login_win.title("Login")
    login_win.geometry("350x260")
    login_win.resizable(False, False)

    tk.Label(login_win, text="Benutzername:").pack(pady=(20,5))
    user_entry = tk.Entry(login_win)
    user_entry.pack()

    tk.Label(login_win, text="Passwort:").pack(pady=(10,5))
    pass_entry = tk.Entry(login_win, show="*")
    pass_entry.pack()

    tk.Button(login_win, text="Anmelden", width=15, command=do_login).pack(pady=10)
    tk.Button(login_win, text="Registrieren", width=15, command=show_register).pack(pady=5)
    tk.Button(login_win, text="Account löschen", width=15, command=show_delete_account).pack(pady=5)

    add_footer(login_win)
    login_win.bind('<Return>', do_login)
    login_win.mainloop()

def show_register():
    global reg_win, reg_user_entry, reg_pass_entry
    allowed, reason = check_allowed("register")
    if not allowed:
        messagebox.showerror("Registrierung deaktiviert", reason)
        return

    reg_win = tk.Toplevel()
    reg_win.title("Registrieren")
    reg_win.geometry("350x260")
    reg_win.resizable(False, False)

    tk.Label(reg_win, text="Benutzername:").pack(pady=(20,5))
    reg_user_entry = tk.Entry(reg_win)
    reg_user_entry.pack()

    tk.Label(reg_win, text="Passwort:").pack(pady=(10,5))
    reg_pass_entry = tk.Entry(reg_win, show="*")
    reg_pass_entry.pack()

    def do_register():
        u = reg_user_entry.get().strip()
        p = reg_pass_entry.get().strip()
        if not u or not p:
            messagebox.showerror("Fehler", "Benutzername oder Passwort leer!")
            return
        if u in users:
            messagebox.showerror("Fehler", "Benutzername existiert bereits.")
            return
        users[u] = p
        save_users(users)
        messagebox.showinfo("Erfolg", "Account erstellt!")
        reg_win.destroy()

    tk.Button(reg_win, text="Registrieren", width=17, command=do_register).pack(pady=15)
    add_footer(reg_win)

def show_delete_account():
    allowed, reason = check_allowed("delete")
    if not allowed:
        messagebox.showerror("Account löschen deaktiviert", reason)
        return

    del_win = tk.Toplevel()
    del_win.title("Account löschen")
    del_win.geometry("350x260")
    del_win.resizable(False, False)

    tk.Label(del_win, text="Benutzername:").pack(pady=(20,5))
    del_user_entry = tk.Entry(del_win)
    del_user_entry.pack()

    tk.Label(del_win, text="Passwort:").pack(pady=(10,5))
    del_pass_entry = tk.Entry(del_win, show="*")
    del_pass_entry.pack()

    def do_delete():
        u = del_user_entry.get().strip()
        p = del_pass_entry.get().strip()
        if not u or not p:
            messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
            return
        if u in banned_users:
            messagebox.showerror("Gebannt", "Dieser Account ist gebannt und kann nicht gelöscht werden.")
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

    tk.Button(del_win, text="Account löschen", width=17, command=do_delete).pack(pady=15)
    add_footer(del_win)

def start_hub(username):
    hub_win = tk.Tk()
    hub_win.title(f"Hub - {username}")
    is_owner = username == "Owner"
    hub_win.geometry("800x600" if is_owner else "600x400")
    hub_win.resizable(False, False)

    main_frame = tk.Frame(hub_win)
    main_frame.pack(fill="both", expand=True)

    tk.Label(main_frame, text=f"Hallo, {username}!\nWähle eine Option:", font=("Arial", 14)).pack(pady=20)

    # Beispielbuttons (wie in Code 1)
    tk.Button(main_frame, text="Uhr").pack(pady=5)
    tk.Button(main_frame, text="Stopuhr").pack(pady=5)
    tk.Button(main_frame, text="Timer").pack(pady=5)
    tk.Button(main_frame, text="Planer").pack(pady=5)
    tk.Button(main_frame, text="Dateimanager").pack(pady=5)
    tk.Button(main_frame, text="Taschenrechner").pack(pady=5)
    tk.Button(main_frame, text="Neuigkeiten").pack(pady=5)

    if is_owner:
        tk.Label(main_frame, text="Owner Konsole").pack(pady=10)  # Platzhalter für Konsole

    add_footer(hub_win)
    hub_win.mainloop()

if __name__ == "__main__":
    show_login()
