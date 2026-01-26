import sysv_ipc
import socket
import threading
import time
import random 
import signal
import os


# Paramètres du monde
LIGNES = 20
COLS = 40
SHM_KEY = 1234       # Clé pour la mémoire partagée
SEM_KEY = 5678       # Clé pour le sémaphore (verrou)

# Paramètres réseau
HOST = "127.0.0.1"
PORT = 7777

# Codes pour la carte
EMPTY = 0
PREY = 1
PREDATOR = 2
GRASS = 3 
ACTIVE_PREY = 4 #le predateur ne chasse que des proies actives

MQ_KEY = 9500

BoolSecheresse = False
TriggerChicxulub = False


# --- Signal pour la secheresse ---

def handler_secheresse(sig, frame):
    global BoolSecheresse
    BoolSecheresse = not BoolSecheresse
    print(f"\nDrought activated: {BoolSecheresse}")

def handler_chicxulub(sig,frame):
    global TriggerChicxulub
    TriggerChicxulub = not TriggerChicxulub
    print(f"\nastéroïde !!!! : {TriggerChicxulub}")

def secheresse_auto():
    global BoolSecheresse

    BoolSecheresse = not BoolSecheresse
    if BoolSecheresse :
        Etiquette = "SECHERESSE AUTO ACTIVE"
    else :
        Etiquette = "SECHERESSE AUTO INACTIVE"
    print(f"{Etiquette}")

    cycle = random.uniform(10,20)
    timer = threading.Timer(cycle,secheresse_auto)
    timer.daemon = True
    timer.start()

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

    # --- creation du signal secheresse ---

    signal.signal(signal.SIGUSR1, handler_secheresse)

    # --- creation du signal Chicxulub
    signal.signal(signal.SIGUSR2,handler_chicxulub)

    # --- creation de la secheresse auto ---
    secheresse_auto()
    # -- Constantes modulables par display

    ProbaHerbe =  0.004


    try:
        # Création de la mémoire partagée (IPC_CREAT)
        # On initialise tout à 0 (EMPTY)
        shm = sysv_ipc.SharedMemory(SHM_KEY, sysv_ipc.IPC_CREAT, size=LIGNES * COLS, mode=0o600) #mode 0o600 = lecture/écriture propriétaire uniquement
        shm.write(b'\x00' * (LIGNES * COLS))# Initialisation à vide
        
        # Création du sémaphore (Valeur 1 = Mutex comme ici)
        sem = sysv_ipc.Semaphore(SEM_KEY, sysv_ipc.IPC_CREAT, initial_value=1)
        print("ok(SHM + SEM)")

    except sysv_ipc.ExistentialError:
        print(" Ressources déjà existantes")
        shm = sysv_ipc.SharedMemory(SHM_KEY)
        sem = sysv_ipc.Semaphore(SEM_KEY)

    # MESSAGE QUEUE
    taille_message = (LIGNES * COLS * 4) + 128

    try:
        mq = sysv_ipc.MessageQueue(MQ_KEY)
        # Si elle existe, on la détruit
        mq.remove()
        print("Ancienne queue supprimée")
    except sysv_ipc.ExistentialError:
        pass

    # Maintenant on crée la neuve
    mq = sysv_ipc.MessageQueue(MQ_KEY, sysv_ipc.IPC_CREAT, max_message_size=taille_message)
    print(f" Message Queue créée (Taille max: {taille_message} octets).")

    #Serveur Socket/Thread
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
                        print(f"Erreur lecture memoire:{e}")
                    finally:
                        sem.release()
                

                    # Envoi de la réponse (Position ou -1)
                    client.sendall(str(pos).encode()) #plutot que le socket.send classique, je veux envoyer tout me buffer
                    client.close()

                except Exception as e:
                    print(f" Erreur socket: {e}")

    # Lancement du serveur en arrière-plan
    t = threading.Thread(target=server, daemon=True)
    t.start()

    #Boucle principale
    print("Simulation en cours")

    try:
        while True:
            # On lit la mémoire
            # On protège la lecture pour ne pas lire une grille à moitié modifiée

            try: #On ne doit pas envoyer le drought activation par mq, mais j'ai laissé le stop
                message,t = mq.receive(type = 2, block = False)
                '''if message == b"DROUGHT":
                    BoolSecheresse = not BoolSecheresse #Pour basculer et annuler
                    print(f"Drought activated")'''
                if message == b"STOP":
                    break
            except sysv_ipc.BusyError:
            
                pass

            sem.acquire()
            try:
                raw_data = shm.read()

                if not TriggerChicxulub:
                    grid = bytearray(raw_data)
                    changed = False
                

                if not BoolSecheresse:
                    grid = bytearray(raw_data)#conversion du byte array
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
            # type=1 : On décide que le type 1 = envoi de la grille (= frame)
            try:
                # block=False permet d'éviter que env ne freeze pas si display n'est pas lancé.
                mq.send(str(os.getpid()).encode(), type=3, block = False) #envoi du pid pour le signal
                
                mq.send(grid_data, type=1, block=False) # type=1 : On décide que le type 1 = envoi de la grille (= frame)
            except sysv_ipc.BusyError:
                # La file est pleine (display est trop lent ou absent), on saute cette image
                pass

            time.sleep(0.5) # Cadence d'envoi


    except KeyboardInterrupt:
        print("Arrêt de la simulation.")
    
    finally :
        #nettoyage propre
        print("Nettoyage")
        try:
            shm.remove()
            sem.remove()
            mq.remove()
            print("Tout est nettoyé.")
        except:
            pass
