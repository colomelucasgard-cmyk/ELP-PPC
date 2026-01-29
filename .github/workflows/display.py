import sysv_ipc
import sys
import os
import select
import time
import signal
import subprocess
import struct

# --- CONSTANTES ---
MQ_KEY = 9500
PREY = 1
PREDATOR = 2
ACTIVE_PREY = 4 
SIZE_ANIMAL = 8

PID_ENV = None
CURSOR_HOME = '\033[H'

def lancer_simulation():
    if not os.path.exists("prey.py") or not os.path.exists("predator.py"):
        print("Fichiers introuvables.")
        return
    try:
        n_preys = int(input("Proies ? (20): ") or 20)
        n_predators = int(input("Prédateurs ? (5): ") or 5)
        
        for _ in range(n_predators):
            subprocess.Popen([sys.executable, "predator.py"])
            time.sleep(0.05)
        for _ in range(n_preys):
            subprocess.Popen([sys.executable, "prey.py"])
            time.sleep(0.05)
    except: pass

def render_dashboard(data_bytes):
    # Header Herbe
    nb_herbe = struct.unpack('>I', data_bytes[:4])[0]
    
    # Population (tout sauf les 4 premiers et le dernier octet)
    pop_bytes = data_bytes[4:-1]
    secheresse_byte = data_bytes[-1]
    
    nb_prey = 0
    nb_active_prey = 0
    nb_pred = 0
    
    # On parcourt par bloc de 8 octets
    total_slots = len(pop_bytes) // SIZE_ANIMAL
    
    for i in range(total_slots):
        chunk = pop_bytes[i*SIZE_ANIMAL : (i+1)*SIZE_ANIMAL]
        pid, type_anim = struct.unpack('ii', chunk)
        
        if pid != 0: # Si Slot occupé
            if type_anim == PREY: nb_prey += 1
            elif type_anim == ACTIVE_PREY: nb_active_prey += 1
            elif type_anim == PREDATOR: nb_pred += 1

    etat_secheresse = "☀️  ON" if secheresse_byte == 1 else "💧 OFF"

    out = "╔════════════════════════════════════╗\n"
    out += "║      THE CIRCLE OF LIFE (PIDs)     ║\n"
    out += "╠════════════════════════════════════╣\n"
    out += f"║ 🌿 Herbe            : {nb_herbe:5d}        ║\n"
    out += f"║ 🔥 Sécheresse       : {etat_secheresse}       ║\n"
    out += "╠════════════════════════════════════╣\n"
    out += f"║ 🐑 Proies Totales   : {nb_prey + nb_active_prey:5d}        ║\n"
    out += f"║    - Passives       : {nb_prey:5d}        ║\n"
    out += f"║    - Actives        : {nb_active_prey:5d}        ║\n"
    out += "╠════════════════════════════════════╣\n"
    out += f"║ 🐺 Prédateurs       : {nb_pred:5d}        ║\n"
    out += "╚════════════════════════════════════╝\n"
    out += "Commandes: 's' = Sécheresse | 'q' = Quitter"
    return out

if __name__ == "__main__":
    try:
        mq = sysv_ipc.MessageQueue(MQ_KEY)
    except:
        print("Env non lancé.")
        sys.exit(1)

    lancer_simulation()
    os.system('clear')

    try:
        while True:
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == 's' and PID_ENV: os.kill(PID_ENV, signal.SIGUSR1)
                elif cmd == 'q': 
                    mq.send(b"STOP", type=2)
                    break

            try:
                msg, _ = mq.receive(type=3, block=False)
                PID_ENV = int(msg.decode())
            except: pass

            try:
                msg, _ = mq.receive(type=1, block=False)
                sys.stdout.write(CURSOR_HOME + render_dashboard(msg))
                sys.stdout.flush()
            except: pass

            time.sleep(0.1)

    except KeyboardInterrupt: pass
