import sysv_ipc
import sys
import os
import env as c #Utile seulement pour les MQ KEY, LIGNES, COLS, à suppr si on veut juste copier les KEYS
import select
import time
import signal
import subprocess #pour ne pas créer d'interdépendances entre les preys et predators

# --- Fonction de lancement ---
def lancer_simulation():
    if not os.path.exists("prey.py") or not os.path.exists("predator.py"):
        print(f"Fichiers introuvables")
        return

    try:
        print(f"Lancement de la simulation")
        n_preys = int(input("nombre de proies ?"))
        n_predators = int(input("nombre de predateurs ?"))

        print(f"ok, lancement de {n_preys} proies et {n_predators} predateurs")

        for i in range(n_predators):
            subprocess.Popen([sys.executable,"predator.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
        
        for j in range(n_preys):
            subprocess.Popen([sys.executable,"prey.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.1)
    
    except ValueError:
        print(f"nombres invalides")

PID_ENV = None #Stockage PID de env

#Configuration Visuelle
CURSOR_HOME = '\033[H' #IA, utile pour le terminal non bloquant 
SYMBOLS = {
    c.EMPTY: " . ",
    c.PREY: " 🐑",
    c.PREDATOR: " 🐺",
    c.GRASS: " 🌿",
    c.ACTIVE_PREY: " 🐐"
}


# Connexion Queue
try:
    mq = sysv_ipc.MessageQueue(c.MQ_KEY)
    print("Connecté à la file de messages.")


except sysv_ipc.ExistentialError:
    print("Erreur : env.py n'est pas lancé (pas de MQ trouvée).")
    sys.exit(1)

# Fonction de dessin (IA)
def render_grid(grid_bytes):
    output = "╔" + "═══" * c.COLS + "╗\n"
    for i in range(c.LIGNES):
        output += "║"
        for j in range(c.COLS):
            idx = i * c.COLS + j
            #gird_bytes = byte pur
            val = grid_bytes[idx]
            output += SYMBOLS.get(val, " ? ")
        output += "║\n"
    output += "╚" + "═══" * c.COLS + "╝"
    
    nb_prey = grid_bytes.count(bytes([c.PREY]))
    nb_active_prey = grid_bytes.count((bytes([c.ACTIVE_PREY])))
    nb_pred = grid_bytes.count(bytes([c.PREDATOR]))
    output += f"\nReçu via MQ | 🐑 + 🐐 : {nb_prey} + {nb_active_prey} | 🐺: {nb_pred}, activez la secheresse (s+Entrée) ou quittez (q+Entrée) ici "
    return output

if __name__ == "__main__":
    
    lancer_simulation()
    
    try:
        # Nettoyage terminal
        os.system('clear')
        
        while True:
            # GESTION CLAVIER NON-BLOQUANTE
            # On demande au système : "Y a-t-il quelque chose sur l'entrée standard (stdin) ?"
            # Le timeout à 0 signifie "vérifie et rend la main tout de suite"
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]: #pareil, pour que ce soit pas bloquant, IA
                cmd = sys.stdin.readline().strip().lower()
                
                if cmd == 's':
                    # Envoi de l'ordre à Env (Type 2 pour les commandes)
                    try:
                        os.kill(PID_ENV, signal.SIGUSR1)
                        print("\nSécheresse basculée !") 
                    except sysv_ipc.BusyError:
                        pass
                elif cmd == 'q':
                    mq.send(b"STOP", type=2)
                    break
            
            try: #on recoit le pid de env
                msg_pid, t = mq.receive(type=3, block = False)
                PID_ENV = int(msg_pid.decode())
            except sysv_ipc.BusyError:
                pass

            #Reception image (normalement pas bloquante)
            try:
                # block=False est CRUCIAL ici. 
                # Si pas de message, ça lève une erreur BusyError au lieu de figer l'écran.
                message, t = mq.receive(type=1, block=False)
                
                # Si on a reçu un message, on dessine
                frame = render_grid(message)
                sys.stdout.write(CURSOR_HOME + frame) #commande non bloquante générée par IA
                sys.stdout.flush() #nettoyage du buffer propre
                
            except sysv_ipc.BusyError:
                # Pas de nouvelle image pour l'instant, on ne fait rien
                pass

            #pause pour protéger cpu (?)
            time.sleep(0.05)
    except sysv_ipc.ExistentialError:
        print("\n La queue a disparu (env.py s'est arrêté ?)")
    except KeyboardInterrupt:
        print("\n👋 Arrêt du display.")
