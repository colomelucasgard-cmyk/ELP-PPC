import sysv_ipc
import socket
import threading
import time
import random 

# Paramètres du Monde
LIGNES = 20
COLS = 20
SHM_KEY = 1234       # Clé pour la mémoire partagée
SEM_KEY = 5678       # Clé pour le sémaphore (verrou)

# Paramètres Réseau
HOST = "127.0.0.1"
PORT = 7777

# Codes pour la carte
EMPTY = 0
PREY = 1
PREDATOR = 2
GRASS = 3 

MQ_KEY = 9500

# --- Initialisation des ressources ---

if __name__ == "__main__":


    print("Nettoyage avant de commencer")
    try:
        sysv_ipc.SharedMemory(SHM_KEY).remove()
        print("- SHM effacée")
    except: pass
    try:
        sysv_ipc.Semaphore(SEM_KEY).remove()
        print("- SEM effacé")
    except: pass
    try:
        sysv_ipc.MessageQueue(MQ_KEY).remove()
        print("- MQ effacée")
    except: pass

    # -- Constantes modulables par display
    BoolSecheresse = False
    ProbaHerbe =  0.005


    try:
        # Création de la mémoire partagée (IPC_CREAT)
        # On initialise tout à 0 (EMPTY)
        shm = sysv_ipc.SharedMemory(SHM_KEY, sysv_ipc.IPC_CREAT, size=LIGNES * COLS, mode=0o600) #mode 0o600 = lecture/écriture propriétaire uniquement
        shm.write(b'\x00' * (LIGNES * COLS))# Initialisation à vide
        
        # Création du sémaphore (Valeur 1 = Mutex)
        sem = sysv_ipc.Semaphore(SEM_KEY, sysv_ipc.IPC_CREAT, initial_value=1)
        print("ok(SHM + SEM)")

    except sysv_ipc.ExistentialError:
        print(" Ressources déjà existantes")
        shm = sysv_ipc.SharedMemory(SHM_KEY)
        sem = sysv_ipc.Semaphore(SEM_KEY)

    # MESSAGE QUEUE
    taille_message = (LIGNES * COLS * 4) + 128

    try:
        # On essaie d'abord de se connecter pour voir si elle existe
        mq = sysv_ipc.MessageQueue(MQ_KEY)
        # Si elle existe, on la détruit pour être sûr d'avoir les bons paramètres
        mq.remove()
        print("Ancienne queue supprimée")
    except sysv_ipc.ExistentialError:
        pass

    # Maintenant on crée la neuve
    mq = sysv_ipc.MessageQueue(MQ_KEY, sysv_ipc.IPC_CREAT, max_message_size=taille_message)
    print(f"✅ Message Queue créée (Taille max: {taille_message} octets).")

    # --- 2. Serveur Socket (Thread) ---
    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            print(f"Serveur écoute sur {PORT}...")

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
                        pos = grid.find(bytes([EMPTY]))
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

            try:
                message,t = mq.receive(type = 2, block = False)
                if message == b"DROUGHT":
                    BoolSecheresse = not BoolSecheresse #Pour basculer et annuler
                    print(f"Drought activated")
                elif message == b"STOP":
                    break
            except sysv_ipc.BusyError:
            
                pass

            sem.acquire()
            try:
                raw_data = shm.read()

                if not BoolSecheresse:
                    grid = bytearray(raw_data)
                    changed = False #Booléen pour voir si quelque chose a changé

                    for i in range(len(grid)):
                        #index = random.randint(0,LIGNES*COLS-1)#Une case au hasard fera pousser de l'herbe
                        if grid[i] == EMPTY and random.random() < ProbaHerbe:
                            grid[i] = GRASS
                            changed = True
                    if changed :
                        shm.write(grid)
                        raw_data = bytes(grid ) #on reconvertit
                grid_data = raw_data
            finally:
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
