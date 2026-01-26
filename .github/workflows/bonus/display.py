import sysv_ipc
import sys
import os
# import env as c  <-- SUPPRIMÉ
import select
import time
import signal
import subprocess 

# --- Constantes (copiées de env pour indépendance) ---
LIGNES = 20
COLS = 40
MQ_KEY = 9500

EMPTY = 0
PREY = 1
PREDATOR = 2
GRASS = 3
ACTIVE_PREY = 4

# --- Fonction de lancement ---
def lancer_simulation():
    if not os.path.exists("prey.py") or not os.path.exists("predator.py"):
        print(f"Fichiers introuvables")
        return

    try:
        print(f"Lancement de la simulation")
        n_preys = int(input("nombre de proies ?"))
        n_predators = int(input("nombre de predateurs ?")) # [cite: 2]

        print(f"ok, lancement de {n_preys} proies et {n_predators} predateurs")

        for i in range(n_predators):
            subprocess.Popen([sys.executable,"predator.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
        
        for j in range(n_preys):
            subprocess.Popen([sys.executable,"prey.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
     
        time.sleep(0.1) # [cite: 3]
    
    except ValueError:
        print(f"nombres invalides")

PID_ENV = None #Stockage PID de env

#Configuration Visuelle
CURSOR_HOME = '\033[H' 
SYMBOLS = {
    EMPTY: " . ",   # c.EMPTY remplacé par EMPTY [cite: 4]
    PREY: " 🐑",
    PREDATOR: " 🐺",
    GRASS: " 🌿",
    ACTIVE_PREY: " 🐐"
}


# Connexion Queue
try:
    mq = sysv_ipc.MessageQueue(MQ_KEY) # c.MQ_KEY remplacé [cite: 17]
    print("Connecté à la file de messages.")


except sysv_ipc.ExistentialError:
    print("Erreur : env.py n'est pas lancé (pas de MQ trouvée).")
    sys.exit(1)

# Fonction de dessin (IA)
def render_grid(grid_bytes):
    output = "╔" + "═══" * COLS + "╗\n" # c.COLS remplacé
    for i in range(LIGNES):
        output += "║"
       
        for j in range(COLS): # [cite: 5]
            idx = i * COLS + j
            #gird_bytes = byte pur
            val = grid_bytes[idx]
            output += SYMBOLS.get(val, " ? ")
        output += "║\n"
    output += "╚" + "═══" * COLS + "╝"
    
    nb_prey = grid_bytes.count(bytes([PREY])) # [cite: 6]
    nb_active_prey = grid_bytes.count((bytes([ACTIVE_PREY])))
    nb_pred = grid_bytes.count(bytes([PREDATOR]))
    # Mise à jour du message d'aide pour inclure Chicxulub (optionnel mais utile)
    output += f"\nReçu via MQ | 🐑 + 🐐 : {nb_prey} + {nb_active_prey} | 🐺: {nb_pred}, activez la secheresse (s), Chicxulub (c) ou quittez (q) " # [cite: 7]
    return output

if __name__ == "__main__":
    
    lancer_simulation()
    
    try:
        # Nettoyage terminal
        os.system('clear')
        
        while True:
            # GESTION CLAVIER NON-BLOQUANTE
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]: 
                cmd = sys.stdin.readline().strip().lower() # [cite: 8]
             
                if cmd == 's':
                    # Envoi de l'ordre à Env (Type 2 pour les commandes)
                    try:
                        os.kill(PID_ENV, signal.SIGUSR1)
                        print("\nSécheresse basculée !") # [cite: 10]
                    except (sysv_ipc.BusyError, ProcessLookupError, TypeError):
                        pass
                
                # AJOUT : Commande pour Chicxulub (puisque handler_chicxulub existe dans env)
                elif cmd == 'c':
                    try:
                         os.kill(PID_ENV, signal.SIGUSR2)
                         print("\nAstéroïde en approche !")
                    except (sysv_ipc.BusyError, ProcessLookupError, TypeError):
                        pass

                elif cmd == 'q':
                    mq.send(b"STOP", type=2) # [cite: 11]
                    break
            
            try: #on recoit le pid de env
                msg_pid, t = mq.receive(type=3, block = False)
                PID_ENV = int(msg_pid.decode())
            except sysv_ipc.BusyError: # [cite: 12]
                pass

            #Reception image (normalement pas bloquante)
            try:
                message, t = mq.receive(type=1, block=False) # [cite: 14]
                
                # Si on a reçu un message, on dessine
                frame = render_grid(message)
                sys.stdout.write(CURSOR_HOME + frame) 
                sys.stdout.flush() # [cite: 15]
                
            except sysv_ipc.BusyError:
                # Pas de nouvelle image pour l'instant, on ne fait rien
                pass

            #pause pour protéger cpu (?)
            time.sleep(0.05) # [cite: 16]
    except sysv_ipc.ExistentialError:
        print("\n La queue a disparu (env.py s'est arrêté ?)")
    except KeyboardInterrupt:
        print("\n👋 Arrêt du display.")
