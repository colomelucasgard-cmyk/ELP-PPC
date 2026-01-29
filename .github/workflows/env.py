import sysv_ipc
import socket
import threading
import time
import random 
import signal
import os
import struct

# --- CONFIGURATION ---
CAPACITY = 100 
# Structure d'un animal : PID (4 bytes) + TYPE (4 bytes) = 8 bytes
SIZE_ANIMAL = 8 

OFFSET_HERBE = 0
SIZE_HERBE = 4
OFFSET_POPULATION = 4
# Taille totale = 4 octets (Herbe) + (100 * 8 octets)
SHM_SIZE = SIZE_HERBE + (CAPACITY * SIZE_ANIMAL)

SHM_KEY = 1234
SEM_KEY = 5678
MQ_KEY = 9500
HOST = "127.0.0.1"
PORT = 7777

# Codes Types
EMPTY = 0
PREY = 1
PREDATOR = 2
ACTIVE_PREY = 4 

BoolSecheresse = False

# --- Helpers ---
def lire_herbe(shm):
    return struct.unpack('>I', shm.read(SIZE_HERBE, offset=OFFSET_HERBE))[0]

def ecrire_herbe(shm, valeur):
    shm.write(struct.pack('>I', valeur), offset=OFFSET_HERBE)

def handler_secheresse(sig, frame):
    global BoolSecheresse
    BoolSecheresse = not BoolSecheresse
    print(f"\n[ENV] Sécheresse: {BoolSecheresse}")

# --- Init ---
if __name__ == "__main__":
    print("Initialisation avec PIDs...")
    try: 
        sysv_ipc.SharedMemory(SHM_KEY).remove(); 
    except: 
        pass
    try: 
        sysv_ipc.Semaphore(SEM_KEY).remove(); 
    except: 
        pass
    try: 
        sysv_ipc.MessageQueue(MQ_KEY).remove(); 
    except: 
        pass

    signal.signal(signal.SIGUSR1, handler_secheresse)

    try:
        shm = sysv_ipc.SharedMemory(SHM_KEY, sysv_ipc.IPC_CREAT, size=SHM_SIZE, mode=0o600)
        ecrire_herbe(shm, 50)
        
        # Initialisation de la population avec des couples (0, 0) partout
        # 'ii' signifie deux entiers (Integer, Integer)
        empty_slot = struct.pack('ii', 0, EMPTY)
        shm.write(empty_slot * CAPACITY, offset=OFFSET_POPULATION)
        
        sem = sysv_ipc.Semaphore(SEM_KEY, sysv_ipc.IPC_CREAT, initial_value=1)
        print("Ressources IPC créées.")
    except sysv_ipc.ExistentialError:
        print("Connexion aux ressources existantes.")
        shm = sysv_ipc.SharedMemory(SHM_KEY)
        sem = sysv_ipc.Semaphore(SEM_KEY)

    mq = sysv_ipc.MessageQueue(MQ_KEY, sysv_ipc.IPC_CREAT)

    # --- Serveur d'inscription ---
    def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            print(f"Serveur prêt sur {PORT}...")

            while True:
                try:
                    client, addr = s.accept()
                    slot_index = -1
                    sem.acquire()
                    try:
                        # On cherche un slot où le PID est 0 (Vide)
                        # On lit toute la pop
                        pop_data = shm.read(CAPACITY * SIZE_ANIMAL, offset=OFFSET_POPULATION)
                        
                        # On parcourt les slots
                        for i in range(CAPACITY):
                            # On extrait les 8 octets du slot i
                            chunk = pop_data[i*SIZE_ANIMAL : (i+1)*SIZE_ANIMAL]
                            pid, type_anim = struct.unpack('ii', chunk)
                            if pid == 0: # C'est vide
                                slot_index = i
                                break
                    finally:
                        sem.release()
                    
                    client.sendall(str(slot_index).encode())
                    client.close()
                except Exception as e:
                    print(f"Erreur socket: {e}")

    t = threading.Thread(target=server, daemon=True)
    t.start()

    # --- Boucle Monde ---
    try:
        while True:
            try:
                msg, _ = mq.receive(type=2, block=False)
                if msg == b"STOP": break
            except sysv_ipc.BusyError: pass

            sem.acquire()
            try:
                nb_herbe = lire_herbe(shm)
                if not BoolSecheresse and nb_herbe < 1000:
                    nb_herbe += 1
                    ecrire_herbe(shm, nb_herbe)
                
                # Lecture brute pour display
                pop_bytes = shm.read(CAPACITY * SIZE_ANIMAL, offset=OFFSET_POPULATION)
            finally:
                sem.release()

            try:
                mq.send(str(os.getpid()).encode(), type=3, block=False)
                # On envoie tout le bloc binaire
                header = struct.pack('>I', nb_herbe)
                secheresse_byte = b'\x01' if BoolSecheresse else b'\x00'
                mq.send(header + pop_bytes + secheresse_byte, type=1, block=False)
            except sysv_ipc.BusyError: pass

            time.sleep(0.1)
    
    except KeyboardInterrupt: pass
    finally:
        try:
            pop_data = shm.read(CAPACITY * SIZE_ANIMAL, offset=OFFSET_POPULATION)
            sem.release()            
            # On parcourt les slots
            for i in range(CAPACITY):
                # On extrait les 8 octets du slot i
                chunk = pop_data[i*SIZE_ANIMAL : (i+1)*SIZE_ANIMAL]
                pid = struct.unpack('ii', chunk)[0]
                if pid>0:
                    try: os.kill(pid,signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    except Exception as e:
                        print(f"Erreur kill PID{pid}:{e}")
        except Exception as e:
            print(f"Erreur lors du nettoyage des processus : {e}")
        try:    
            shm.remove()
            sem.remove()
            mq.remove()
        except: pass