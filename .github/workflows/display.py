import sysv_ipc
import sys
import os
import env as c
import select
import time

# --- Configuration Visuelle ---
CURSOR_HOME = '\033[H'
SYMBOLS = {
    c.EMPTY: " . ",
    c.PREY: " 🐑",
    c.PREDATOR: " 🐺",
    c.GRASS: " 🌿"
}

print("📺 Démarrage du Display (Mode Message Queue)...")

# 1. Connexion à la Queue (et seulement à la queue)
try:
    mq = sysv_ipc.MessageQueue(c.MQ_KEY)
    print("Connecté à la file de messages.")
except sysv_ipc.ExistentialError:
    print("Erreur : env.py n'est pas lancé (pas de MessageQueue trouvée).")
    sys.exit(1)

# Fonction de dessin (inchangée)
def render_grid(grid_bytes):
    output = "╔" + "═══" * c.COLS + "╗\n"
    for i in range(c.LIGNES):
        output += "║"
        for j in range(c.COLS):
            idx = i * c.COLS + j
            # Attention : grid_bytes vient de la MQ, c'est un bytes pur
            val = grid_bytes[idx]
            output += SYMBOLS.get(val, " ? ")
        output += "║\n"
    output += "╚" + "═══" * c.COLS + "╝"
    
    nb_prey = grid_bytes.count(bytes([c.PREY]))
    nb_pred = grid_bytes.count(bytes([c.PREDATOR]))
    output += f"\n📨 Reçu via MQ | 🐑: {nb_prey} | 🐺: {nb_pred} "
    return output

# 2. Boucle de lecture
try:
    # Nettoyage terminal
    os.system('clear') 
    
    while True:
        # GESTION CLAVIER NON-BLOQUANTE
        # On demande au système : "Y a-t-il quelque chose sur l'entrée standard (stdin) ?"
        # Le timeout à 0 signifie "vérifie et rend la main tout de suite"
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            cmd = sys.stdin.readline().strip().lower()
            
            if cmd == 's':
                # Envoi de l'ordre à Env (Type 2 pour les commandes)
                try:
                    mq.send(b"DROUGHT", type=2)
                    print("\n[Commande] Sécheresse basculée !") # Feedback visuel
                except sysv_ipc.BusyError:
                    pass
            elif cmd == 'q':
                mq.send(b"STOP", type=2)
                break

        # --- B. RÉCEPTION IMAGE (NON-BLOQUANT) ---
        try:
            # block=False est CRUCIAL ici. 
            # Si pas de message, ça lève une erreur BusyError au lieu de figer l'écran.
            message, t = mq.receive(type=1, block=False)
            
            # Si on a reçu un message, on dessine
            frame = render_grid(message)
            sys.stdout.write(CURSOR_HOME + frame)
            sys.stdout.flush()
            
        except sysv_ipc.BusyError:
            # Pas de nouvelle image pour l'instant, on ne fait rien
            pass

        # Petite pause pour ne pas utiliser 100% du CPU inutilement
        time.sleep(0.05)

except sysv_ipc.ExistentialError:
    print("\n La queue a disparu (env.py s'est arrêté ?)")
except KeyboardInterrupt:
    print("\n👋 Arrêt du display.")
