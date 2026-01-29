Annexe IA : 

L'utilisation de l'IA générative s'est faite : 
Dans la visulation des diagrammes, nous nous sommes aidés de l'IA qui transformé nos diagrammes 'sur papier' en code Mermaid.

Pour la rédaction du README, du compte-rendu en LateX et de cette annexe : pour la mise en page (syntaxe) adaptée aux différents formats et pour s'assurer qu'il n'y a pas de fautes d'orthographe. Le texte sinon est resté inchangé.

Dans le code : 
*La principale utilisation de l'IA s'est faite pour le débuggage : rajout de multiples print, de quelques try/except pour mieux encapsuler et vérifier ce que nous faisions, pour vérifier à *quelle instruction le programme n'était pas correct,... Nous spécifierons cela pour chaque programme afin de rester le plus exhaustif possible.
*Nous retrouvons aussi l'utilisation de l'IA pour la suggestion d'API à utiliser : sysv_ipc a été une des recommendations de l'IA, nous lui avons demandé, en complément de la documentation, *d'illustrer comment fonctionne la mémoire partagée de l'API, l'utilsation de select dans le display.py pour avoir un terminal non bloquant.
*Indications sur l'utilisation du module struct dans la sharedMemory pour que toutes les données prennent la "même place" (c-à-d 4 octets)

env.py : 
*utilisation surtout pour le débuggage lié à l'utilisation des sockets
*Ligne 48 à 64 : rajout de l'IA de la suppression des mutex, de la Mq et de la mémoire partagée au cas où le noettyage du code précédent ne s'est pas bien fait.
*l'IA générative nous a donné l'idée d'emploi du module struct, notamment pour faire l'extraction de données aux lignes 102-108
*ligne 112 : utilisation de client.sendall au lieu de client.send grâce à l'IA
*ligne 144 : conversion en octet de notre if BoolSecheresse else et du header

Dans predator.py et prey.py : débuggage sur le module struct qui nous a aidé à gérer les conversions en bytes proprement (>I et ii sont deux représentations d'entiers que nous ne connaissions pas avant la proposition de l'IA)
*Ligne 106 à 115 qui fait nettoyer la propre case du prédateur une fois mort
*ligne 94 : l'IA nous a proposé la solution de mettre le PID du nouveau né temporairement à -1 pour éviter les vols de case 

Dans display.py : 
*ligne 18 : rajout de CURSOR_HOME qui place le curseur de la souris en haut à gauche
*ligne 35-36 : rajout des 'or 20', 'or 5' au cas ou on ne rentre rien quand on nous demande le nombre de proies et prédateurs que l'on veut
*ligne 80-95 : affichage fait entièrement par IA afin de rendre ça un peu joli sans interface graphique
*rajout des os.system('clear') que nous n'avions pas vu en TD
