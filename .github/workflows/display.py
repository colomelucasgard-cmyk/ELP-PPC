import sysv_ipc
import sys
import os
import config as c

# --- Configuration Visuelle ---
CURSOR_HOME = '\033[H'
SYMBOLS = {
    c.EMPTY: " . ",
    c.PREY: " 🐑",
    c.PREDATOR: " 🐺"
}

print("📺 Démarrage du Display (Mode Message Queue)...")

# 1. Connexion à la Queue (et seulement à la queue)
try:
    mq = sysv_ipc.MessageQueue(c.MQ_KEY)
    print("✅ Connecté à la file de messages.")
except sysv_ipc.ExistentialError:
    print("❌ Erreur : env.py n'est pas lancé (pas de MessageQueue trouvée).")
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
        # A. Réception bloquante
        # Le display attend qu'un message arrive. Il ne consomme pas de CPU tant que env n'envoie rien.
        # type=1 pour ne lire que les frames (si jamais on ajoute d'autres types de messages plus tard)
        message, t = mq.receive(type=1)
        
        # message est de type 'bytes', c'est exactement notre grille !
        
        # B. Rendu
        frame = render_grid(message)
        
        # C. Affichage fluide
        sys.stdout.write(CURSOR_HOME + frame)
        sys.stdout.flush()

except sysv_ipc.ExistentialError:
    print("\n❌ La queue a disparu (env.py s'est arrêté ?)")
except KeyboardInterrupt:
    print("\n👋 Arrêt du display.")