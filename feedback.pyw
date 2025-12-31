import sys
import tkinter as tk
from tkinter import messagebox
from supabase import create_client

# --- Supabase Setup ---
SUPABASE_URL = "https://vaxelbftwysyecnwwbpq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZheGVsYmZ0d3lzeWVjbnd3YnBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY3NjI3NDgsImV4cCI6MjA4MjMzODc0OH0.cEE1dJ8I1bJ0m9cR3ezpVGILApQN_crxWpsrwe7hXi8"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Benutzername vom Hub übernehmen ---
username = sys.argv[1]

# --- DB-Funktionen ---
def load_ideas():
    result = supabase.table("ideas").select("*").execute()
    return result.data if result.data else []

def save_idea(text, author):
    supabase.table("ideas").insert({
        "text": text,
        "status": "Offen",
        "author": author
    }).execute()

def update_idea_status(idea_id, new_status):
    supabase.table("ideas").update({"status": new_status}).eq("id", idea_id).execute()

def delete_idea(idea_id):
    supabase.table("ideas").delete().eq("id", idea_id).execute()

# --- Feedback GUI ---
def start_external_feedback():
    open_idea_system(username)

def open_idea_system(username):
    win = tk.Toplevel()
    win.title(f"Ideen-System – Eingeloggt als {username}")
    win.geometry("600x450")
    win.resizable(False, False)
    win.configure(bg="#f0f0f0")

    header = tk.Label(win, text=f"Willkommen, {username}!", font=("Arial", 16, "bold"), bg="blue", fg="white")
    header.pack(fill="x", pady=(0, 10))

    if username != "Owner":
        tk.Label(win, text="Neue Idee einreichen:", font=("Arial", 14), bg="#f0f0f0").pack(pady=(5, 5))
        idea_entry = tk.Text(win, height=6, width=60, font=("Arial", 12))
        idea_entry.pack(pady=(0, 10))

        def submit_idea():
            text = idea_entry.get("1.0", tk.END).strip()
            if not text:
                messagebox.showwarning("Achtung", "Bitte eine Idee eingeben.")
                return
            save_idea(text, username)
            idea_entry.delete("1.0", tk.END)
            messagebox.showinfo("Gespeichert", "Idee wurde eingereicht!")

        tk.Button(win, text="Einreichen", font=("Arial", 12, "bold"),
                  bg="blue", fg="white", activebackground="blue",
                  activeforeground="white", command=submit_idea).pack(pady=(0, 10))

    else:  # Owner
        tk.Label(win, text="Eingereichte Ideen:", font=("Arial", 14), bg="#f0f0f0").pack(pady=(5, 5))

        list_frame = tk.Frame(win)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        listbox = tk.Listbox(list_frame, font=("Arial", 12), width=70, height=15)
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        # --- DB-Aktualisierung alle 5 Sekunden ---
        def refresh_list():
            listbox.delete(0, tk.END)
            ideas = load_ideas()
            for idea in ideas:
                listbox.insert(tk.END, f"{idea['id']}. {idea['text']} | Status: {idea['status']} | Von: {idea['author']}")
            win.after(5000, refresh_list)  # wiederholen

        def update_status(new_status):
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Achtung", "Bitte eine Idee auswählen.")
                return
            index = selection[0]
            ideas = load_ideas()
            idea_id = ideas[index]["id"]
            update_idea_status(idea_id, new_status)

        def delete_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Achtung", "Bitte eine Idee auswählen.")
                return
            index = selection[0]
            ideas = load_ideas()
            delete_idea(ideas[index]["id"])

        btn_frame = tk.Frame(win, bg="#f0f0f0")
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Akzeptieren", font=("Arial", 12, "bold"),
                  bg="blue", fg="white", activebackground="blue", activeforeground="white",
                  command=lambda: update_status("Akzeptiert")).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Ablehnen", font=("Arial", 12, "bold"),
                  bg="blue", fg="white", activebackground="blue", activeforeground="white",
                  command=lambda: update_status("Abgelehnt")).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Löschen", font=("Arial", 12, "bold"),
                  bg="red", fg="white", activebackground="red", activeforeground="white",
                  command=delete_selected).grid(row=0, column=2, padx=5)

        refresh_list()  # Initiale Abfrage starten

    # Footer
    tk.Label(win, text="© 2025 NOVA-Chat", font=("Segoe UI", 10, "bold"),
             fg="black", bg=win.cget("bg")).pack(side="bottom", fill="x", pady=5)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    start_external_feedback()
    root.mainloop()
