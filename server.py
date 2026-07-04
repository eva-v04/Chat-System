import socket
import json
import threading
import time

HOST = '127.0.0.1'
PORT = 12345

# Δομές δεδομένων πρωτοκόλλου
clients = {}       # {username: (ip, port)}
user_rooms = {}    # {username: room_name_string ή None}
last_seen = {}     # {username: timestamp_of_last_packet}

lock = threading.Lock()

def send_udp(server_socket, address, message_dict):
    try:
        encoded = json.dumps(message_dict).encode('utf-8')
        server_socket.sendto(encoded, address)
    except Exception as e:
        print(f"[ERROR] Σφάλμα αποστολής στο {address}: {e}")

def broadcast_global(server_socket, message_dict, exclude_user=None):
    for username, address in list(clients.items()):
        if username != exclude_user:
            send_udp(server_socket, address, message_dict)

def broadcast_to_room(server_socket, room_name, message_dict, exclude_user=None):
    for username, current_room in list(user_rooms.items()):
        if current_room == room_name and username != exclude_user:
            if username in clients:
                send_udp(server_socket, clients[username], message_dict)

def check_timeouts(server_socket):
    """Απότομη Αποσύνδεση: Timeout στα 5 λεπτά (300s) για σταθερότητα"""
    while True:
        time.sleep(10)
        current_time = time.time()
        with lock:
            for username, last_time in list(last_seen.items()):
                if current_time - last_time > 300:  
                    print(f"[TIMEOUT] Ο χρήστης '{username}' διαγράφηκε λόγω αδράνειας.")
                    old_room = user_rooms.get(username)
                    if old_room:
                        broadcast_to_room(server_socket, old_room, {
                            "msg_id": 999, "action": "ROOM_ANNOUNCEMENT", "sender": "SERVER",
                            "target": old_room, "payload": f"{username} left the room due to timeout", "status": "SUCCESS"
                        })
                    if username in clients: del clients[username]
                    if username in user_rooms: del user_rooms[username]
                    if username in last_seen: del last_seen[username]

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    print(f"[STARTING] Ο UDP Server ακούει στη θύρα {PORT}...")
    
    threading.Thread(target=check_timeouts, args=(server_socket,), daemon=True).start()
    
    while True:
        try:
            data, client_address = server_socket.recvfrom(4096)
            msg = json.loads(data.decode('utf-8'))
            
            action = msg.get("action")
            sender = msg.get("sender")
            target = msg.get("target")
            payload = msg.get("payload")
            
            with lock:
                # 3.1 Διαδικασία Σύνδεσης / Εγγραφής
                if action == "CONNECT":
                    if not sender or sender in clients or sender.lower() == "server":
                        res = {"msg_id": 502, "action": "CONNECT_RESPONSE", "sender": "SERVER", "target": sender, "payload": "Username already taken", "status": "ERROR"}
                        send_udp(server_socket, client_address, res)
                    else:
                        clients[sender] = client_address
                        user_rooms[sender] = None
                        last_seen[sender] = time.time()
                        print(f"[REGISTER] {sender} -> {client_address}")
                        res = {"msg_id": 501, "action": "CONNECT_RESPONSE", "sender": "SERVER", "target": sender, "payload": "Registration successful", "status": "SUCCESS"}
                        send_udp(server_socket, client_address, res)
                    continue

                # Αν ο χρήστης δεν είναι γραμμένος, αγνόησε το πακέτο
                if sender not in clients:
                    continue
                
                # Ανανέωση Keep-Alive χρόνου για κάθε ληφθέν πακέτο
                last_seen[sender] = time.time()
                clients[sender] = client_address 

                # 3.6 Μηχανισμός Keep-Alive / Heartbeat (PING)
                if action == "PING":
                    continue
                
                # 3.2 Καθολική Εκπομπή (BROADCAST)
                elif action == "BROADCAST":
                    print(f"[BROADCAST] Από {sender}: {payload}")
                    broadcast_global(server_socket, {
                        "msg_id": 503, "action": "BROADCAST", "sender": sender, "target": None, "payload": payload, "status": "SUCCESS"
                    }, exclude_user=sender)
                
                # 3.3 Προσωπικό Μήνυμα (PRIVATE)
                elif action == "PRIVATE":
                    print(f"[PRIVATE] Από {sender} προς {target}: {payload}")
                    if target in clients:
                        send_udp(server_socket, clients[target], {"msg_id": 504, "action": "PRIVATE", "sender": sender, "target": target, "payload": payload, "status": "SUCCESS"})
                    else:
                        send_udp(server_socket, client_address, {"msg_id": 999, "action": "RESPONSE", "sender": "SERVER", "target": sender, "payload": "User offline", "status": "ERROR"})
                
                # 3.4 Διαχείριση Δωματίων (JOIN_ROOM)
                elif action == "JOIN_ROOM":
                    room_name = target.strip() if target else ""
                    old_room = user_rooms.get(sender)
                    if old_room:
                        broadcast_to_room(server_socket, old_room, {"msg_id": 505, "action": "ROOM_ANNOUNCEMENT", "sender": "SERVER", "target": old_room, "payload": f"{sender} left the room", "status": "SUCCESS"}, exclude_user=sender)
                    
                    user_rooms[sender] = room_name
                    print(f"[ROOM] Ο {sender} μπήκε στο δωμάτιο '{room_name}'")
                    broadcast_to_room(server_socket, room_name, {"msg_id": 505, "action": "ROOM_ANNOUNCEMENT", "sender": "SERVER", "target": room_name, "payload": f"{sender} joined the room", "status": "SUCCESS"}, exclude_user=sender)
                    send_udp(server_socket, client_address, {"msg_id": 999, "action": "RESPONSE", "sender": "SERVER", "target": sender, "payload": f"Μεταφερθήκατε στο δωμάτιο '{room_name}'", "status": "SUCCESS"})

                # Αποστολή Μηνύματος στο Κανάλι (ROOM_MSG)
                elif action == "ROOM_MSG":
                    current_room = user_rooms.get(sender)
                    print(f"[ROOM MSG] Από {sender} στο '{current_room}': {payload}")
                    if current_room:
                        broadcast_to_room(server_socket, current_room, {"msg_id": 506, "action": "ROOM_MSG", "sender": sender, "target": current_room, "payload": payload, "status": "SUCCESS"}, exclude_user=sender)

                # 3.5 Προβολή Συνδεδεμένων Χρηστών (LIST_USERS)
                elif action == "LIST_USERS":
                    user_list = list(clients.keys())
                    print(f"[LIST REQUEST] Αποστολή λίστας χρηστών στον {sender}")
                    send_udp(server_socket, client_address, {"msg_id": 507, "action": "LIST_USERS_RESPONSE", "sender": "SERVER", "target": sender, "payload": user_list, "status": "SUCCESS"})

                # 3.7 Αποσύνδεση (DISCONNECT)
                elif action == "DISCONNECT":
                    if sender in clients: del clients[sender]
                    if sender in user_rooms: del user_rooms[sender]
                    if sender in last_seen: del last_seen[sender]
                    print(f"[DISCONNECT] Ο χρήστης {sender} αποσυνδέθηκε.")

        except Exception as e:
            print(f"[SERVER ERROR]: {e}")

if __name__ == "__main__":
    start_server()