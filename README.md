# PPC
1. Strucures utilisés
Pour les mutexs (les sémpahores initialisées à 1, l'accès à la mémoire partagée -> module sisv_ipc)

Activer/Désactiver la sécheresse : appuyer s + Entrée sur le display
Quitter le display : appuyer sur q

Les proies et prédateurs suivent des heuristiques simples : 
Les proies : fuient lorsqu'un prédateur est un voisin (ie une case adjacente)
Les prédateurs : traquent les proies si ils en voient une à une case adjacente 
La reproduction : La proie vient de passer de l'état passif à l'état actif, elle mange jusqu'à un seuil de satiété pour redevenir passive. Durant ce temps la, elle a une petite probabilité de se reproduire (une proie peut se reproduire et rester active ou alors ne pas se reproduire en mangeant et redevient passive).
Les enfants des proies et des prédateurs héritent des gènes de ces derniers avec des mutations aléatoires (mimer la sélection naturelle).
Les proies et prédateurs ont un age (=itération dans le boucle de vie) qui les fait mourir obligatoirement entre 300 et 500 ans pour éviter les situations de cluster

Déroulé : d'abord, nous avons pensé intuitivement au déplacement des proies (ce qui n'est pas le cas) -> un peu hors sujet car on avait un mutex pour 800 cases
-> recode de env.py d'abord + simple accès dans la logique producer consumer. 
-> après, on est revenu à env.py -> logique de distance, pas de listes de pid mais des moutons qui se déplacent pour manger de l'herbe qui pousse sur des cases
Mutex pour une case : pas opti -> liste de sémaphores avec des modulos -> n sémaphores = n proies qui peuvent manger en même temps. 
Les codes "bonus" (ceux qui suivent les heuristiques de déplacements, sont placés dans le dossier bonus.
