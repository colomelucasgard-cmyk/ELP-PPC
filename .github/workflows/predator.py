import socket
import time
import random
import sysv_ipc
import config as c

print("[CLIENT] Démarrage du prédateur...")

# --- 1. Connexion au serveur pour obtenir une position ---
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)# Timeout de 5 secondes pour voir si le serveur répond
        s.connect((c.HOST, c.PORT))
        
        # Réception de la position
        data = s.recv(1024)
        if not data:
            print("[CLIENT] Erreur: Aucune donnée reçue.")
            exit(1)
            
        my_pos = int(data.decode())

except (socket.error, ValueError) as e:
    print(f"[CLIENT] Impossible de rejoindre la simulation: {e}")
    exit(1)

if my_pos == -1:
    print("[CLIENT] Le monde est plein. Fin du processus.")
    exit(0)

print(f"[CLIENT] Position assignée: {my_pos}")

# --- 2. Connexion aux ressources partagées (IPC) ---
try:
    # On se rattache aux ressources existantes créées par env.py
    shm = sysv_ipc.SharedMemory(c.SHM_KEY)
    sem = sysv_ipc.Semaphore(c.SEM_KEY)
except sysv_ipc.ExistentialError:
    print("[CLIENT] Erreur: L'environnement (env.py) n'est pas lancé.")
    exit(1)

# --- 3. Initialisation sur la carte ---
sem.acquire()
try:
    # On écrit l'octet correspondant à un PREDATEUR à la position donnée
    shm.write(bytes([c.PREDATOR]), offset=my_pos)
finally:
    sem.release()

# --- 4. Boucle de Vie ---
try:
    while True:
        time.sleep(random.uniform(0.8, 1.2)) # Vitesse variable

        sem.acquire()
        try:
            # Calcul des coordonnées actuelles
            row = my_pos // c.COLS
            col = my_pos % c.COLS
            
            # Liste des déplacements possibles (Haut, Bas, Gauche, Droite)
            moves = []
            if row > 0: moves.append(my_pos - c.COLS)
            if row < c.LIGNES - 1: moves.append(my_pos + c.COLS)
            if col > 0: moves.append(my_pos - 1)
            if col < c.COLS - 1: moves.append(my_pos + 1)
            
            if moves:
                target = random.choice(moves)
                
                # Lecture de la case cible (1 octet)
                val = shm.read(1, offset=target)
                
                # Si la case est vide (0), on bouge
                if val == bytes([c.EMPTY]):
                    # 1. Effacer ancienne position
                    shm.write(bytes([c.EMPTY]), offset=my_pos)
                    # 2. Ecrire nouvelle position
                    shm.write(bytes([c.PREDATOR]), offset=target)
                    
                    my_pos = target
                    print(f"Déplacement vers {my_pos}")
                else:
                    # Case occupée, on reste sur place
                    pass
        finally:
            sem.release()

except KeyboardInterrupt:
    print("\n[CLIENT] Interruption...")

finally:
    # Nettoyage: on efface notre trace avant de quitter
    try:
        sem.acquire()
        shm.write(bytes([c.EMPTY]), offset=my_pos)
        sem.release()
        print("[CLIENT] predateur retiré de la carte.")
    except:
        pass