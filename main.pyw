import tkinter as tk
from tkinter import messagebox, ttk
import subprocess
from supabase import create_client
import bcrypt
import json
import sys
import os
import webbrowser  # für anklickbare Links

# ----- Supabase Setup -----
SUPABASE_URL = "https://vaxelbftwysyecnwwbpq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZheGVsYmZ0d3lzeWVjbnd3YnBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY3NjI3NDgsImV4cCI6MjA4MjMzODc0OH0.cEE1dJ8I1bJ0m9cR3ezpVGILApQN_crxWpsrwe7hXi8"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OWNER_USERNAME = "Owner"
USER_JSON_FILE = "current_user.json"
FIRST_RUN_FILE = "first_run.json"

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
    result = supabase.table("users").select("id, password, banned").eq("username", username).execute()
    data = result.data
    if not data:
        return None, False
    db_password = data[0]["password"]
    banned = data[0]["banned"]
    user_id = data[0]["id"]
    if banned:
        return None, True
    if bcrypt.checkpw(password.encode(), db_password.encode()):
        return user_id, False
    return None, False

def delete_user(username):
    supabase.table("users").delete().eq("username", username).execute()

def ban_user(username):
    supabase.table("users").update({"banned": True}).eq("username", username).execute()

def unban_user(username):
    supabase.table("users").update({"banned": False}).eq("username", username).execute()

def get_all_users():
    result = supabase.table("users").select("username, password, banned, is_admin").execute()
    return result.data

def is_admin(username):
    result = supabase.table("users").select("is_admin").eq("username", username).execute()
    data = result.data
    if data and data[0]["is_admin"]:
        return True
    return False

# ----- Admin-Hub -----
def show_admin_hub(username):
    hub = tk.Tk()
    hub.title(f"Admin-Hub - {username}")
    hub.geometry("600x500")
    hub.resizable(False, False)
    hub.configure(bg="#2b2b2b")
    hub.configure(highlightbackground="blue", highlightthickness=4)

    tk.Label(hub, text=f"Willkommen, {username} (Admin)", font=("Segoe UI", 14, "bold"),
             fg="white", bg="#2b2b2b").pack(pady=10)

    if username == OWNER_USERNAME:
        def open_owner_chat():
            try:
                subprocess.Popen([sys.executable, "Server.py"])
                subprocess.Popen([sys.executable, "Client.pyw", username])
            except Exception as e:
                messagebox.showerror("Fehler", f"Chat konnte nicht gestartet werden:\n{e}")

        chat_btn = tk.Button(hub, text="In den Chat (Owner)", width=25, bg="blue", fg="white", command=open_owner_chat)
        chat_btn.pack(pady=10)

    # Treeview Setup
    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview", background="#3c3f41", foreground="white", fieldbackground="#3c3f41")
    style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), foreground="white", background="#3c3f41")
    style.map("Treeview",
              background=[("selected", "blue")],
              foreground=[("selected", "white")])

    columns = ("Benutzername", "Passwort", "Status")
    tree = ttk.Treeview(hub, columns=columns, show="headings", height=15)
    tree.pack(pady=10, padx=10, fill="both", expand=True)

    tree.heading("Benutzername", text="Benutzername")
    tree.heading("Passwort", text="Passwort")
    tree.heading("Status", text="Gebannt")
    tree.column("Benutzername", width=200, anchor="center")
    tree.column("Passwort", width=200, anchor="center")
    tree.column("Status", width=100, anchor="center")

    scrollbar = ttk.Scrollbar(hub, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")

    btn_frame = tk.Frame(hub, bg="#2b2b2b")
    btn_frame.pack(pady=10)

    ban_btn = tk.Button(btn_frame, text="Bannen", width=12, bg="#e74c3c", fg="white")
    ban_btn.grid(row=0, column=0, padx=5)
    unban_btn = tk.Button(btn_frame, text="Entbannen", width=12, bg="#2ecc71", fg="white")
    unban_btn.grid(row=0, column=1, padx=5)
    delete_btn = tk.Button(btn_frame, text="Löschen", width=12, bg="#f39c12", fg="white")
    delete_btn.grid(row=0, column=2, padx=5)

    def update_buttons_state(event=None):
        selection = tree.selection()
        if not selection:
            ban_btn.config(state="disabled")
            unban_btn.config(state="disabled")
            delete_btn.config(state="disabled")
            return
        user = tree.item(selection[0])["values"][0]
        status = tree.item(selection[0])["values"][2]
        delete_btn.config(state="normal" if user != OWNER_USERNAME else "disabled")
        if status == "Ja":
            ban_btn.config(state="disabled")
            unban_btn.config(state="normal")
        else:
            ban_btn.config(state="normal" if user != OWNER_USERNAME else "disabled")
            unban_btn.config(state="disabled")

    tree.bind("<<TreeviewSelect>>", update_buttons_state)

    def ban_selected():
        selection = tree.selection()
        if selection:
            user = tree.item(selection[0])["values"][0]
            if user == OWNER_USERNAME:
                messagebox.showerror("Fehler", "Du kannst dich nicht selbst bannen ❌")
                return
            ban_user(user)

    def unban_selected():
        selection = tree.selection()
        if selection:
            user = tree.item(selection[0])["values"][0]
            unban_user(user)

    def delete_selected():
        selection = tree.selection()
        if selection:
            user = tree.item(selection[0])["values"][0]
            if user == OWNER_USERNAME:
                messagebox.showerror("Fehler", "Du kannst dich nicht selbst löschen ❌")
                return
            if messagebox.askyesno("Sicher?", f"Willst du {user} wirklich löschen?"):
                delete_user(user)

    ban_btn.config(command=ban_selected)
    unban_btn.config(command=unban_selected)
    delete_btn.config(command=delete_selected)

    # Automatisches Refresh
    def refresh_user_list():
        for row in tree.get_children():
            tree.delete(row)
        for user_data in get_all_users():
            status = "Ja" if user_data["banned"] else "Nein"
            tree.insert("", "end", values=(user_data["username"], user_data["password"], status))
        update_buttons_state()
        hub.after(5000, refresh_user_list)

    refresh_user_list()
    hub.mainloop()

# ----- Register GUI -----
def show_register():
    reg_win = tk.Toplevel()
    reg_win.title("Registrieren")
    reg_win.geometry("350x260")
    reg_win.resizable(False, False)

    tk.Label(reg_win, text="Benutzername:").pack(pady=(20, 5))
    reg_user_entry = tk.Entry(reg_win)
    reg_user_entry.pack()

    tk.Label(reg_win, text="Passwort:").pack(pady=(10, 5))
    reg_pass_entry = tk.Entry(reg_win)
    reg_pass_entry.pack()

    def do_register():
        u = reg_user_entry.get().strip()
        p = reg_pass_entry.get().strip()
        if not u or not p:
            messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
            return
        if register_user(u, p):
            messagebox.showinfo("Erfolg", "Account erstellt! Du kannst dich jetzt anmelden.")
            reg_win.destroy()
        else:
            messagebox.showerror("Fehler", "Benutzername existiert bereits oder ist Owner.")

    tk.Button(reg_win, text="Registrieren", width=15, command=do_register).pack(pady=10)
    tk.Label(reg_win, text="© 2025 NOVA-Chat", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(side="bottom", pady=10)

# ----- Delete Account GUI -----
def show_delete_account():
    del_win = tk.Toplevel()
    del_win.title("Account löschen")
    del_win.geometry("350x260")
    del_win.resizable(False, False)

    tk.Label(del_win, text="Benutzername:").pack(pady=(10,0))
    del_user_entry = tk.Entry(del_win)
    del_user_entry.pack()

    tk.Label(del_win, text="Passwort:").pack(pady=(10,0))
    del_pass_entry = tk.Entry(del_win)
    del_pass_entry.pack()

    def do_delete():
        u = del_user_entry.get().strip()
        p = del_pass_entry.get().strip()
        user_id, banned = check_login(u, p)
        if not u or not p:
            messagebox.showerror("Fehler", "Benutzername und Passwort dürfen nicht leer sein.")
            return
        if banned:
            messagebox.showerror("Fehler", "Du wurdest gebannt! Bitte melde dich beim Owner.")
            return
        if user_id:
            if messagebox.askyesno("Sicher?", "Willst du diesen Account wirklich löschen?"):
                delete_user(u)
                messagebox.showinfo("Erledigt", "Account wurde gelöscht.")
                del_win.destroy()
        else:
            messagebox.showerror("Fehler", "Benutzername oder Passwort ist falsch.")

    tk.Button(del_win, text="Löschen", command=do_delete).pack(pady=10)
    tk.Label(del_win, text="© 2025 NOVA-Chat", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(side="bottom", pady=10)

# ----- Login GUI mit Erststart Popup -----
def show_login_with_agb():
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
    login_btn = tk.Button(btn_frame, text="Anmelden", width=12, state="disabled")
    login_btn.grid(row=0, column=0, padx=5)

    reg_btn = tk.Button(btn_frame, text="Registrieren", width=15, command=show_register, state="disabled")
    reg_btn.grid(row=0, column=1, padx=5)
    del_btn = tk.Button(btn_frame, text="Account löschen", width=15, command=show_delete_account, state="disabled")
    del_btn.grid(row=1, column=0, columnspan=2, pady=(10,0))

    tk.Label(login_win, text="© 2025 NOVA-Chat", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(side="bottom", pady=10)

    def do_login():
        username = user_entry.get().strip()
        password = pass_entry.get().strip()
        user_id, banned = check_login(username, password)
        if banned:
            messagebox.showerror("Fehler", "Dieser Benutzer wurde gebannt ❌")
            return
        if user_id:
            with open(USER_JSON_FILE, "w", encoding="utf-8") as f:
                json.dump({"user_id": user_id}, f)
            login_win.destroy()
            if is_admin(username):
                show_admin_hub(username)
            else:
                try:
                    subprocess.Popen([sys.executable, "Server.py"])
                    subprocess.Popen([sys.executable, "Client.pyw", username])
                except Exception as e:
                    messagebox.showerror("Fehler beim Starten der Skripte", f"{e}")
        else:
            messagebox.showerror("Fehler", "Benutzername oder Passwort ist falsch.")

    login_btn.config(command=do_login)

    # ----- Erststart AGB Popup -----
    def show_first_run_popup():
        popup = tk.Toplevel(login_win)
        popup.title("Wichtige Information")
        popup.geometry("400x200")
        popup.resizable(False, False)
        popup.grab_set()  # blockiert Interaktion mit Login

        tk.Label(popup, text="Wenn du fortfährst, stimmst du unseren AGBs und der Datenschutzerklärung zu:",
                 wraplength=380, justify="left").pack(pady=10)

        def open_agb(): webbrowser.open("agb.html")
        def open_privacy(): webbrowser.open("datenschutz.html")

        agb_link = tk.Label(popup, text="AGB", fg="blue", cursor="hand2")
        agb_link.pack()
        agb_link.bind("<Button-1>", lambda e: open_agb())

        privacy_link = tk.Label(popup, text="Datenschutzerklärung", fg="blue", cursor="hand2")
        privacy_link.pack()
        privacy_link.bind("<Button-1>", lambda e: open_privacy())

        agree_var = tk.BooleanVar()
        tk.Checkbutton(popup, text="Ich stimme zu", variable=agree_var).pack(pady=10)

        def proceed():
            if not agree_var.get():
                messagebox.showerror("Fehler", "Du musst den Bedingungen zustimmen, um fortzufahren.")
                return
            with open(FIRST_RUN_FILE, "w", encoding="utf-8") as f:
                json.dump({"first_run_done": True}, f)
            popup.destroy()
            # Login freigeben
            login_btn.config(state="normal")
            reg_btn.config(state="normal")
            del_btn.config(state="normal")

        tk.Button(popup, text="Fortfahren", width=15, command=proceed).pack(pady=20)

    if not os.path.exists(FIRST_RUN_FILE):
        show_first_run_popup()
    else:
        login_btn.config(state="normal")
        reg_btn.config(state="normal")
        del_btn.config(state="normal")

    login_win.bind('<Return>', lambda event: do_login())
    login_win.mainloop()

# ----- Main -----
if __name__ == "__main__":
    show_login_with_agb()
