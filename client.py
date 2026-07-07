import socket
import threading
import json
import time

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
SERVER_ADDRESS = (SERVER_HOST, SERVER_PORT)

authenticated = False
local_msg_id = 100
current_room = None

def get_next_msg_id():
    global local_msg_id
    local_msg_id += 1
    return local_msg_id

def send_heartbeat(client_socket, username):
    """Στέλνει PING ανά 30 δευτερόλεπτα στον Server"""
    while authenticated:
        time.sleep(30)
        ping_pkt = {"msg_id": get_next_msg_id(), "action": "PING", "sender": username, "target": None, "payload": None, "status": None}
        try:
            client_socket.sendto(json.dumps(ping_pkt).encode('utf-8'), SERVER_ADDRESS)
        except:
            break

def receive_messages(client_socket):
    global authenticated
    while True:
        try:
            data, _ = client_socket.recvfrom(4096)
            msg = json.loads(data.decode('utf-8'))
            
            action = msg.get("action")
            sender = msg.get("sender")
            payload = msg.get("payload")
            status = msg.get("status")
            
            if action == "CONNECT_RESPONSE":
                if status == "SUCCESS":
                    authenticated = True
                else:
                    print(f"\n[SERVER REJECTION]: {payload}")
            elif action == "BROADCAST":
                print(f"\n[{sender} προς όλους]: {payload}")
            elif action == "PRIVATE":
                print(f"\n[{sender} προσωπικό]: {payload}")
            elif action == "ROOM_MSG":
                print(f"\n[{sender} στο δωμάτιο {msg.get('target')}]: {payload}")
            elif action == "ROOM_ANNOUNCEMENT":
                print(f"\n[ROOM INFO]: {payload}")
            elif action == "LIST_USERS_RESPONSE":
                print(f"\n[SERVER] Συνδεδεμένοι χρήστες: {', '.join(payload)}")
            
            elif action == "HISTORY_RESPONSE":
                print(f"\n--- ΙΣΤΟΡΙΚΟ ΜΗΝΥΜΑΤΩΝ ---")
                if not payload:
                    print("Δεν υπάρχουν παλαιότερα μηνύματα.")
                for msg_data in payload:
                    print(f"[{msg_data['time']}] {msg_data['sender']}: {msg_data['payload']}")
                print("--------------------------")
            
            
            
            
            elif action in ["INFO", "RESPONSE"]:
                if status == "ERROR":
                    print(f"\n[ERROR]: {payload}")
                else:
                    print(f"\n[SERVER]: {payload}")
        except Exception:
            break

def start_client():
    global authenticated, current_room
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    username = input("Δώσε το username σου: ")
    connect_pkt = {"msg_id": 101, "action": "CONNECT", "sender": username, "target": None, "payload": None, "status": None}
    
    receiver_thread = threading.Thread(target=receive_messages, args=(client_socket,), daemon=True)
    receiver_thread.start()
    
    try:
        client_socket.sendto(json.dumps(connect_pkt).encode('utf-8'), SERVER_ADDRESS)
        time.sleep(0.5) 
    except Exception as e:
        print(f"[ERROR] Αποτυχία: {e}")
        return

    print(f"[SUCCESS] Επιτυχής σύνδεση ως '{username}'!")
    threading.Thread(target=send_heartbeat, args=(client_socket, username), daemon=True).start()

    # Οδηγίες Χρήσης
    print("\n" + "="*50)
    print("📢 ΟΔΗΓΙΕΣ ΧΡΗΣΗΣ ΕΝΤΟΛΩΝ CHAT:")
    print("1. Για να μπεις σε δωμάτιο γράψε: #join <room_name>")
    print("2. Για να στείλεις στο δωμάτιο γράψε: @room <μήνυμα>")
    print("3. Για καθολικό μήνυμα γράψε: @all <μήνυμα>")
    print("4. Για προσωπικό μήνυμα γράψε: @<username> <μήνυμα>")
    print("5. Για λίστα χρηστών γράψε: #list")
    print("6. Για γενικό ιστορικό ή δωματίου: #history")
    print("7. Για όλο το προσωπικό ιστορικό: #history private")
    print("8. Για ιστορικό με συγκεκριμένο χρήστη: #history @<username>")
    print("9. Για έξοδο γράψε: #exit")
    print("="*50 + "\n")

    while True:
        try:
            user_input = input()
            if not user_input:
                continue
            
            if user_input.strip() == "#exit":
                pkt = {"msg_id": get_next_msg_id(), "action": "DISCONNECT", "sender": username, "target": None, "payload": None, "status": None}
                client_socket.sendto(json.dumps(pkt).encode('utf-8'), SERVER_ADDRESS)
                break
            elif user_input.strip() == "#list":
                pkt = {"msg_id": get_next_msg_id(), "action": "LIST_USERS", "sender": username, "target": None, "payload": None, "status": None}
            
            
            elif user_input.startswith("#history"):
                parts = user_input.split()
                
                # Περίπτωση 1: Συγκεκριμένη ιδιωτική συνομιλία 
                if len(parts) > 1 and parts[1].startswith("@"):
                    target_user = parts[1][1:] # Αφαιρούμε το '@'
                    pkt = {"msg_id": get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": username, "target": "PRIVATE", "payload": target_user, "status": None}
                    
                # Περίπτωση 2: Όλα τα προσωπικά μηνύματα του χρήστη 
                elif len(parts) > 1 and parts[1].lower() == "private":
                    pkt = {"msg_id": get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": username, "target": "PRIVATE", "payload": None, "status": None}
                    
                # Περίπτωση 3: Απλό #history (Δωμάτιο αν είναι μέσα, αλλιώς Καθολικά)
                else:
                    if current_room:
                        pkt = {"msg_id": get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": username, "target": "ROOM", "payload": current_room, "status": None}
                    else:
                        pkt = {"msg_id": get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": username, "target": "BROADCAST", "payload": None, "status": None}
            
            
            
            
            elif user_input.startswith("#join "):
                room = user_input[6:].strip()
                current_room = room
                pkt = {"msg_id": get_next_msg_id(), "action": "JOIN_ROOM", "sender": username, "target": room, "payload": None, "status": None}
            elif user_input.startswith("@all "):
                content = user_input[5:]
                pkt = {"msg_id": get_next_msg_id(), "action": "BROADCAST", "sender": username, "target": None, "payload": content, "status": None}
            elif user_input.startswith("@room "):
                if not current_room:
                    print("[ERROR]: Δεν βρίσκεσαι σε κάποιο δωμάτιο. Μπες πρώτα με #join <room>")
                    continue
                content = user_input[6:]
                pkt = {"msg_id": get_next_msg_id(), "action": "ROOM_MSG", "sender": username, "target": current_room, "payload": content, "status": None}
            elif user_input.startswith("@") and " " in user_input:
                parts = user_input.split(" ", 1)
                target_user = parts[0][1:]
                content = parts[1]
                pkt = {"msg_id": get_next_msg_id(), "action": "PRIVATE", "sender": username, "target": target_user, "payload": content, "status": None}
            else:
                print("Μη έγκυρη εντολή.")
                continue

            client_socket.sendto(json.dumps(pkt).encode('utf-8'), SERVER_ADDRESS)
            
        except (KeyboardInterrupt, SystemExit):
            break

    client_socket.close()

if __name__ == "__main__":
    start_client()