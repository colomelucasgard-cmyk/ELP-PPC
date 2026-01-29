import socket
import time
import random
import sysv_ipc
import env as c
import multiprocessing
import sys
import struct
import os

def run_prey(my_slot=None, genes=None):
    # 1. Inscription
    if my_slot is None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((c.HOST, c.PORT))
                data = s.recv(1024)
                if not data: return
                my_slot = int(data.decode())
        except: return

    if my_slot == -1: return

    try:
        shm = sysv_ipc.SharedMemory(c.SHM_KEY)
        sem = sysv_ipc.Semaphore(c.SEM_KEY)
    except: return

    my_pid = os.getpid()

    # Init : J'écris (MON_PID, PREY)
    sem.acquire()
    try:
        packed_data = struct.pack('ii', my_pid, c.PREY)
        shm.write(packed_data, offset=c.OFFSET_POPULATION + (my_slot * c.SIZE_ANIMAL))
    finally:
        sem.release()

    if genes is None:
        genes = {"seuil_H": 7, "seuil_R": 10, "cout_repro": 4, "metabolisme": 0.2}
    
    energie = 5
    age = 0
    age_mort = random.uniform(50, 100)

    try:
        while True:
            age += 1
            energie -= genes["metabolisme"]
            time.sleep(random.uniform(0.5, 1.0))

            if energie < 0 or age > age_mort:
                break 

            # État
            code_actuel = c.PREY
            if energie < genes["seuil_H"]:
                etat = "ACTIVE"
                code_actuel = c.ACTIVE_PREY
            elif energie > 10:
                etat = "PASSIVE"
                code_actuel = c.PREY

            # Interaction
            sem.acquire()
            try:
                # 1. Vérification SURVIE (Est-ce que mon PID est toujours là ?)
                offset_moi = c.OFFSET_POPULATION + (my_slot * c.SIZE_ANIMAL)
                data_moi = shm.read(c.SIZE_ANIMAL, offset=offset_moi)
                pid_lu, type_lu = struct.unpack('ii', data_moi)

                if pid_lu != my_pid:
                    # Mon slot a été écrasé (mis à 0 ou pris par quelqu'un d'autre)
                    # Je suis mort
                    sem.release()
                    return 

                # 2. Update État (Toujours mon PID, mais nouveau Type)
                shm.write(struct.pack('ii', my_pid, code_actuel), offset=offset_moi)

                # 3. Manger
                if etat == "ACTIVE":
                    bytes_herbe = shm.read(c.SIZE_HERBE, offset=c.OFFSET_HERBE)
                    nb_herbe = struct.unpack('>I', bytes_herbe)[0]
                    if nb_herbe > 0:
                        nb_herbe -= 1
                        shm.write(struct.pack('>I', nb_herbe), offset=c.OFFSET_HERBE)
                        energie += 2
            finally:
                sem.release()

            # Reproduction
            if energie > genes["seuil_R"] and random.random() < 0.1:
                child_slot = -1
                sem.acquire()
                try:
                    # Cherche un slot avec PID=0
                    pop_data = shm.read(c.CAPACITY * c.SIZE_ANIMAL, offset=c.OFFSET_POPULATION)
                    for i in range(c.CAPACITY):
                        chunk = pop_data[i*c.SIZE_ANIMAL : (i+1)*c.SIZE_ANIMAL]
                        p, t = struct.unpack('ii', chunk)
                        if p == 0:
                            child_slot = i
                            # On réserve temporairement avec un PID placeholder ou juste le type
                            # Idéalement l'enfant mettra son vrai PID au démarrage
                            # On met un PID temporaire (-1) pour pas qu'on le vole
                            shm.write(struct.pack('ii', -1, c.PREY), offset=c.OFFSET_POPULATION + (i * c.SIZE_ANIMAL))
                            break
                finally:
                    sem.release()

                if child_slot != -1:
                    p = multiprocessing.Process(target=run_prey, args=(child_slot, genes))
                    p.start()
                    energie -= genes["cout_repro"]

    except KeyboardInterrupt: 
        pass
    except sysv_ipc.ExistentialError:
        pass
    finally:
        try:
            sem.acquire()
            offset_moi = c.OFFSET_POPULATION + (my_slot * c.SIZE_ANIMAL)
            # On relit pour être sûr qu'on n'efface pas quelqu'un d'autre
            data = shm.read(c.SIZE_ANIMAL, offset=offset_moi)
            pid_lu, _ = struct.unpack('ii', data)
            if pid_lu == my_pid:
                # On remet à (0, 0)
                shm.write(struct.pack('ii', 0, c.EMPTY), offset=offset_moi)
            sem.release()
        except: 
            pass
        sys.exit(0)

if __name__ == "__main__":
    p = multiprocessing.Process(target=run_prey)
    p.start()
    p.join()