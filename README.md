# UDP Chat System with SQLite3 (Python 3.x)

## Περιγραφή

Το **UDP Chat System** αποτελεί την ολοκληρωμένη υλοποίηση της ομαδικής εργασίας για το μάθημα **Δίκτυα Υπολογιστών του τμήματος Διοίκησης Επιχειρήσεων και Οργανισμών του Εθνικού και Καποδιστριακού Πανεπιστημίου Αθηνών (Εαρινό Εξάμηνο 2026)**.

Πρόκειται για ένα σύστημα ανταλλαγής μηνυμάτων σε πραγματικό χρόνο (**Real-Time Chat**) βασισμένο στο πρωτόκολλο **UDP**, το οποίο ακολουθεί αρχιτεκτονική **Client–Server**.

Παρότι το UDP είναι **connectionless** και δεν παρέχει αξιοπιστία ή διαχείριση συνδέσεων, η εφαρμογή υλοποιεί τους απαραίτητους μηχανισμούς σε επίπεδο εφαρμογής (Application Layer), όπως παρακολούθηση χρηστών, heartbeat, timeout και διαχείριση ιστορικού συνομιλιών.

---

# Βασικά Χαρακτηριστικά

- UDP Client–Server αρχιτεκτονική
- Multi-threaded Server
- Command Line Client (CLI)
- Graphical User Interface (GUI) με Tkinter
- Global Chat (Broadcast)
- Private Messages
- Chat Rooms
- Λίστα Online Χρηστών
- Persistent αποθήκευση ιστορικού σε SQLite3
- Heartbeat (PING)
- Αυτόματο Timeout ανενεργών χρηστών
- Thread-safe πρόσβαση στις κοινόχρηστες δομές
- JSON-based communication protocol

---

# Αρχιτεκτονική Συστήματος

Το σύστημα αποτελείται από τρία βασικά μέρη:

## 1. UDP Server

Ο server είναι υπεύθυνος για:

- διαχείριση των συνδεδεμένων χρηστών
- δρομολόγηση των μηνυμάτων
- διαχείριση των chat rooms
- αποθήκευση ιστορικού στη βάση SQLite
- έλεγχο heartbeat
- αυτόματο timeout ανενεργών clients

Ο Server είναι **multi-threaded** ώστε να μπορεί να εξυπηρετεί ταυτόχρονα πολλούς χρήστες.

---

## 2. CLI Client

Ελαφρύς client γραμμής εντολών.

Υποστηρίζει όλες τις λειτουργίες του συστήματος μέσω ειδικών εντολών.

---

## 3. GUI Client

Υλοποιήθηκε με **Tkinter** και προσφέρει:

- εύκολη σύνδεση
- εμφάνιση συνομιλιών
- αποστολή μηνυμάτων
- λήψη μηνυμάτων σε ξεχωριστό thread χωρίς να "παγώνει" το περιβάλλον

---

# Πρωτόκολλο Επικοινωνίας

Η επικοινωνία πραγματοποιείται αποκλειστικά μέσω UDP sockets.

Όλα τα πακέτα ανταλλάσσονται σε μορφή JSON.

Παράδειγμα:

```json
{
    "msg_id": 42,
    "action": "BROADCAST",
    "sender": "user1",
    "target": "all",
    "payload": "Hello!",
    "status": "SUCCESS"
}
```

## Πεδία

| Πεδίο | Περιγραφή |
|--------|-----------|
| `msg_id` | Μοναδικός αριθμός μηνύματος |
| `action` | Τύπος ενέργειας |
| `sender` | Username αποστολέα |
| `target` | Παραλήπτης ή chat room |
| `payload` | Περιεχόμενο μηνύματος |
| `status` | SUCCESS ή ERROR |

---

# Υποστηριζόμενες Ενέργειες (Actions)

| Action | Περιγραφή |
|---------|-----------|
| CONNECT | Σύνδεση χρήστη |
| DISCONNECT | Αποσύνδεση |
| BROADCAST | Μήνυμα προς όλους |
| PRIVATE | Ιδιωτικό μήνυμα |
| JOIN_ROOM | Είσοδος σε chat room |
| ROOM_MSG | Μήνυμα στο δωμάτιο |
| LIST_USERS | Λίστα online χρηστών |
| HISTORY_REQUEST | Ανάκτηση ιστορικού |
| PING | Heartbeat |

---

# Μηχανισμοί του Συστήματος

## Multi-threading

Ο Server δημιουργεί ξεχωριστά threads ώστε να μπορεί να επεξεργάζεται πολλαπλά UDP datagrams ταυτόχρονα.

Για την προστασία των κοινόχρηστων δομών χρησιμοποιείται:

```python
threading.Lock()
```

ώστε να αποφεύγονται race conditions.

---

## Heartbeat (Keep Alive)

Κάθε client αποστέλλει αυτόματα:

```
PING
```

ανά **30 δευτερόλεπτα**.

Ο Server ενημερώνει το πεδίο:

```
last_seen
```

για κάθε χρήστη.

---

## Automatic Timeout

Daemon thread του Server ελέγχει περιοδικά τους χρήστες.

Εάν κάποιος χρήστης δεν επικοινωνήσει για:

```
300 δευτερόλεπτα (5 λεπτά)
```

θεωρείται αποσυνδεδεμένος και:

- αφαιρείται από τους online users
- αποχωρεί από τα rooms
- αποδεσμεύονται οι πόροι του

---

## Persistent Chat History

Όλα τα μηνύματα αποθηκεύονται στη βάση:

```
chat_history.db
```

Υποστηρίζονται:

- Global chat
- Room messages
- Private messages

Κατά την ανάκτηση ιστορικού πραγματοποιείται έλεγχος εξουσιοδότησης (authorization), ώστε κάθε χρήστης να μπορεί να δει μόνο τα μηνύματα που δικαιούται.

---

# Δομή Repository

```
.
├── server.py
├── client.py
├── gui_client.py
├── chat_history.db
├── README.md
└── Tests Report.pdf
```

## Περιγραφή

| Αρχείο | Περιγραφή |
|---------|-----------|
| `server.py` | UDP Server |
| `client.py` | CLI Client |
| `gui_client.py` | GUI Client |
| `chat_history.db` | SQLite Database |
| `Tests Report.pdf` | Αναφορά δοκιμών |

---

# Προαπαιτούμενα

- Python 3.8 ή νεότερη
- SQLite3 (ενσωματωμένη στην Python)
- Tkinter (για τον GUI Client)

Σε Ubuntu / Debian:

```bash
sudo apt update
sudo apt install python3-tk -y
```

---

# Εκτέλεση

## Εκκίνηση Server

```bash
python3 server.py
```

Ο Server ακούει στην προεπιλεγμένη θύρα:

```
0.0.0.0:12345
```

---

## GUI Client

```bash
python3 gui_client.py
```

Συμπληρώστε:

- Username
- IP Server
- Port (12345)

---

## CLI Client

```bash
python3 client.py
```

---

# Εντολές CLI

| Εντολή | Περιγραφή |
|---------|-----------|
| `#join <room>` | Είσοδος σε δωμάτιο |
| `@room <μήνυμα>` | Μήνυμα στο τρέχον room |
| `@all <μήνυμα>` | Broadcast προς όλους |
| `@username <μήνυμα>` | Private message |
| `#list` | Online users |
| `#history` | Τελευταία μηνύματα |
| `#history private` | Όλα τα προσωπικά μηνύματα |
| `#history @username` | Ιστορικό συνομιλίας |
| `#exit` | Αποσύνδεση |

---

# Βάση Δεδομένων

Η εφαρμογή χρησιμοποιεί SQLite3 για αποθήκευση:

- Global messages
- Room messages
- Private messages
- Metadata αποστολέα
- Metadata παραλήπτη
- Chat rooms
- Χρονικές σημάνσεις (timestamps)

Η βάση δημιουργείται αυτόματα κατά την πρώτη εκτέλεση.

---

# Θέματα Ασφάλειας

Το σύστημα περιλαμβάνει βασικούς μηχανισμούς προστασίας:

- Authorization κατά την ανάκτηση ιστορικού
- Automatic cleanup ανενεργών clients

---

# Χρήση Εργαλείων Τεχνητής Νοημοσύνης

Κατά την ανάπτυξη του έργου χρησιμοποιήθηκαν εργαλεία Τεχνητής Νοημοσύνης (LLMs) αποκλειστικά ως βοηθητικά μέσα για:

- υποστήριξη στην εγκατάσταση εξαρτήσεων (π.χ. `python3-tk`)
- βελτίωση της τεκμηρίωσης (README.md) του έργου
- μορφοποίηση και οργάνωση του pdf των αποτελεσμάτων δοκιμών (βλ. Tests Report.pdf)
- αναδιατύπωση περιγραφών και τεχνικής τεκμηρίωσης
- σύνταξη και παραγωγή σε μορφή PDF του Εγγράφου Περιγραφής Πρωτοκόλλου (Protocol Description Report)

Ο σχεδιασμός, η υλοποίηση και η λειτουργικότητα του συστήματος αναπτύχθηκαν από την ομάδα του έργου.

---

# Prompt Videos

## SSH Server Prompt Video
