import sysv_ipc
import socket
import threading
import time
import sys
import config as c

# --- 1. Initialisation des Ressources (IPC) ---
try:
    # Création de la mémoire partagée (IPC_CREAT)
    # On initialise tout à 0 (c.EMPTY)
    shm = sysv_ipc.SharedMemory(c.SHM_KEY, sysv_ipc.IPC_CREAT, size=c.LIGNES * c.COLS, mode=0o600) #mode 0o600 = lecture/écriture propriétaire uniquement
    shm.write(b'\x00' * (c.LIGNES * c.COLS))# Initialisation à vide
    
    # Création du sémaphore (Valeur 1 = Mutex)
    sem = sysv_ipc.Semaphore(c.SEM_KEY, sysv_ipc.IPC_CREAT, initial_value=1)
    print("ok(SHM + SEM")

except sysv_ipc.ExistentialError:
    print(" Ressources déjà existantes")
    shm = sysv_ipc.SharedMemory(c.SHM_KEY)
    sem = sysv_ipc.Semaphore(c.SEM_KEY)

#MESSAGE QUEUE
# On calcule la taille nécessaire (Nb cases * 4 octets pour les int)

taille_message = (c.LIGNES * c.COLS * 4) + 128

try:
    # On force la taille max du message à la création
    mq = sysv_ipc.MessageQueue(c.MQ_KEY, sysv_ipc.IPC_CREAT, max_message_size=taille_message)
    print(f"✅ Message Queue créée (Taille max: {taille_message} octets).")
except sysv_ipc.ExistentialError:
    mq = sysv_ipc.MessageQueue(c.MQ_KEY)
    print("⚠️ Connexion à la MQ existante.")

# --- 2. Serveur Socket (Thread) ---
def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((c.HOST, c.PORT))
        s.listen()
        print(f"Serveur écoute sur {c.PORT}...")

        while True:
            try:
                client, addr = s.accept()
                print(f"Demande d'entrée de {addr}", flush=True) #flush pour debug

                pos = -1 # Par défaut: pas de place

                # --- Section Critique ---
                sem.acquire()
                try:
                    # Lecture de toute la carte
                    grid = shm.read()
                    # Recherche du premier octet vide (0)
                    pos = grid.find(bytes([c.EMPTY]))
                except Exception as e:
                    print(f"Erreur lecture mémoire: {e}")
                finally:
                    sem.release()
            

                # Envoi de la réponse (Position ou -1)
                client.sendall(str(pos).encode())
                client.close()

            except Exception as e:
                print(f" Erreur socket: {e}")

# Lancement du serveur en arrière-plan
t = threading.Thread(target=server, daemon=True)
t.start()

# --- 3. Boucle Principale (Affichage) ---
print("Simulation en cours")

try:
    while True:
        # A. On lit la mémoire (snapshot)
        # On protège la lecture pour ne pas lire une grille à moitié modifiée
        sem.acquire()
        grid_data = shm.read()
        sem.release()

        # B. On envoie les données brutes dans la Message Queue
        # type=1 : On décide que le type 1 correspond à une "frame" vidéo
        try:
            # Note : send est bloquant si la file est pleine. 
            # block=False permet d'éviter que env ne gèle si display n'est pas lancé.
            mq.send(grid_data, type=1, block=False)
        except sysv_ipc.BusyError:
            # La file est pleine (display est trop lent ou absent), on saute cette image
            pass

        time.sleep(0.5) # Cadence d'envoi


except KeyboardInterrupt:
    print("Arrêt de la simulation.")
    # Nettoyage propre
    try:
        shm.remove()
        sem.remove()
        mq.remove()
        print("nettoyage ok")
    except:
        pass