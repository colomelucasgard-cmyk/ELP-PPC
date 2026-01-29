import socket
import time
import random
import sysv_ipc
import env as c
import multiprocessing
import sys
import struct
import os

def run_predator(my_slot=None, genes=None):
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

    sem.acquire()
    try:
        shm.write(struct.pack('ii', my_pid, c.PREDATOR), offset=c.OFFSET_POPULATION + (my_slot * c.SIZE_ANIMAL))
    finally:
        sem.release()

    if genes is None:
        genes = {"seuil_H": 7, "seuil_R": 11, "cout_repro": 6, "metabolisme": 0.15}

    energie = 8
    etat = "PASSIVE"
    age = 0
    age_mort = random.uniform(60, 90)

    try:
        while True:
            age += 1
            energie -= genes["metabolisme"]
            time.sleep(random.uniform(0.5, 1.0))

            if energie < 0 or age > age_mort:
                break

            if energie < genes["seuil_H"]:
                etat = "ACTIVE"
            else:
                etat = "PASSIVE"

            if etat == "ACTIVE":
                sem.acquire()
                try:
                    # Scan population
                    pop_data = shm.read(c.CAPACITY * c.SIZE_ANIMAL, offset=c.OFFSET_POPULATION)
                    
                    target_slot = -1
                    
                    # On cherche une proie active
                    for i in range(c.CAPACITY):
                        chunk = pop_data[i*c.SIZE_ANIMAL : (i+1)*c.SIZE_ANIMAL]
                        pid_lu, type_lu = struct.unpack('ii', chunk)
                        
                        if type_lu == c.ACTIVE_PREY:
                            target_slot = i
                            # Mange ! -> On écrit (0, 0) à sa place
                            # La proie verra que son PID a disparu et s'arrêtera
                            offset_target = c.OFFSET_POPULATION + (i * c.SIZE_ANIMAL)
                            shm.write(struct.pack('ii', 0, c.EMPTY), offset=offset_target)
                            energie += 5
                            # print(f"[PRED {my_pid}] Mange PID {pid_lu}")
                            break 
                finally:
                    sem.release()

            # Reproduction
            if energie > genes["seuil_R"] and random.random() < 0.02:
                child_slot = -1
                sem.acquire()
                try:
                    pop_data = shm.read(c.CAPACITY * c.SIZE_ANIMAL, offset=c.OFFSET_POPULATION)
                    for i in range(c.CAPACITY):
                        chunk = pop_data[i*c.SIZE_ANIMAL : (i+1)*c.SIZE_ANIMAL]
                        p, t = struct.unpack('ii', chunk)
                        if p == 0:
                            child_slot = i
                            shm.write(struct.pack('ii', -1, c.PREDATOR), offset=c.OFFSET_POPULATION + (i * c.SIZE_ANIMAL))
                            break
                finally:
                    sem.release()

                if child_slot != -1:
                    p = multiprocessing.Process(target=run_predator, args=(child_slot, genes))
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
            data = shm.read(c.SIZE_ANIMAL, offset=offset_moi)
            pid_lu, _ = struct.unpack('ii', data)
            if pid_lu == my_pid:
                shm.write(struct.pack('ii', 0, c.EMPTY), offset=offset_moi)
            sem.release()
        except: 
            pass
        sys.exit(0)

if __name__ == "__main__":
    p = multiprocessing.Process(target=run_predator)
    p.start()
    p.join()