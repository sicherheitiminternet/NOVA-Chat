import socket
import threading
import re
import json
import os

HOST = '0.0.0.0'
PORT = 12345
clients = {}  # client_socket: username
PIN_FILE = "pinned.json"  # Datei zum Speichern der angepinnten Nachricht

# Erlaubte Farbcodes für Owner
allowed_color_codes = {
    "&1", "&2", "&3", "&4", "&5", "&6", "&7",
    "&8", "&9", "&a", "&b", "&c", "&d", "&e", "&f", "&l", "&o", "&n", "&m", "&l"
}

# --- Pinned-Nachricht laden ---
if not os.path.exists(PIN_FILE):
    with open(PIN_FILE, "w") as f:
        json.dump("", f)

with open(PIN_FILE, "r") as f:
    pinned_message = json.load(f) or None

def save_pinned(message):
    global pinned_message
    pinned_message = message if message.strip() != "" else None
    with open(PIN_FILE, "w") as f:
        json.dump("" if pinned_message is None else pinned_message, f)

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

            if message.startswith("PIN|"):
                new_pin = message.split("|", 1)[1]
                if new_pin.strip() == "":
                    save_pinned("")  # Nachricht löschen
                else:
                    save_pinned(new_pin)  # Nachricht setzen

                # An alle Clients schicken (auch leere Nachricht zum Entfernen)
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

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Socket wiederverwendbar machen
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server.bind((HOST, PORT))
    server.listen()
    print(f"✅ Server läuft auf {HOST}:{PORT} ...")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()


if __name__ == "__main__":
    start_server()
