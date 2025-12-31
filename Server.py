import socket
import threading
import re
from supabase import create_client, Client

# --- Supabase Setup ---
SUPABASE_URL = "https://vaxelbftwysyecnwwbpq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZheGVsYmZ0d3lzeWVjbnd3YnBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY3NjI3NDgsImV4cCI6MjA4MjMzODc0OH0.cEE1dJ8I1bJ0m9cR3ezpVGILApQN_crxWpsrwe7hXi8"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HOST = '0.0.0.0'
PORT = 12345
clients = {}  # client_socket: username

# Erlaubte Farbcodes für Owner
allowed_color_codes = {
    "&1", "&2", "&3", "&4", "&5", "&6", "&7",
    "&8", "&9", "&a", "&b", "&c", "&d", "&e", "&f", "&l", "&o", "&n", "&m"
}

# --- Pinned-Nachricht laden ---
def load_pinned():
    res = supabase.table("pinned_messages").select("*").limit(1).execute()
    if res.data:
        return res.data[0]["message"]
    return None

def save_pinned(message):
    global pinned_message
    pinned_message = message if message.strip() != "" else None

    if pinned_message is None:
        # Alte Nachricht löschen
        supabase.table("pinned_messages").delete().neq("id", 0).execute()
    else:
        # Nachricht updaten oder neu einfügen
        existing = supabase.table("pinned_messages").select("*").limit(1).execute()
        if existing.data:
            supabase.table("pinned_messages").update({"message": pinned_message}).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.table("pinned_messages").insert({"message": pinned_message}).execute()

pinned_message = load_pinned()

# --- Hilfsfunktionen ---
def strip_disallowed_colors(message, username):
    if username.lower() != "owner":
        return re.sub(r"&[0-9a-flomnr]", "", message, flags=re.IGNORECASE)
    else:
        def repl(m):
            code = m.group(0).lower()
            return code if code in allowed_color_codes else ""
        return re.sub(r"&[0-9a-flomnr]", repl, message, flags=re.IGNORECASE)

def send_to_client(client, message, color="white"):
    try:
        client.send(f"{color}|{message}".encode('utf-8'))
    except:
        pass

def broadcast(message, color="white", exclude=None):
    for client in clients:
        if exclude and client == exclude:
            continue
        send_to_client(client, message, color)

# --- Client Handling ---
def handle_client(client_socket):
    global pinned_message
    try:
        username = client_socket.recv(1024).decode('utf-8').strip()
        clients[client_socket] = username

        # Angepinnte Nachricht an neuen Client senden, falls vorhanden
        if pinned_message:
            try:
                client_socket.send(f"PIN|{pinned_message}".encode('utf-8'))
            except:
                pass

        color = "#1100FD" if username.lower() == "owner" else "white"
        broadcast(f"{username} ist dem Chat beigetreten.", color=color)

        while True:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break

            # DELETE Nachricht
            if message.startswith("DELETE|"):
                msg_to_delete = message.split("|", 1)[1]
    
                # Nur Owner kann alle löschen
                requesting_user = username.lower()
                msg_owner = msg_to_delete.split(":", 1)[0].lower()
    
                if requesting_user == "owner" or requesting_user == msg_owner:
                    for c in clients:
                        try:
                            c.send(f"DELETE|{msg_to_delete}".encode('utf-8'))
                        except:
                            pass
                else:
                    try:
                        client_socket.send("❌ Du kannst nur deine eigenen Nachrichten löschen.".encode('utf-8'))
                    except:
                        pass
                continue

            # PIN Handling
            if message.startswith("PIN|"):
                new_pin = message.split("|", 1)[1]
                if new_pin.strip() == "":
                    save_pinned("")  # Nachricht löschen
                else:
                    save_pinned(new_pin)  # Nachricht setzen

                for c in clients:
                    try:
                        c.send(f"PIN|{'' if pinned_message is None else pinned_message}".encode('utf-8'))
                    except:
                        pass
            else:
                clean_msg = strip_disallowed_colors(message, username)
                color = "#1100FD" if username.lower() == "owner" else "white"
                broadcast(clean_msg, color=color)

    finally:
        if client_socket in clients:
            left_user = clients[client_socket]
            del clients[client_socket]
            color = "#1100FD" if left_user.lower() == "owner" else "white"
            broadcast(f"{left_user} hat den Chat verlassen.", color=color)
            client_socket.close()

# --- Server Start ---
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"✅ Server läuft auf {HOST}:{PORT} ...")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_server()
