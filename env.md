graph TD
    Start((Début)) --> Reg[Inscription via Socket :<br/>Obtention d'un index de slot]
    Reg --> Init[Initialisation IPC :<br/>SHM & Sémaphore]
    Init --> WriteSelf[Écrire PID et Type PREY dans SHM<br/>via Sémaphore]
    
    WriteSelf --> Loop[Boucle de vie]
    
    subgraph "Cycle de Vie"
        Loop --> Stats[Vieillir & Consommer Énergie<br/>metabolisme = 0.2]
        Stats --> DeathCheck{Énergie < 0 OU<br/>Âge > Max ?}
        DeathCheck -- Oui --> Cleanup
        
        DeathCheck -- Non --> StateUpdate[Déterminer état :<br/>ACTIVE si faim, sinon PASSIVE]
        
        StateUpdate --> LockSem[Acquérir Sémaphore]
        
        LockSem --> SurvivalCheck{Mon PID est-il<br/>toujours en SHM ?}
        SurvivalCheck -- Non --> ReleaseDeath[Libérer Sémaphore & Finir]
        SurvivalCheck -- Oui --> UpdateSHM[Mettre à jour Type en SHM<br/>PREY ou ACTIVE_PREY]
        
        UpdateSHM --> Eating{État ACTIVE ?}
        Eating -- Oui --> EatGrass[Lire Herbe dans SHM<br/>Si > 0 : Herbe -1, Énergie +2]
        Eating -- Non --> UnlockSem
        EatGrass --> UnlockSem[Libérer Sémaphore]
        
        UnlockSem --> ReproCheck{Énergie > seuil_R<br/>& Proba 10% ?}
        ReproCheck -- Oui --> SearchSlot[Acquérir Sémaphore &<br/>Chercher slot vide PID=0]
        SearchSlot --> ReserveSlot[Réserver slot : PID=-1<br/>Libérer Sémaphore]
        ReserveSlot --> SpawnChild[Lancer Processus Enfant]
        SpawnChild --> Loop
        
        ReproCheck -- Non --> Loop
    end

    ReleaseDeath --> End((Fin))
    Cleanup --> ClearSHM[Acquérir Sémaphore &<br/>Remettre slot à 0,0]
    ClearSHM --> End
