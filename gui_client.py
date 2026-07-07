import socket
import threading
import json
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python UDP Chat System")
        self.root.geometry("650x500")
        
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = None
        self.username = ""
        self.authenticated = False
        self.local_msg_id = 100
        self.current_room = None

        self.setup_login_interface()

    def get_next_msg_id(self):
        self.local_msg_id += 1
        return self.local_msg_id

    def setup_login_interface(self):
        """Φόρμα Σύνδεσης"""
        self.login_frame = tk.Frame(self.root, padx=20, pady=20)
        self.login_frame.pack(expand=True)

        tk.Label(self.login_frame, text="Username:", font=("Arial", 11)).grid(row=0, column=0, pady=5, sticky="e")
        self.ent_username = tk.Entry(self.login_frame, font=("Arial", 11))
        self.ent_username.grid(row=0, column=1, pady=5)
        self.ent_username.insert(0, "user1")

        tk.Label(self.login_frame, text="Server IP:", font=("Arial", 11)).grid(row=1, column=0, pady=5, sticky="e")
        self.ent_ip = tk.Entry(self.login_frame, font=("Arial", 11))
        self.ent_ip.grid(row=1, column=1, pady=5)
        self.ent_ip.insert(0, "127.0.0.1") # Εδώ βάζουμε την IP του server

        tk.Label(self.login_frame, text="Port:", font=("Arial", 11)).grid(row=2, column=0, pady=5, sticky="e")
        self.ent_port = tk.Entry(self.login_frame, font=("Arial", 11))
        self.ent_port.grid(row=2, column=1, pady=5)
        self.ent_port.insert(0, "12345")

        self.btn_connect = tk.Button(self.login_frame, text="Σύνδεση", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=self.connect_to_server)
        self.btn_connect.grid(row=3, column=0, columnspan=2, pady=15, ipadx=20)

    def connect_to_server(self):
        self.username = self.ent_username.get().strip()
        ip = self.ent_ip.get().strip()
        port_str = self.ent_port.get().strip()

        if not self.username or not ip or not port_str:
            messagebox.showerror("Σφάλμα", "Όλα τα πεδία είναι υποχρεωτικά!")
            return

        try:
            port = int(port_str)
            self.server_address = (ip, port)
        except ValueError:
            messagebox.showerror("Σφάλμα", "Το Port πρέπει να είναι αριθμός!")
            return

        # Εκκίνηση thread λήψης
        threading.Thread(target=self.receive_messages, daemon=True).start()

        # Αποστολή CONNECT
        connect_pkt = {"msg_id": 101, "action": "CONNECT", "sender": self.username, "target": None, "payload": None, "status": None}
        self.client_socket.sendto(json.dumps(connect_pkt).encode('utf-8'), self.server_address)
        
        # Αναμονή για απάντηση (μικρό delay)
        time.sleep(0.5)
        if self.authenticated:
            self.login_frame.pack_forget()
            self.setup_main_interface()
            # Έναρξη Heartbeat
            threading.Thread(target=self.send_heartbeat, daemon=True).start()
        else:
            messagebox.showerror("Αποτυχία", "Ο Server απέρριψε τη σύνδεση ή είναι offline.")

    def setup_main_interface(self):
        """Κεντρική Οθόνη Chat"""
        self.main_frame = tk.Frame(self.root, padx=10, pady=10)
        self.main_frame.pack(fill="both", expand=True)

        # Αριστερό Panel (Μηνύματα και Αποστολή)
        left_panel = tk.Frame(self.main_frame)
        left_panel.pack(side="left", fill="both", expand=True)

        self.chat_area = scrolledtext.ScrolledText(left_panel, wrap=tk.WORD, font=("Arial", 10), state="disabled")
        self.chat_area.pack(fill="both", expand=True, pady=(0, 10))

        # Ζώνη εισαγωγής μηνύματος
        input_frame = tk.Frame(left_panel)
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="Τύπος:").pack(side="left")
        self.msg_type_combo = ttk.Combobox(input_frame, values=["Broadcast", "Room", "Private"], width=10, state="readonly")
        self.msg_type_combo.set("Broadcast")
        self.msg_type_combo.pack(side="left", padx=5)

        tk.Label(input_frame, text="Προς/Στόχος:").pack(side="left")
        self.ent_target = tk.Entry(input_frame, width=10)
        self.ent_target.pack(side="left", padx=5)

        self.ent_msg = tk.Entry(input_frame, font=("Arial", 10))
        self.ent_msg.pack(side="left", fill="x", expand=True, padx=5)
        self.ent_msg.bind("<Return>", lambda event: self.send_message())

        btn_send = tk.Button(input_frame, text="Αποστολή", bg="#2196F3", fg="white", command=self.send_message)
        btn_send.pack(side="right", padx=5)
        

        # Δεξί Panel (Δωμάτια και Χρήστες)
        right_panel = tk.Frame(self.main_frame, width=150, padx=10)
        right_panel.pack(side="right", fill="y")

        # Διαχείριση Room
        tk.Label(right_panel, text="Room Management", font=("Arial", 10, "bold")).pack(pady=(0,5))
        self.lbl_current_room = tk.Label(right_panel, text="Room: None", fg="blue")
        self.lbl_current_room.pack()
        
        self.ent_room_name = tk.Entry(right_panel, width=15)
        self.ent_room_name.pack(pady=5)
        btn_join = tk.Button(right_panel, text="Join/Change Room", command=self.join_room)
        btn_join.pack(fill="x", pady=2)

        tk.Frame(right_panel, height=2, bd=1, relief="sunken").pack(fill="x", pady=15)

        # Κουμπιά ενεργειών
        btn_list = tk.Button(right_panel, text="Ποιοι είναι μέσα;", bg="#FF9800", fg="white", command=self.request_user_list)
        btn_list.pack(fill="x", pady=5)
        btn_history = tk.Button(right_panel, text="Ιστορικό", bg="#9C27B0", fg="white", command=self.request_history)
        btn_history.pack(fill="x", pady=5)

        btn_exit = tk.Button(right_panel, text="Έξοδος", bg="#f44336", fg="white", command=self.disconnect_server)
        btn_exit.pack(fill="x", side="bottom", pady=10)

        self.log_message("[SYSTEM]: Επιτυχής σύνδεση στο chat!")

    def log_message(self, text):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, text + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state="disabled")

    def send_heartbeat(self):
        while self.authenticated:
            time.sleep(30)
            ping_pkt = {"msg_id": self.get_next_msg_id(), "action": "PING", "sender": self.username, "target": None, "payload": None, "status": None}
            try:
                self.client_socket.sendto(json.dumps(ping_pkt).encode('utf-8'), self.server_address)
            except:
                break

    def receive_messages(self):
        while True:
            try:
                data, _ = self.client_socket.recvfrom(4096)
                msg = json.loads(data.decode('utf-8'))
                
                action = msg.get("action")
                sender = msg.get("sender")
                payload = msg.get("payload")
                status = msg.get("status")
                
                if action == "CONNECT_RESPONSE":
                    if status == "SUCCESS":
                        self.authenticated = True
                elif action == "BROADCAST":
                    self.log_message(f"[{sender} προς όλους]: {payload}")
                elif action == "PRIVATE":
                    self.log_message(f"[{sender} προσωπικό]: {payload}")
                elif action == "ROOM_MSG":
                    self.log_message(f"[{sender} στο δωμάτιο {msg.get('target')}]: {payload}")
                elif action == "ROOM_ANNOUNCEMENT":
                    self.log_message(f"[ROOM INFO]: {payload}")
                elif action == "LIST_USERS_RESPONSE":
                    self.log_message(f"[SERVER] Συνδεδεμένοι χρήστες: {', '.join(payload)}")
                
                elif action == "HISTORY_RESPONSE":
                    self.log_message(f"\n--- ΙΣΤΟΡΙΚΟ ---")
                    if not payload:
                        self.log_message("Κενό ιστορικό.")
                    for msg_data in payload:
                        self.log_message(f"[{msg_data['time']}] {msg_data['sender']}: {msg_data['payload']}")
                    self.log_message("----------------")
                
                
                
                
                
                elif action in ["INFO", "RESPONSE"]:
                    if status == "ERROR":
                        self.log_message(f"[ERROR]: {payload}")
                    else:
                        self.log_message(f"[SERVER]: {payload}")
            except Exception:
                break


    def request_history(self):
        mode = self.msg_type_combo.get()  # Παίρνει την τιμή "Broadcast", "Room" ή "Private"
        target = self.ent_target.get().strip()
        
        if mode == "Room":
            if not self.current_room:
                messagebox.showwarning("Προειδοποίηση", "Δεν είστε σε κάποιο δωμάτιο!")
                return
            pkt = {"msg_id": self.get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": self.username, "target": "ROOM", "payload": self.current_room, "status": None}
        elif mode == "Private":
            if not target:
                messagebox.showwarning("Προειδοποίηση", "Συμπληρώστε το πεδίο 'Προς/Στόχος' για να δείτε τη συνομιλία με τον συγκεκριμένο χρήστη.")
                return
            pkt = {"msg_id": self.get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": self.username, "target": "PRIVATE", "payload": target, "status": None}
        else:
            pkt = {"msg_id": self.get_next_msg_id(), "action": "HISTORY_REQUEST", "sender": self.username, "target": "BROADCAST", "payload": None, "status": None}
            
        try:
            self.client_socket.sendto(json.dumps(pkt).encode('utf-8'), self.server_address)
        except Exception as e:
            self.log_message(f"[ERROR]: Αποτυχία αιτήματος ιστορικού: {e}")



    def send_message(self):
        content = self.ent_msg.get().strip()
        if not content:
            return

        mode = self.msg_type_combo.get()
        target = self.ent_target.get().strip()

        if mode == "Broadcast":
            pkt = {"msg_id": self.get_next_msg_id(), "action": "BROADCAST", "sender": self.username, "target": None, "payload": content, "status": None}
            self.log_message(f"[Εσείς προς όλους]: {content}")
        elif mode == "Room":
            if not self.current_room:
                messagebox.showwarning("Προειδοποίηση", "Δεν είστε σε δωμάτιο! Μπείτε πρώτα από το δεξί μενού.")
                return
            pkt = {"msg_id": self.get_next_msg_id(), "action": "ROOM_MSG", "sender": self.username, "target": self.current_room, "payload": content, "status": None}
            self.log_message(f"[Εσείς στο δωμάτιο {self.current_room}]: {content}")
        elif mode == "Private":
            if not target:
                messagebox.showwarning("Προειδοποίηση", "Πρέπει να γράψετε το username του στόχου στο πεδίο 'Προς/Στόχος'.")
                return
            pkt = {"msg_id": self.get_next_msg_id(), "action": "PRIVATE", "sender": self.username, "target": target, "payload": content, "status": None}
            self.log_message(f"[Εσείς προσωπικό προς {target}]: {content}")

        try:
            self.client_socket.sendto(json.dumps(pkt).encode('utf-8'), self.server_address)
            self.ent_msg.delete(0, tk.END)
        except Exception as e:
            self.log_message(f"[ERROR]: Αποτυχία αποστολής: {e}")

    def join_room(self):
        room = self.ent_room_name.get().strip()
        if not room:
            return
        self.current_room = room
        self.lbl_current_room.config(text=f"Room: {room}")
        pkt = {"msg_id": self.get_next_msg_id(), "action": "JOIN_ROOM", "sender": self.username, "target": room, "payload": None, "status": None}
        self.client_socket.sendto(json.dumps(pkt).encode('utf-8'), self.server_address)

    def request_user_list(self):
        pkt = {"msg_id": self.get_next_msg_id(), "action": "LIST_USERS", "sender": self.username, "target": None, "payload": None, "status": None}
        self.client_socket.sendto(json.dumps(pkt).encode('utf-8'), self.server_address)

    def disconnect_server(self):
        pkt = {"msg_id": self.get_next_msg_id(), "action": "DISCONNECT", "sender": self.username, "target": None, "payload": None, "status": None}
        try:
            self.client_socket.sendto(json.dumps(pkt).encode('utf-8'), self.server_address)
        except:
            pass
        self.client_socket.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.disconnect_server)
    root.mainloop()