import socket
import time
import random
import sysv_ipc
import env as c
import multiprocessing
import sys

# --- Fonctions Utilitaires ---

def obtenir_voisins(pos):
    """Renvoie la liste des indices des cases voisines valides."""
    row = pos // c.COLS
    col = pos % c.COLS
    voisins = []
    
    # Haut, Bas, Gauche, Droite
    if row > 0: voisins.append(pos - c.COLS)
    if row < c.LIGNES - 1: voisins.append(pos + c.COLS)
    if col > 0: voisins.append(pos - 1)
    if col < c.COLS - 1: voisins.append(pos + 1)
    
    return voisins

# --- Fonction Principale du Processus (La Vie de la Proie) ---
def run_prey(position_depart=None, genes = None):
    """
    Fonction qui contient toute la logique de vie.
    - Si position_depart est None : C'est une proie initiale (Socket).
    - Si position_depart est défini : C'est un enfant (Spawn direct).
    """
    my_pos = position_depart
    
    # 1. Connexion au serveur (Seulement si pas de position assignée)
    if my_pos is None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((c.HOST, c.PORT))
                data = s.recv(1024)
                if not data: return
                my_pos = int(data.decode())
        except Exception as e:
            print(f"Erreur connexion: {e}")
            return

    if my_pos == -1:
        print("Monde plein.")
        return

    # 2. IPC (Chaque processus doit se connecter aux ressources)
    try:
        shm = sysv_ipc.SharedMemory(c.SHM_KEY)
        sem = sysv_ipc.Semaphore(c.SEM_KEY)
    except sysv_ipc.ExistentialError:
        print("Env non lancé.")
        return

    # 3. Initialisation Carte
    # Si je suis un enfant, mon parent a DÉJÀ réservé ma place.
    # Si je suis une proie initiale (socket), je dois m'écrire.
    if position_depart is None:
        sem.acquire()
        try:
            shm.write(bytes([c.PREY]), offset=my_pos)
        finally:
            sem.release()

    print(f"[PROIE {multiprocessing.current_process().pid}] Née en {my_pos}")

    if genes is None: #dico pour mimer la selection naturelle
        genes = {
            "seuil_H": 7,
            "seuil_R": 7,
            "cout_repro": 4,
            "seuil_satiete": 12,
            "metabolisme": 0.1 # Vitesse à laquelle l'énergie baisse
        }
    
    # On unpack les gènes dans des variables locales pour simplifier l'usage
    seuil_H = genes["seuil_H"]
    seuil_satiete = genes["seuil_satiete"]
    cout_reproduction = genes["cout_repro"]
    seuil_R = genes["seuil_R"]
    metabolisme = genes["metabolisme"]
    age = 0
    age_mort = random.uniform(300,500)

    energie = 5
    etat = "PASSIVE"

    # --- Fonctions internes pour utiliser les variables locales (shm, my_pos...) ---
    
    def essayer_deplacement(cible,code_bytes, est_actif): #code_bytes = si la proie est active ou pas
        nonlocal my_pos, energie 
        # Lecture (attention, sem doit être acquis avant l'appel ou ici)
        # Ici on suppose que l'appelant gère le sémaphore pour optimiser
        val = shm.read(1, offset=cible)
        
        if val == bytes([c.EMPTY]):
            shm.write(bytes([c.EMPTY]), offset=my_pos)
            shm.write(code_bytes, offset=cible)
            my_pos = cible
            return True
            
        elif val == bytes([c.GRASS]):
            shm.write(bytes([c.EMPTY]), offset=my_pos)
            shm.write(code_bytes, offset=cible)
            my_pos = cible
            
            if est_actif:
                energie += 2
                # L'herbe est digérée (elle disparaît déjà via l'écriture du code proie)
            else:
                # L'herbe est piétinée (détruite) mais pas mangée, #pass, sinon return False pour considérer l'herbe comme pas deplacable
                return False
            return True
        return False

    def action_tour(code_actuel):
        code_bytes = bytes([code_actuel]) #crochet pour renvoyer le bon octet
        sem.acquire()
        try:
            # 1. Obtenir les voisins
            voisins = obtenir_voisins(my_pos)
            random.shuffle(voisins)
            
            bouge = False

            est_actif = (etat == "ACTIVE")
            
            if etat == "ACTIVE":
                # Stratégie : Chercher herbe en priorité
                for v in voisins:
                    if shm.read(1, offset=v) == bytes([c.GRASS]):
                        essayer_deplacement(v,code_bytes,est_actif)
                        bouge = True
                        break
            
            danger_proche = []
            safe_cases = []
            
            for v in voisins:
                val = shm.read(1, offset=v)
                if val == bytes([c.PREDATOR]):
                    danger_proche.append(v)
                elif val == bytes([c.EMPTY]) or val == bytes([c.GRASS]):
                    safe_cases.append(v)
                    
            #FUITE
            if danger_proche and safe_cases:
                best_escape = safe_cases[0] 
                essayer_deplacement(best_escape, code_bytes, est_actif)
                bouge = True
            
            # Si pas bougé (soit PASSIF, soit pas d'herbe trouvée en ACTIF)
            if not bouge and voisins:
                target = random.choice(voisins)
                essayer_deplacement(target,code_bytes,est_actif)
                
        finally:
            sem.release()

    # 4. Boucle de Vie
    try:
        while True:
            try:
                # Métabolisme
                age += 1
                energie -= metabolisme
                time.sleep(random.uniform(0.5, 1.0))
                
                # Mort
                if energie < 0 or age > age_mort:
                    print(f"[PROIE {my_pos}] Mort de faim...")
                    sem.acquire()
                    try:
                        #On nettoie la case s'il n'y a que nous dessus
                        if shm.read(1, offset=my_pos) in [bytes([c.PREY]), bytes([c.ACTIVE_PREY])]:
                            shm.write(bytes([c.EMPTY]), offset=my_pos)
                    finally:
                        sem.release()
                    break
                
                code_actuel = c.PREY

                # Machine à états
                if energie < seuil_H:
                    etat = "ACTIVE"
                    code_actuel = c.ACTIVE_PREY
                
                elif etat == "ACTIVE" and energie > seuil_satiete:
                    etat = "PASSIVE"
                    code_actuel = c.PREY
            
                elif etat == "ACTIVE":
                    code_actuel = c.ACTIVE_PREY
                else:
                    code_actuel = c.PREY
                
                sem.acquire() #Si ma position n'est pas moi, alors j'ai été mangé seuil_satiete = 10 
                try :
                    val_sur_carte = shm.read(1, offset=my_pos)
                    
                    # On est vivant peut importe si on est passif ou actif
                    est_vivant = (val_sur_carte == bytes([c.PREY])) or (val_sur_carte == bytes([c.ACTIVE_PREY]))
                    
                    if not est_vivant:
                        print(f"[PROIE] {my_pos} a été mangée ! ")
                        sem.release()
                        sys.exit(0)
                    
                    # Mise à jour de l'apparence anti-suicide
                    if val_sur_carte != bytes([code_actuel]):
                        shm.write(bytes([code_actuel]), offset=my_pos)
                finally :
                    sem.release()
                
                #  --- REPRODUCTION ---
                if energie > seuil_R and random.random() <0.2 :
                    child_spot = -1
                    
                    sem.acquire() # Section critique pour trouver une place
                    try:
                        voisins = obtenir_voisins(my_pos)
                        random.shuffle(voisins)
                        for v in voisins:
                            if shm.read(1, offset=v) == bytes([c.EMPTY]):
                                child_spot = v
                                # IMPORTANT : On RÉSERVE la place pour l'enfant tout de suite
                                # Sinon un autre processus pourrait prendre la place avant que l'enfant ne démarre
                                shm.write(bytes([c.PREY]), offset=child_spot)
                                break
                    finally:
                        sem.release()
                    
                    # Si on a trouvé une place, on lance le processus
                    if child_spot != -1:
                        child_genes = genes.copy()
                        for cle in child_genes :
                            if cle == metabolisme:
                                child_genes[metabolisme] += random.uniform(-0.01,0.005)
                            else: 
                                child_genes[cle] += random.uniform(-0.2, 0.2)
                        p = multiprocessing.Process(target=run_prey, args=(child_spot,child_genes))
                        p.start()
                        energie -= cout_reproduction# Coût de reproduction
                        print(f"💕 Reproduction de {my_pos} vers {child_spot}")

                # Action (Déplacement/Manger) -> maintenant, on prend en compte de si la proie est active ou pas
                try:
                    action_tour(code_actuel)
                except sysv_ipc.ExistentialError:
                    # Si la mémoire a disparu, env a terminé
                    print(f"[PROIE {multiprocessing.current_process().pid}] Monde détruit. Arrêt.")
                    break # On sort de la boucle proprement
            
            except sysv_ipc.ExistentialError:
                break
    
    
    
    except KeyboardInterrupt:
        pass

    finally:
        # Nettoyage
        try:
            sem.acquire()
            # On vérifie qu'on est bien toujours une proie ici (pas écrasé)
            if shm.read(1, offset=my_pos) == bytes([c.PREY]):
                shm.write(bytes([c.EMPTY]), offset=my_pos)
            sem.release()
        except:
            pass

# --- MAIN ---
if __name__ == "__main__":
    # Lancement de la première proie (mode Socket)
    # Les enfants seront lancés par la fonction run_prey elle-même
    p = multiprocessing.Process(target=run_prey)
    p.start()
    p.join() 
