# PPC
1. Structures utilisés

Pour les mutexs (les sémpahores initialisées à 1, l'accès à la mémoire partagée -> module sisv_ipc)
Chaque animal est représenté par 8 octets ; 4 octets pour le pid, 4 octets pour son état. La mémoire partagée stocke alors l'animal dans deux cases mémoires. On utilise le module struct pour convertir chaque donné de la simulation en 4 octets pour assurer la compatibilité de la mémoire partagée.
Les modules os,sys sont utilisés pour les signaux.
Le module time est utilisé dans l'implémenation des proies, des prédateurs et de env
Le module select est utilisé dans le display pour gérer le terminal


Activer/Désactiver la sécheresse : appuyer s + Entrée sur le display
Quitter le display : appuyer sur q = Entrée

Vous pouvez choisir, après avoir lancé env.py de soi : 
Lancer les proies et prédateurs via des terminaux distinctifs
Avoir un nombre défini de proies et de prédateurs lancés via display
