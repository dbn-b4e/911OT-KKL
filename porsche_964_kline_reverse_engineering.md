# Porsche 964/993 K-Line Protocol - Reverse Engineering Complet

## TODO - Implémentation ESP32

### Hardware
- [ ] Choisir IC K-Line (L9637D ou SN65HVDA195)
- [ ] Concevoir PCB interface K-Line → ESP32
- [ ] Ajouter régulateur 3.3V/5V depuis 12V véhicule
- [ ] Prévoir connecteur OBD-II 16 broches
- [ ] Prévoir adaptateur 19 broches pour 964/993 early
- [ ] Protection ESD sur K-Line
- [ ] LED status (connexion, activité, erreur)

### Firmware ESP32
- [ ] Implémenter init 5-baud via GPIO (200ms/bit)
- [ ] Implémenter handshake (sync 0x55, keywords, ACK)
- [ ] Implémenter communication KWP1281 avec ACK inter-octets
- [ ] Support baudrate 8800 (964) et 9600 (993)
- [ ] Détection auto 964 vs 993 ou sélection manuelle
- [ ] Commandes : GetECUID, ReadFaults, ClearFaults, ReadGroup
- [ ] Test actuateurs (CCU)
- [ ] System Adaptation (v4 feature)
- [ ] Keep-alive (ACK toutes les 5s)
- [ ] Gestion timeout et reconnexion

### Interface Utilisateur
- [ ] Affichage LCD/OLED ou app mobile (BLE/WiFi)
- [ ] Sélection module ECU (Motronic, ABS, CCU, SRS, Alarm, TIP)
- [ ] Affichage codes défaut avec descriptions
- [ ] Affichage valeurs temps réel (RPM, temp, etc.)
- [ ] Logging données sur SD card ou envoi WiFi

### Tests
- [ ] Tester connexion Motronic 964 (8800 baud)
- [ ] Tester connexion Motronic 993 (9600 baud)
- [ ] Tester ABS 964 (0x3D @ 4800)
- [ ] Tester ABS 993 (0x1F @ 9600)
- [ ] Tester CCU, SRS, Alarm, TIP
- [ ] Valider lecture/effacement codes défaut
- [ ] Valider workaround Drive Block (993)

### Documentation
- [ ] Schéma électrique final
- [ ] BOM (Bill of Materials)
- [ ] Instructions montage
- [ ] Guide utilisateur

---

## Document Analysé

### Versions ScanTool

| Version | Date | Taille | MD5 | Nouveautés |
|---------|------|--------|-----|------------|
| **v3** | 2004-06-11 | 278,528 | 548dc53aaddb5ae8d9e2c542628b19f9 | Version de base |
| **v4** | 2006-07-01 | 282,624 | c2ef21530883533f1f31e2028313f211 | +System Adaptation, +Alarm, +TIP, +CSV logging |

- **Type**: PE32 executable (GUI) Intel 80386, MFC Application
- **Auteur original**: Doug Boyce
- **Différence binaire**: +4096 bytes (1 page mémoire)

### Release Notes v4
```
05/30/06: Scantool version 4
05/30/06: Added system adaptation feature
06/01/06: Changed adaptation timeout from 40 to 60 seconds.
          ECU sometimes drops connection during cranking which adds
          to time needed for adaptation.
```

---

## 1. Adresses ECU (5-Baud Init Address)

**IMPORTANT**: Les adresses sont en DÉCIMAL dans le fichier cfg !

### Porsche 964 (Carrera, C2, C4)

| Module | Décimal | Hex | Baudrate | Description |
|--------|---------|-----|----------|-------------|
| **Motronic DME** | 16 | **0x10** | 8800 | Gestion moteur (Bosch M2.1) |
| **ABS/Traction** | 61 | **0x3D** | 4800 | ABS et contrôle traction (C4) |
| **Climate Control** | 81 | **0x51** | 4800 | Climatisation (CCU) |
| **SRS Airbag** | 87 | **0x57** | 9600 | Coussins gonflables |
| **Alarm** | 64 | **0x40** | 9600 | Système antivol (v4+) |
| **TIP (Tiptronic)** | 41 | **0x29** | 4800 | Boîte automatique (v4+) |

### Porsche 993

| Module | Décimal | Hex | Baudrate | Notes |
|--------|---------|-----|----------|-------|
| **Motronic DME** | 16 | **0x10** | **9600** | Différent de 964! |
| **ABS/Traction** | **31** | **0x1F** | **9600** | Adresse ET baudrate différents! |
| **Climate Control** | 81 | **0x51** | 4800 | Identique |
| **SRS Airbag** | 87 | **0x57** | 9600 | Identique |
| **Alarm** | 64 | **0x40** | 9600 | Identique |
| **TIP (Tiptronic)** | 41 | **0x29** | 4800 | Identique |

### Résumé Baudrates

```
964:
  Motronic:     8800 baud
  ABS/Traction: 4800 baud
  Climate:      4800 baud
  Airbag:       9600 baud
  Alarm:        9600 baud
  TIP:          4800 baud

993:
  Motronic:     9600 baud  ← DIFFÉRENT
  ABS/Traction: 9600 baud  ← DIFFÉRENT (adresse aussi!)
  Climate:      4800 baud
  Airbag:       9600 baud
  Alarm:        9600 baud
  TIP:          4800 baud
```

---

## 1b. Spécificités 964 Turbo 3.6 (Type 965)

### ATTENTION : Architecture DIFFÉRENTE de la 964 Carrera !

La 964 Turbo (965) n'utilise **PAS** le système Motronic intégré. Elle a une architecture séparée :

| Système | 964 Carrera | 964 Turbo (965) |
|---------|-------------|-----------------|
| **Injection** | Motronic M2.1 (EFI séquentielle) | **CIS K-Jetronic** (mécanique) |
| **Allumage** | Intégré dans Motronic | **ECU séparé** (Bosch EZ69) |
| **Lambda** | Intégré dans Motronic | **ECU séparé** (optionnel) |
| **Diagnostic K-Line moteur** | Oui (0x10) | **NON** |

### ECUs présents sur 964 Turbo

| ECU | Part Number | Fonction | Localisation |
|-----|-------------|----------|--------------|
| **Ignition Control** (Bosch EZ69) | 965 602 706 01 (3.3L) | Allumage électronique | Panneau électrique moteur |
| **Ignition Control** (Bosch EZ69) | 965 602 706 02 (3.6L) | Allumage (mapping modifié) | Panneau électrique moteur |
| **Oxygen Sensor Control** | 965 618 103 00 (ROW) | Contrôle Lambda CIS | Sous siège gauche |
| **Oxygen Sensor Control** | 965 618 103 01 (USA) | Contrôle Lambda CIS | Sous siège gauche |
| **Turbo Control Unit** | - | Pompes carburant, sécurités, boost | Sous siège gauche |
| **Acceleration Enrichment** | - | Enrichissement à froid | Sous siège gauche |
| **Ignition Relay** | 965 618 130 00 | Relais puissance | Sous siège passager |

### Entrées ECU Allumage (EZ69)

| Signal | Source | Description |
|--------|--------|-------------|
| RPM | Flywheel speed sensor | Capteur régime volant moteur |
| Pression | Capteur **intégré dans ECU** | Relié au papillon |
| Temp air boost | Intercooler | Température air suralimentation |
| Idle switch | Papillon 0° | Contact ralenti |
| Octane code | Jumper 944 612 525 01 | Sélecteur carburant (optionnel) |

### Sorties ECU Allumage (EZ69)

| Signal | Destination | Description |
|--------|-------------|-------------|
| Ignition pulse | Transformateur allumage | Commande bobine |
| RPM signal | Turbo control unit | Régime pour pompes carburant |
| RPM signal | Compte-tours | Affichage tableau de bord |

### Différences Turbo 3.3L vs 3.6L

| Aspect | M30/69 (3.3L 1991-92) | M64/50 (3.6L 1993-94) |
|--------|----------------------|----------------------|
| Base moteur | Dérivé 930 | Dérivé M64 Carrera |
| ECU Allumage | 965 602 706 01 | 965 602 706 02 |
| Prise pression ECU | Amont papillon | **Aval papillon** |
| Distributeur | Standard 930 | 965 602 024 00 (arbre long) |
| Pression contrôle (pleine charge) | 4.5 → 3.2 bar | 4.5 → **2.9 bar** |
| Régulateur pression | Standard | 965 606 106 00 |
| Bougies | Standard | Bosch FR 6 LDC |

### Pas de capteur de cliquetis !

> *"Both turbocharged engine variants are not fitted with knock regulation protection"*
> — Adrian Streather, 964 Turbo Technical Overview

Les moteurs 965 n'ont **PAS** de protection anti-cliquetis électronique. Porsche recommande du carburant 98 RON minimum.

### Diagnostic K-Line disponible sur 965

| Module | Adresse | Baudrate | Diagnostic K-Line |
|--------|---------|----------|-------------------|
| Ignition (EZ69) | - | - | **NON** (pas de K-Line) |
| Lambda Control | - | - | Limité (si équipé) |
| **ABS/Traction** | 61 (0x3D) | 4800 | **OUI** |
| **Climate (CCU)** | 81 (0x51) | 4800 | **OUI** |
| **Airbag (SRS)** | 87 (0x57) | 9600 | **OUI** |

### Diagnostic alternatif moteur 965

Pour diagnostiquer le moteur turbo sans K-Line :

**1. Oscilloscope**
- Signal RPM (flywheel sensor)
- Duty cycle frequency valve (Lambda)
- Signal allumage

**2. Multimètre**
- Résistances capteurs NTC
- Tension O2 sensor (0.1-0.9V)
- Switches papillon (0°, 7°, 66°)

**3. Manomètre**
- Pression carburant système (5.3-5.7 bar)
- Pression contrôle (2.8-4.5 bar selon temp)
- Boost turbo (0.7-0.8 bar nominal)

### Système CIS K-Jetronic (Injection mécanique)

```
                    ┌─────────────────┐
                    │  Air Flow Meter │
                    │  (Débitmètre)   │
                    └────────┬────────┘
                             │
                             ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│ Fuel Pumps   │───►│ Fuel Distributor│───►│ 6 Injectors  │
│ (2x electric)│    │ (Mécanique)     │    │ (Mécaniques) │
└──────────────┘    └────────┬────────┘    └──────────────┘
                             │
                    ┌────────┴────────┐
                    │ Frequency Valve │◄─── Lambda ECU
                    │ (Électrovanne)  │     (Duty cycle)
                    └─────────────────┘
```

Le **Frequency Valve** est le seul élément électroniquement contrôlé de l'injection :
- Fréquence fixe ~70 Hz
- Duty cycle variable (lean < 50% < rich)
- Contrôlé par Lambda ECU basé sur O2 sensor

### Capteurs et switches papillon (965)

| Switch | Angle | Fonction |
|--------|-------|----------|
| 0° | Fermé | Idle - ralenti |
| 7° | Partiel | Fin enrichissement accélération |
| 66° | Pleine charge | Full load - enrichissement max |

### Sécurités Turbo Control Unit

| Protection | Seuil | Action |
|------------|-------|--------|
| Sur-régime | 6800 RPM | Coupure pompes carburant |
| Sur-boost | 1.1-1.4 bar | Coupure pompes carburant |
| Ignition delay | 5 sec après coupure | Maintien allumage |

---

## 2. Codes de Commandes (Block Title - Requêtes)

| Code | Hex | Nom | Description |
|------|-----|-----|-------------|
| 0 | 0x00 | **GetECUID** | Demande identification ECU |
| 5 | 0x05 | **ClearFaults** | Effacer codes défaut |
| 6 | 0x06 | **EndComm** | Terminer la communication |
| 7 | 0x07 | **ReadFaults** | Lire codes défaut |
| 9 | 0x09 | **ACK** | Acquittement / Keep-alive |
| 16 | 0x10 | **ActuatorTest** | Test des actuateurs |
| 20 | 0x14 | **ReadSensor** | Lecture capteur unique |
| 33 | 0x21 | **ReadSingle** | Lecture valeur simple |
| 40 | 0x28 | **BasicSetting** | Réglage de base / Adaptation |
| 41 | 0x29 | **ReadGroup** | Lecture groupe de mesures |
| 42 | 0x2A | **Login** | Authentification |
| 43 | 0x2B | **ReadAdapt** | Lire adaptation |
| 44 | 0x2C | **WriteAdapt** | Écrire adaptation |

---

## 3. Codes de Réponse (Block Title - Réponses ECU)

| Code | Hex | Nom | Description |
|------|-----|-----|-------------|
| 9 | 0x09 | **ACK** | Acquittement positif |
| 10 | 0x0A | **NAK** | Erreur / Refus |
| 231 | 0xE7 | **GroupData** | Données de groupe (4 valeurs) |
| 244 | 0xF4 | **AdaptResp** | Réponse adaptation lecture |
| 245 | 0xF5 | **AdaptWrite** | Réponse adaptation écriture |
| 246 | 0xF6 | **ASCIIID** | Chaîne identification (Part Number) |
| 252 | 0xFC | **FaultCodes** | Codes défaut |
| 253 | 0xFD | **AdaptChan** | Canal adaptation |
| 254 | 0xFE | **BinaryData** | Données binaires |

---

## 4. Format des Blocs KWP1281

```
┌─────────┬──────────┬───────┬────────────┬─────┐
│ Length  │ Counter  │ Title │   Data     │ ETX │
│ (1 byte)│ (1 byte) │(1 byte│ (0-n bytes)│0x03 │
└─────────┴──────────┴───────┴────────────┴─────┘
```

### Champs

| Champ | Taille | Description |
|-------|--------|-------------|
| Length | 1 | Longueur totale bloc (Length + Counter + Title + Data + ETX) |
| Counter | 1 | Compteur séquentiel 0x00-0xFF, incrémenté chaque bloc |
| Title | 1 | Code commande ou réponse |
| Data | 0-n | Données optionnelles |
| ETX | 1 | Toujours 0x03 (End of Text) |

### Protocole ACK Inter-Octets

**CRITIQUE**: Chaque octet reçu (sauf le dernier 0x03) doit être acquitté :

```
ECU envoie: 0x07
Outil répond: 0xF8 (= ~0x07 = 0xFF - 0x07)

ECU envoie: 0x03 (fin de bloc)
Outil ne répond pas (pas d'ACK pour ETX)
```

---

## 5. Trames Détaillées

### 5.1 Initialisation 5-Baud

```
Signal K-Line (via RTS):
┌─────┬───┬───┬───┬───┬───┬───┬───┬───┬─────┐
│Start│ 0 │ 1 │ 2 │ 3 │ 4 │ 5 │ 6 │ 7 │Stop │
│  0  │LSB│   │   │   │   │   │   │MSB│  1  │
└─────┴───┴───┴───┴───┴───┴───┴───┴───┴─────┘
  200ms chaque bit = 2 secondes total

Exemple pour adresse 0x10 (Motronic):
0x10 = 0b00010000
Séquence: 0-0-0-0-0-1-0-0-0-1 (Start-LSB...MSB-Stop)
```

### 5.2 Handshake Complet

```
Outil                              ECU
  │                                  │
  │──── Adresse 0x10 @ 5 baud ──────>│
  │          (2 secondes)            │
  │                                  │
  │<──────── Sync 0x55 ─────────────│
  │                                  │
  │<──────── Keyword1 ──────────────│
  │────── ACK (~Keyword1) ─────────>│
  │                                  │
  │<──────── Keyword2 ──────────────│
  │  (attendre 30ms)                 │
  │────── ACK (~Keyword2) ─────────>│
  │                                  │
  │ === Communication @ baudrate ===│
```

### 5.3 Requête Identification ECU

**Envoi (Outil → ECU):**
```
┌────┬────┬────┬────┐
│ 04 │ 00 │ 00 │ 03 │
└────┴────┴────┴────┘
 Len  Cnt  Cmd  ETX
       │    └── 0x00 = GetECUID
       └── Premier bloc = compteur 0
```

**Réponse (ECU → Outil):**
```
┌────┬────┬────┬────────────────────────┬────┐
│ 0F │ 01 │ F6 │ "964.618.124.02" (ASCII)│ 03 │
└────┴────┴────┴────────────────────────┴────┘
 Len  Cnt  Rsp  Part Number (12 chars)   ETX
            └── 0xF6 = ASCII ID Response
```

### 5.4 Lecture Codes Défaut

**Envoi:**
```
┌────┬────┬────┬────┐
│ 04 │ 02 │ 07 │ 03 │
└────┴────┴────┴────┘
 Len  Cnt  Cmd  ETX
            └── 0x07 = ReadFaults
```

**Réponse (avec défauts):**
```
┌────┬────┬────┬────┬────┬────┬────┬────┐
│ 08 │ 03 │ FC │ XX │ SS │ YY │ TT │ 03 │
└────┴────┴────┴────┴────┴────┴────┴────┘
 Len  Cnt  Rsp  Code1 Stat Code2 Stat ETX
            │    │     │
            │    │     └── Status (AND 0x3F = count)
            │    └── Code défaut
            └── 0xFC = Fault Response
```

**Réponse (sans défauts):**
```
┌────┬────┬────┬────┬────┐
│ 05 │ 03 │ FC │ 00 │ 03 │
└────┴────┴────┴────┴────┘
            │    └── 0x00 = pas de défaut
            └── 0xFC
```

### 5.5 Effacement Codes Défaut

**Envoi:**
```
┌────┬────┬────┬────┐
│ 04 │ 04 │ 05 │ 03 │
└────┴────┴────┴────┘
            └── 0x05 = ClearFaults
```

**Réponse:**
```
┌────┬────┬────┬────┐
│ 04 │ 05 │ 09 │ 03 │
└────┴────┴────┴────┘
            └── 0x09 = ACK (succès)
```

### 5.6 Lecture Groupe de Mesures

**Envoi:**
```
┌────┬────┬────┬────┬────┐
│ 05 │ 06 │ 29 │ GG │ 03 │
└────┴────┴────┴────┴────┘
            │    └── Numéro de groupe (01-FF)
            └── 0x29 = ReadGroup
```

**Réponse:**
```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 0F │ 07 │ E7 │ F1 │ V1a│ V1b│ F2 │ V2a│ V2b│ F3 │ V3a│ V3b│ F4 │...│
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
            │    │    │    │
            │    │    │    └── Valeur 1 (16-bit big-endian)
            │    │    └── Formula 1 (type de conversion)
            │    └── 4 valeurs × 3 bytes = 12 bytes data
            └── 0xE7 = Group Data Response
```

### 5.7 Keep-Alive (ACK)

**Envoi (toutes les 5 secondes max):**
```
┌────┬────┬────┬────┐
│ 04 │ XX │ 09 │ 03 │
└────┴────┴────┴────┘
            └── 0x09 = ACK
```

### 5.8 Fin de Communication

**Envoi:**
```
┌────┬────┬────┬────┐
│ 04 │ XX │ 06 │ 03 │
└────┴────┴────┴────┘
            └── 0x06 = EndComm
```

### 5.9 Test Actuateur

**Envoi (démarrer test):**
```
┌────┬────┬────┬────┬────┐
│ 05 │ XX │ 10 │ AA │ 03 │
└────┴────┴────┴────┴────┘
            │    └── Numéro actuateur (01-FF)
            └── 0x10 = ActuatorTest
```

**Réponse:**
```
┌────┬────┬────┬────┬────┬────┐
│ 06 │ XX │ F5 │ AA │ SS │ 03 │
└────┴────┴────┴────┴────┴────┘
            │    │    └── Status
            │    └── Numéro actuateur
            └── 0xF5 = Actuator Response
```

### 5.10 Lecture Adaptation

**Envoi:**
```
┌────┬────┬────┬────┬────┐
│ 05 │ XX │ 2B │ CH │ 03 │
└────┴────┴────┴────┴────┘
            │    └── Canal adaptation (00-FF)
            └── 0x2B = ReadAdapt
```

**Réponse:**
```
┌────┬────┬────┬────┬────┬────┬────┐
│ 07 │ XX │ F4 │ CH │ Vhi│ Vlo│ 03 │
└────┴────┴────┴────┴────┴────┴────┘
            │    │    └── Valeur 16-bit (big-endian)
            │    └── Canal
            └── 0xF4 = Adaptation Response
```

### 5.11 Écriture Adaptation

**Envoi:**
```
┌────┬────┬────┬────┬────┬────┬────┐
│ 07 │ XX │ 2C │ CH │ Vhi│ Vlo│ 03 │
└────┴────┴────┴────┴────┴────┴────┘
            │    │    └── Nouvelle valeur 16-bit
            │    └── Canal adaptation
            └── 0x2C = WriteAdapt
```

**Réponse (succès):**
```
┌────┬────┬────┬────┐
│ 04 │ XX │ 09 │ 03 │
└────┴────┴────┴────┘
            └── 0x09 = ACK
```

### 5.12 Login (Authentification)

**Envoi:**
```
┌────┬────┬────┬────┬────┬────┬────┐
│ 07 │ XX │ 2A │ P1 │ P2 │ WS │ 03 │
└────┴────┴────┴────┴────┴────┴────┘
            │    │    │    └── Workshop code (optionnel)
            │    │    └── PIN byte 2
            │    └── PIN byte 1
            └── 0x2A = Login
```

**Réponse (succès):**
```
┌────┬────┬────┬────┐
│ 04 │ XX │ 09 │ 03 │
└────┴────┴────┴────┘
            └── 0x09 = ACK (login OK)
```

### 5.13 Basic Setting / System Adaptation (v4)

**Envoi:**
```
┌────┬────┬────┬────┬────┐
│ 05 │ XX │ 28 │ GG │ 03 │
└────┴────┴────┴────┴────┘
            │    └── Groupe de réglage
            └── 0x28 = BasicSetting
```

**Réponse (données live pendant réglage):**
```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 10 │ XX │ E7 │ F1 │V1hi│V1lo│ F2 │V2hi│V2lo│ F3 │V3hi│V3lo│ F4 │V4hi│V4lo│ 03 │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
            └── 0xE7 = Données groupe (4 valeurs avec formules)
```

### 5.14 System Adaptation (Procédure v4)

**Procédure d'adaptation moteur:**

1. Moteur à température de fonctionnement
2. Envoyer BasicSetting (0x28) avec groupe approprié
3. Suivre instructions (démarrer moteur, attendre ralenti stable)
4. Timeout: **60 secondes** (augmenté de 40s dans v4)
5. L'ECU peut perdre la connexion pendant le démarrage - c'est normal

**Registre Adaptation IAC (964):**
```
Actual Value.Adapted IAC trim = 0x7E4B
```

---

## 6. Format des Codes Défaut

### Structure du Status Byte

```
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 7 │ 6 │ 5 │ 4 │ 3 │ 2 │ 1 │ 0 │
└───┴───┴───┴───┴───┴───┴───┴───┘
  │   │   └───────────────────────── Compteur (0-63)
  │   └── Type: 0=intermittent
  └── Type: 1=permanent
```

**Extraction:**
```c
uint8_t count = status & 0x3F;  // Bits 0-5
uint8_t type = (status >> 6);   // Bits 6-7
```

### Codes Défaut Motronic 964 [M00]

| Code | Description |
|------|-------------|
| 11 | DME control unit power supply too high/low |
| 12 | Idle speed contact ground short |
| 13 | Full load contact ground short |
| 14 | Engine temperature sensor |
| 15 | Idle speed contact break |
| 21 | Air flow sensor (MAF) |
| 22 | Idle speed control (ISV) |
| 23 | Oxygen regulation at stop (intake air leak?) |
| 24 | Oxygen sensor |
| 25 | Air temperature sensor |
| 31 | Knock sensor 1 |
| 32 | Knock sensor 2 |
| 33 | Knock computer |
| 34 | Hall signal |
| 41 | Control unit faulty |
| 43 | Tank venting valve (canister) |
| 44 | Resonance plate |
| 45 | Check engine warning lamp |
| 51 | Injection valve 1 |
| 52 | Injection valve 2 |
| 53 | Injection valve 3 |
| 54 | Injection valve 4 |
| 55 | Injection valve 5 |
| 56 | Injection valve 6 |

### Codes Défaut Motronic 993 [M04/M06]

| Code | Description |
|------|-------------|
| 11 | Power supply, DME, high |
| 14 | Engine temperature sensor 2 |
| 15 | Throttle Potentiometer |
| 16 | Throttle Potentiometer |
| 18 | RPM Signal |
| 19 | Speed signal / Speedometer |
| 21 | Hot-wire mass air flow sensor |
| 22 | Oxygen sensor (Sensor signal) |
| 23 | Oxygen regulation / stop (intake air leak?) |
| 24 | Oxygen sensor short to+ or 0 Volts |
| 25 | Intake air temperature sensor |
| 26 | Ignition timing change |
| 27 | IAC opening/closing winding |
| 28 | IAC opening/closing winding |
| 31 | Knock sensor 1 |
| 32 | Knock sensor 2 |
| 33 | Control unit faulty, Knock computer |
| 34 | Hall signal |
| 36 | Idle CO potentiometer |
| 41 | Control unit faulty |
| 42 | Fuel pump relay (DME relay) |
| 43 | Tank ventilation valve |
| 44 | Auxiliary air pump relay |
| 45 | Warning lamp Check Engine |
| 51-56 | Injection valves 1-6 |
| 67-69 | Ignition final stage |

### Codes Défaut ABS/Traction 964 [S00]

| Code | Description |
|------|-------------|
| 11 | Lateral lock valve - No feedback signal |
| 12 | Lateral acceleration sensor short-circuit/break |
| 13 | Lateral acceleration sensor - implausible signal |
| 14 | Lateral lock - deviation in regulating values |
| 15 | Control unit defective |
| 21 | Front left speed sensor |
| 22 | Front right speed sensor |
| 23 | Rear right speed sensor |
| 24 | Rear left speed sensor |
| 31 | Front left ABS valve |
| 32 | Front right ABS valve |
| 33 | Rear axle ABS valve |
| 34 | Valve relay |
| 35 | Return pump |
| 41 | Front-rear differential lock valve |
| 42 | Front-rear acceleration sensor short-circuit/break |
| 43 | Longitudinal acceleration sensor - implausible |
| 44 | Front-rear differential lock control deviations |
| 45 | Full differential locking button |

### Codes Défaut ABS 993 [ABS5]

| Code | Description |
|------|-------------|
| 11 | Control unit faulty |
| 12 | Stop light switch |
| 13 | Incorrect gearwheel |
| 14 | Intake valve |
| 15 | Switch-over valve |
| 17 | Throttle (TP) information |
| 21-24 | Speed sensors signal unplausible (FL, FR, RR, RL) |
| 25-28 | Speed sensors open/short (FL, FR, RR, RL) |
| 31-34 | Inlet ABS valves (FL, FR, R, RL) |
| 35-38 | Exhaust ABS valves (FL, FR, RL, RR) |
| 39 | Valve relay |
| 40 | Return pump |

### Codes Défaut Climate Control [H00/H05/H06/H08]

| Code | Description | Actuateur Test |
|------|-------------|----------------|
| 11 | Inside temperature sensor | - |
| 12 | Left mixing chamber temperature sensor | - |
| 13 | Right mixing chamber temperature sensor | - |
| 14 | Evaporator temperature sensor | - |
| 15 | Rear fan temperature sensor | - |
| 16 | Outside temperature sensor (993 only) | - |
| 21 | Oil cooler temperature sensor | - |
| **22** | **Defrost flap motor** | Actuator |
| **23** | **Footwell flap motor** | Actuator |
| **24** | **Fresh air flap motor** | Actuator |
| **31** | **Left mixing flap motor** | Actuator |
| **32** | **Right mixing flap motor** | Actuator |
| **33** | **Left heater blower motor** | Actuator |
| **34** | **Right heater blower motor** | Actuator |
| **41** | **Condenser blower motor** | Actuator |
| **42** | **Oil cooler blower motor** | Actuator |
| **43** | **Rear blower motor speed 1** | Actuator |
| **44** | **Rear blower motor speed 2** | Actuator |
| **45** | **Inside sensor blower motor** | Actuator |
| 46-47 | Rear blower motor (duplicates) | - |

### Codes Défaut Airbag 993 [B02/B03]

| Code | Description |
|------|-------------|
| 1-7 | Fault memory cannot be erased |
| 2 | Driver ignition circuit to + or 0 V |
| 3 | Battery voltage low |
| 4-5 | Driver ignition circuit |
| 10-11 | Passenger ignition circuit |
| 17 | Battery voltage low |
| 19 | Airbag Warning Light to + or 0 V |
| 20-21 | Driver ignition circuit |
| 26-27 | Passenger ignition circuit |
| 36 | Driver ignition circuit |
| 39 | Passenger ignition circuit |
| 70-73 | Child seat detection |
| 73 | Short circuit ignition pills |
| 76 | Control unit fault cannot be erased |
| 77 | Result message cannot be erased |
| 100-103 | Control unit faulty |

### Codes Défaut Alarm [I00/I01]

| Code | Description |
|------|-------------|
| 11 | Control unit faulty |
| 12 | Voltage failure term 30, active alarm |
| 13 | Voltage failure term 30 during output |
| 14 | Position of drives unplausible |
| 15 | Door open during activation |
| 16 | Engine lid open during activation |
| 17 | Luggage lid open during activation |
| 18 | Glove box open during activation |
| 19 | Input 2 to gnd during activation |
| 20 | Central locking system button closed during activation |
| 21 | Input 1 to gnd during activation |
| 22 | Input 3 to positive during activation |
| 23-26 | Fault memory |

### Codes Défaut Tiptronic [G00]

| Code | Description |
|------|-------------|
| 11 | Signal Implausible |
| 13 | Voltage for drive links failed |
| 14 | Voltage for sensors failed |
| 21 | RPM signal from DME failed |
| 22 | Load signal from DME failed |
| 23 | Throttle Pot. Failed |
| 24 | Change of ignition timing |
| 31 | Solenoid valve 1 failed |
| 32 | Solenoid valve 2 failed |
| 33 | Solenoid valve torque converter clutch failed |
| 34 | Pressure regulator failed |
| 35 | Selector lever switch/transmission failed |
| 36 | Transmission speed sensor failed |
| 37 | Transmission temp. sensor failed |
| 38 | Selector lever switch/transmission partial failure |
| 42-44 | Transmission control unit failure |
| 45-46 | Downshift fault in rev limiter |
| 51 | Manual program switch failed |
| 52 | Tip. Switch up and down failed |
| 53 | Kick down switch failed |
| 54 | Transverse accel. Sensor failed |
| 55 | Speed signal 1 from ABS control unit failed |
| 56 | Input to combination instrument failed |
| 57 | Transmission oil cooler blower relay failed |
| 59 | Switch R-position failed |
| 60 | Reverse light relay failed |

---

## 7. Registres et Formules - Comparaison 964 vs 993

### Motronic 964 (8800 baud)

| Paramètre | Registre | Formule | Unité |
|-----------|----------|---------|-------|
| **RPM** | 0x3A | `n * 40` | tr/min |
| **Intake Air Temp** | 0x37 | `((n*115)/100) - 26` | °F |
| **Cylinder Head Temp** | 0x38 | `((n*115)/100) - 26` | °F |
| **AFM Voltage** | 0x45 | `(n*500)/255` | Volts |
| **Injector Time** | 0x42 | `n * 5` | ms |
| **Ignition Advance** | 0x5D | `(((n-0x68)*2075)/255) * -1` | ° |
| **Adapted IAC trim** | 0x7E4B | - | (v4 only) |

### Motronic 993 (9600 baud)

| Paramètre | Registre | Formule | Unité |
|-----------|----------|---------|-------|
| **Battery** | 0x36 | `(n*682)/100` | Volts |
| **Intake Air Temp** | 0x37 | `((n*115)/100) - 26` | °F |
| **Cylinder Head Temp** | 0x38 | `((n*115)/100) - 26` | °F |
| **RPM** | 0x39 | `n * 40` | tr/min |
| **Ignition Advance** | 0x3A | `(n*1)/2` | ° |
| **O2 Sensor** | 0x3D | `n * 3` | mV |
| **Base Inj (8-bit)** | 0x3E | `n * 50` | ms |
| **Base Inj (16-bit)** | 0x3F | UINT16 | ms |
| **MAF Voltage** | 0x47 | `(n*500)/255` | Volts |

### Inputs Analogiques 964

| Input # | Description | Formule | Unité |
|---------|-------------|---------|-------|
| 1 | MAF Sensor | `(n*500)/255` | Volts |
| 2 | Battery | `(n*682)/100` | Volts |
| 3 | NTC 1 (temp) | - | - |
| 4 | NTC 2 (temp) | - | - |
| 6 | O2 Sensor | - | - |
| 7 | FQS (Fuel Quality) | `(n*500)/255` | Volts |
| 8 | MAP Sensor | - | - |

### Inputs Analogiques 993

| Input # | Description | Formule | Unité |
|---------|-------------|---------|-------|
| 1 | Throttle Angle | `(n-0x1A)*42` | ° |
| 2 | Battery | `(n*682)/100` | Volts |
| 4 | en-sen220-10 | - | - |
| 5 | MAF Sensor | `(n*500)/255` | Volts |
| 7 | tipIgTmChg | `n*1` | ° |
| 8 | O2sen 5-170 | - | - |

### Switches (Contacts) 964

| Switch # | Description |
|----------|-------------|
| 1 | WOT (Wide Open Throttle) - Pleine charge |
| 2 | Idle - Contact ralenti |

### Climate Control 993 - Actual Values

| Registre | Description |
|----------|-------------|
| 0x02 | Voltage Term X (V) |
| 0x04 | Inside Temperature (°F) |
| 0x06 | Rear Blower Temperature (°F) |
| 0x08 | Lt mixing Temperature (°F) |
| 0x10 | Rt mixing Temperature (°F) |
| 0x1B | Front Oil Cooler Temp (°F) |
| 0x1D | Evaporator Temperature (°F) |

### ABS 993 - Actual Values

| Registre | Description |
|----------|-------------|
| 0x02 | Stop Light SW |
| 0x04 | Valve Relay |
| 0x06 | Return Pump |
| 0x08 | Speed Vehicle |
| 0x10 | Front Left wheel |
| 0x1B | Front Right wheel |
| 0x1D | Rear Left wheel |
| 0x1F | Rear Right wheel |

### Conversion Températures

```c
// Formule cfg: ((n*115)/100) - 26 = °F
// Pour avoir °C:
float temp_f = ((raw * 115.0) / 100.0) - 26.0;
float temp_c = (temp_f - 32.0) * 5.0 / 9.0;

// Formule directe °C (dans configs _cfg.txt):
// ((((n*115)/100)-26)-32)*5/9
```

---

## 8. Connecteur Diagnostic 19 Broches

### Localisation
- **Position**: Sous le tableau de bord, côté passager
- **Type**: Connecteur rond 19 broches Porsche

### Pinout

```
        ┌─────────────────┐
       /  1   2   3   4   \
      │  5   6   7   8   9  │
      │ 10  11  12  13  14  │
       \ 15  16  17  18  19 /
        └─────────────────┘
```

| Pin | Signal | Description |
|-----|--------|-------------|
| 1-6 | - | Non utilisé |
| **7** | **L-Line** | Ligne L (optionnel, certains modules) |
| **8** | **K-Line** | Ligne K (données bidirectionnelles) |
| 9 | - | Non utilisé |
| **10** | **GND** | Masse châssis |
| 11 | - | Non utilisé |
| **12** | **+12V PERM** | Alimentation permanente batterie |
| **13** | **+12V IGN** | Alimentation après contact |
| 14-19 | - | Non utilisé |

### Pins Essentiels

| Pin | Fonction | Requis |
|-----|----------|--------|
| 8 | K-Line (data) | **OUI** |
| 10 | Masse | **OUI** |
| 12 ou 13 | +12V | **OUI** |
| 7 | L-Line | Non (optionnel) |

---

## 9. Problème Porsche Drive Block (Immobilizer) - 993

### Le Problème

Les 993 équipées du **Porsche Immobilizer (Drive Block)** ont des difficultés à se connecter au DME Motronic via K-Line. L'immobiliseur bloque les connexions OBD tant qu'il n'est pas déverrouillé.

### Workaround (trouvé sur Rennlist)

**Setup:**
- Voiture fermée et verrouillée
- Laptop à l'intérieur, connecté à l'OBD
- Switches:
  - SW1/1 = DME/CCU/ABS/ALARM (pas SRS)
  - SW2/1 = DME (Motronic)
- ScanTool4 **pas encore lancé**

**Procédure:**

1. Appuyer sur la télécommande pour déverrouiller
2. Ouvrir la porte
3. Mettre la clé dans le contact
4. Contact ON (ne pas démarrer le moteur)
5. Lancer ScanTool4
6. ScanTool4 essaie plusieurs fois mais échoue
7. **Fermer ScanTool4**
8. **Relancer ScanTool4**
9. ScanTool4 essaie plusieurs fois jusqu'à connexion réussie
10. Affiche toutes les données

**Note:** Si vous coupez le contact, il faut **reverrouiller** la voiture et refaire toute la procédure depuis le début.

Source: [Rennlist Forum](http://forums.rennlist.com/rennforums/993-forum/371155-scantool-interface-for-1995-obd1-cars-and-the-immobilizer-is-there-a-workaround.html)

---

## 10. Schéma Interface Hardware (ST_Iface Rev 2.1)

### Circuit Officiel ScanTool Interface

D'après le schéma `ST_Iface.pdf` de Gregg Kricorissian :

```
                                    +12V (Pin 13 - Switched)
                                      │
                              ┌───────┴───────┐
                              │    μA7805     │
                              │  Vin  GND +5V │
                              └───┬────┬───┬──┘
                                  │    │   │
                                 C7   GND  +5V
                               2.2μF       │
                                           │
    ┌──────────────────────────────────────┴──────────────────┐
    │                     SIPEX 3222EC                        │
    │              (MAX3232 RS232 Transceiver)                │
    │   T1-IN ◄─── CD4011 ◄─── K-Line logic                  │
    │   T1-OUT ───► PC RX (Pin 2 DE-9)                       │
    │   R1-IN ◄─── PC TX (Pin 3 DE-9)                        │
    │   R1-OUT ───► CD4011 ───► K-Line drive                 │
    └─────────────────────────────────────────────────────────┘


    K-Line Interface (Pin 8):
    ─────────────────────────

                            +12V
                              │
                            [510Ω] R9
                              │
        K-Line (Pin 8) ───────┼──────────────────┐
                              │                  │
                              │            ┌─────┴─────┐
                            [510Ω] R8      │  CD4011   │
                              │            │   U2c     │──► To 3222
                              │            │  (buffer) │
                         ┌────┴────┐       └───────────┘
                         │ 2N7000  │
                         │   Q2    │◄─── From CD4011 U2b
                         │ (N-FET) │
                         └────┬────┘
                              │
                             GND
```

### Composants Clés

| Composant | Valeur | Fonction |
|-----------|--------|----------|
| U1 | Sipex 3222EC | Transceiver RS232 ↔ TTL |
| U2 | CD4011 | 4x NAND gates (logique) |
| U3 | μA7805 | Régulateur 5V |
| Q1, Q2 | 2N7000 | N-MOSFET driver K/L-Line |
| R8, R9 | 510Ω | Pull-up K-Line (ISO 9141) |
| R1, R2 | 1kΩ | Résistances gate MOSFET |
| R5, R7 | 10kΩ | Pull-up/down |
| D1-D4 | 1N4148 | Protection |

### Adaptation pour ESP32

Pour utiliser avec ESP32 (3.3V), remplacer le 3222 par connexion directe :

```
                        +12V
                          │
                        [510Ω]
                          │
    K-Line ───────────────┼─────────────────────┐
                          │                     │
                          │              [10kΩ] diviseur
                        [510Ω]                  │
                          │                     ├──► ESP32 RX (GPIO16)
                     ┌────┴────┐                │    (3.3V max!)
                     │ 2N7000  │              [20kΩ]
                     │         │                │
                     └────┬────┘               GND
                          │
    ESP32 TX (GPIO17) ►───┤ (via 1kΩ)
                          │
                         GND

Note: Ajouter diviseur résistif pour RX (12V → 3.3V)
      Ratio ~4:1 avec 10k + 3.3k ou similaire
```

---

## 11. Paramètres de Communication Série

### Configuration DCB (extraite du code)

| Paramètre | Valeur par défaut | Notes |
|-----------|-------------------|-------|
| **BaudRate** | 9600 (0x2580) | Lu depuis cfg, 9600 si absent |
| **ByteSize** | 8 | Standard |
| **Parity** | None | |
| **StopBits** | 1 | |

**Important**: Le baudrate **8800** pour la 964 n'est PAS hardcodé - il doit être spécifié dans le fichier `scantool.cfg`.

### Fichiers de Configuration

| Fichier | Usage |
|---------|-------|
| `scantool.cfg` | Config active (copier depuis 964 ou 993) |
| `scantool_964_cfg.txt` | Template 964, températures en °C |
| `scantool_964_cfg_f.txt` | Template 964, températures en °F |
| `scantool_993_cfg.txt` | Template 993, températures en °C |
| `scantool_993_cfg_f.txt` | Template 993, températures en °F |
| `scantool.ini` | Port COM (si différent de COM1) |

---

## 12. Séquence d'Initialisation 5-Baud (Reverse Engineered)

### Algorithme Complet

```c
// Phase 1: Start bit (K-line LOW)
EscapeCommFunction(hCom, CLRRTS);   // 3 = CLRRTS → K-Line = 0
Sleep(200);                          // 200ms par bit à 5 baud

// Phase 2: Envoyer 8 bits de l'adresse ECU (LSB first)
for (int i = 0; i < 8; i++) {
    if (address & (1 << i)) {
        EscapeCommFunction(hCom, SETRTS);  // 4 = SETRTS → K-Line = 1
    } else {
        EscapeCommFunction(hCom, CLRRTS);  // 3 = CLRRTS → K-Line = 0
    }
    Sleep(200);  // 200ms par bit
}

// Phase 3: Stop bit (K-line HIGH)
EscapeCommFunction(hCom, SETRTS);   // K-Line = 1
PurgeComm(hCom, PURGE_RXCLEAR | PURGE_TXCLEAR);  // 0x0C
```

### Handshake Post-Init

```c
// Attendre sync byte
byte sync = ReadByte();
if (sync != 0x55) {
    Sleep(1000);  // 0x3E8 = 1000ms timeout
    goto retry_init;
}

// Recevoir keyword 1
byte kw1 = ReadByte();

// Recevoir keyword 2
byte kw2 = ReadByte();

// Envoyer ACK de keyword 2 (complement à 1)
Sleep(30);  // 0x1E = 30ms delay avant ACK
byte ack = 0xFF - kw2;  // Equivalent à ~kw2
SendByte(ack);
```

### Timing Constants

| Constante | Valeur | Usage |
|-----------|--------|-------|
| 200ms | 0xC8 | Bit time 5-baud |
| 30ms | 0x1E | Delay avant ACK keyword |
| 1000ms | 0x3E8 | Timeout retry init |
| 60000ms | - | Timeout adaptation (v4) |

---

## 13. Implémentation ESP32 Recommandée

```c
#include "driver/uart.h"
#include "driver/gpio.h"

#define KLINE_TX_PIN    GPIO_NUM_17
#define KLINE_RX_PIN    GPIO_NUM_16
#define BAUD_964        8800
#define BAUD_993        9600
#define BIT_TIME_5BAUD  200  // ms

// Adresses ECU
#define ECU_MOTRONIC    0x10
#define ECU_ABS_964     0x3D
#define ECU_ABS_993     0x1F
#define ECU_CCU         0x51
#define ECU_SRS         0x57
#define ECU_ALARM       0x40
#define ECU_TIP         0x29

// Init 5-baud via GPIO (pas UART)
void send_5baud_address(uint8_t addr) {
    gpio_set_direction(KLINE_TX_PIN, GPIO_MODE_OUTPUT);

    // Start bit (LOW)
    gpio_set_level(KLINE_TX_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(BIT_TIME_5BAUD));

    // 8 data bits LSB first
    for (int i = 0; i < 8; i++) {
        gpio_set_level(KLINE_TX_PIN, (addr >> i) & 1);
        vTaskDelay(pdMS_TO_TICKS(BIT_TIME_5BAUD));
    }

    // Stop bit (HIGH)
    gpio_set_level(KLINE_TX_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(BIT_TIME_5BAUD));
}

// Handshake après init
bool kwp1281_handshake(uint32_t baudrate) {
    // Configurer UART après 5-baud
    uart_set_baudrate(UART_NUM_1, baudrate);

    // Attendre sync 0x55
    uint8_t sync;
    if (!uart_read_byte(&sync, 1000) || sync != 0x55) {
        return false;
    }

    // Recevoir keyword 1
    uint8_t kw1;
    uart_read_byte(&kw1, 100);

    // Recevoir keyword 2
    uint8_t kw2;
    uart_read_byte(&kw2, 100);

    // ACK keyword 2 (complement) après 30ms
    vTaskDelay(pdMS_TO_TICKS(30));
    uint8_t ack = ~kw2;  // ou 0xFF - kw2
    uart_write_byte(ack);

    return true;
}

// Communication bloc KWP1281
bool kwp1281_send_block(uint8_t title, uint8_t *data, uint8_t len) {
    uint8_t block[256];
    static uint8_t counter = 0;

    block[0] = len + 3;      // Length
    block[1] = counter++;    // Counter
    block[2] = title;        // Block title
    memcpy(&block[3], data, len);
    block[len + 3] = 0x03;   // End byte

    // Envoyer avec ACK inter-octets
    for (int i = 0; i < len + 4; i++) {
        uart_write_byte(block[i]);
        if (i < len + 3) {  // Pas d'ACK pour 0x03
            uint8_t ack;
            uart_read_byte(&ack, 100);
            // Vérifier: ack == ~block[i]
        }
    }
    return true;
}

// Connecter à un ECU
bool connect_ecu(uint8_t ecu_addr, uint32_t baudrate) {
    send_5baud_address(ecu_addr);
    return kwp1281_handshake(baudrate);
}

// Exemple: Connecter au Motronic 964
// connect_ecu(ECU_MOTRONIC, BAUD_964);

// Exemple: Connecter au Motronic 993
// connect_ecu(ECU_MOTRONIC, BAUD_993);
```

---

## 14. Ressources et Liens

### Téléchargement ScanTool

| Version | Lien | Status |
|---------|------|--------|
| **v3** | http://members.rennlist.com/jandreas/scantool3.zip | Actif |
| **v4** | http://dedeharter.com/scantool/scantool4.zip | **MORT** (utiliser T_OBD_Software.zip) |
| **T_OBD Software** | https://www.bergvillfx.com/products/t-obd-tool | Actif (contient v4) |

### Interfaces Hardware Compatibles

#### ATTENTION : Les adaptateurs ELM327/KKL standard NE FONCTIONNENT PAS !

Les interfaces OBD-II génériques (ELM327, KKL VAG-COM, etc.) **ne sont PAS compatibles** avec ce protocole car :

1. **Baudrate non-standard** : 8800 baud (964) n'est pas supporté par la plupart des adaptateurs USB-Série
2. **Init 5-baud via RTS** : Nécessite contrôle direct de la ligne RTS, pas juste UART TX
3. **ACK inter-octets** : Le protocole KWP1281 Porsche nécessite des ACK entre chaque octet

#### Interfaces Commerciales

| Interface | Prix | Lien | Notes |
|-----------|------|------|-------|
| **T-OBD (BERGVILL F/X)** | ~150€ | [bergvillfx.com](https://www.bergvillfx.com/products/t-obd-tool) | Officiel, USB, plug-and-play |
| **T-OBD v2** | ~180€ | [bergvillfx.com](https://www.bergvillfx.com/products/t-obd-tool2) | Version améliorée |
| **ECUFix Interface** | ~$100 | [ecufix.com](http://www.ecufix.com) | Opto-isolé, compatible ISO 9141-1 |
| **ISO 9141 Click** | ~25€ | [mikroe.com](https://www.mikroe.com/iso-9141-click) | Module L9637D prêt à l'emploi |

---

### Circuits Intégrés K-Line (ISO 9141)

Pour construire une interface hardware propre, utiliser un IC dédié K-Line :

| IC | Fabricant | Package | Datasheet | Notes |
|----|-----------|---------|-----------|-------|
| **L9637D** | STMicroelectronics | SO-8 | [PDF](https://www.st.com/resource/en/datasheet/l9637.pdf) | **Recommandé**, facile à trouver, ~1€ |
| **MC33290** | NXP (ex-Freescale) | SO-8 | [PDF](https://www.nxp.com/docs/en/data-sheet/MC33290.pdf) | Classique, remplacé par MC33660 |
| **MC33660** | NXP | SO-8 | [NXP](https://www.nxp.com) | Remplacement pin-compatible MC33290 |
| **SN65HVDA195** | Texas Instruments | SO-8 | [TI](https://www.ti.com/product/SN65HVDA195) | Moderne, excellente protection ESD |
| **SN65HVDA100** | Texas Instruments | SO-8 | [TI](https://www.ti.com/product/SN65HVDA100) | Alternative au 195 |
| **Si9241** | Vishay | SO-8 | [Vishay](https://www.vishay.com) | Moins courant |

#### Schéma Typique L9637D

```
                          +12V (VBAT)
                            │
                         [100nF]
                            │
         ┌──────────────────┴──────────────────┐
         │                L9637D               │
         │                                     │
    1 ───┤ TX        ┌─────────┐          VS ├─── +12V
         │           │         │               │
    2 ───┤ GND       │  K-Line │           K ├───────── K-Line (Pin 8)
         │           │Transceiv│               │           │
    3 ───┤ RX        │         │         ISO ├─── NC    [510Ω]
         │           └─────────┘               │           │
    4 ───┤ VCC (+5V)                      GND ├─── GND   +12V
         │                                     │
         └─────────────────────────────────────┘

         Pin 1 (TX)  ◄─── ESP32 TX (GPIO17)
         Pin 3 (RX)  ───► ESP32 RX (GPIO16)
         Pin 4 (VCC) ◄─── +5V ou +3.3V (selon variante)
         Pin 2 (GND) ◄─── GND commun
```

**Notes L9637D :**
- VCC : 5V (version standard) ou 3.3V (vérifier datasheet)
- Pull-up 510Ω sur K-Line vers +12V (intégré ou externe selon IC)
- Condensateur 100nF sur VS (alimentation 12V)
- TX/RX compatibles 3.3V pour ESP32

#### Schéma SN65HVDA195 (TI)

```
                          VBAT (+12V)
                            │
         ┌──────────────────┴──────────────────┐
         │             SN65HVDA195             │
         │                                     │
    1 ───┤ TXD                           VBB ├─── +12V
         │                                     │     │
    2 ───┤ GND                             K ├─────┼── K-Line
         │                                     │     │
    3 ───┤ RXD                            EN ├───┘  (pull-up interne)
         │                                     │
    4 ───┤ VCC (+3.3V)                   GND ├─── GND
         │                                     │
         └─────────────────────────────────────┘

         EN : Connecter à +3.3V ou GPIO pour enable/disable
```

---

### Projets Open Source ESP32 + K-Line

| Projet | IC Supportés | Protocole | Lien |
|--------|--------------|-----------|------|
| **OBD2_KLine_Library** | L9637D, MC33290, Si9241, SN65HVDA195 | ISO 9141, KWP2000 | [GitHub](https://github.com/muki01/OBD2_KLine_Library) |
| **OBD9141** | MC33290, SN65HVDA100, SN65HVDA195 | ISO 9141-2, KWP | [GitHub](https://github.com/iwanders/OBD9141) |
| **VAG_KW1281** | L9637D, MC33290 | **KW1281** (similaire Porsche!) | [GitHub](https://github.com/muki01/VAG_KW1281) |
| **OBD2_K-line_Reader** | Transistors ou ICs | ISO 9141, ISO 14230 | [GitHub](https://github.com/muki01/OBD2_K-line_Reader) |
| **OBDPlot** | Windows app | Visualisation 964/993 Motronic | [GitHub](https://github.com/jjbunn/OBDPlot) |

#### Attention : Baudrate 8800

Les bibliothèques ci-dessus sont souvent configurées pour 9600 ou 10400 baud. Pour la **964 à 8800 baud**, il faudra :

1. Vérifier que l'UART ESP32 supporte 8800 (oui, c'est le cas)
2. Modifier la configuration baudrate dans le code
3. Adapter l'init 5-baud si nécessaire

Le projet **VAG_KW1281** est le plus proche du protocole Porsche (KWP1281 avec ACK inter-octets).

---

#### Adaptateurs USB-Série Compatibles 8800 Baud

**IMPORTANT** : Tous les adaptateurs USB-Série ne supportent pas 8800 baud !

| Chipset | 8800 baud | Notes |
|---------|-----------|-------|
| **FTDI FT232R** | ✅ OUI | Recommandé, supporte baud rates non-standard |
| **FTDI FT232H** | ✅ OUI | Version plus récente |
| **Prolific PL2303** | ⚠️ Variable | Certaines versions OK, d'autres non |
| **CH340/CH341** | ❌ NON | Ne supporte pas 8800 baud |
| **CP2102** | ⚠️ Variable | Tester avant d'acheter |

**Drivers FTDI** : https://ftdichip.com/drivers/

Le package T_OBD_Software.zip inclut les drivers FTDI : `CDM v2.12.24 WHQL Certified.zip`

### Adaptateur 19 Broches → OBD-II

Pour les 964 et 993 early (1994-1995/1), un adaptateur du connecteur 19 broches Porsche vers OBD-II 16 broches est nécessaire.

| Vendeur | Produit | Lien |
|---------|---------|------|
| **BERGVILL F/X** | 19-pin adapter | [bergvillfx.com](https://www.bergvillfx.com/products/t-obd-tool) (vendu séparément) |
| **Pelican Parts** | Diagnostic adapters | [pelicanparts.com](https://www.pelicanparts.com/catalog/SuperCat/911L/POR_911L_ENGTOL_pg1.htm) |

### Forums et Documentation

| Ressource | Lien |
|-----------|------|
| **Rennlist 964 Forum** | https://rennlist.com/forums/964-forum/ |
| **Rennlist 993 Forum** | https://rennlist.com/forums/993-forum/ |
| **964 Diagnostic FAQ** | https://rennlist.com/forums/964-forum/280358-964-diagnostic-tool-faq.html |
| **Pelican Parts Forum** | http://forums.pelicanparts.com/porsche-911-technical-forum/ |
| **PFF.de (Allemand)** | https://www.pff.de/ |

### Alternatives Commerciales

Pour ceux qui préfèrent une solution commerciale complète :

| Outil | Prix | Modèles | Lien |
|-------|------|---------|------|
| **Durametric** | ~$400 | 964, 993, 996, 997... | [durametric.com](https://www.durametric.com/) |
| **PIWIS** | $$$$ | Tous Porsche | Outil officiel Porsche |

---

## 15. Conclusion

Le reverse engineering de ScanTool v3 et v4 révèle:

1. **Mécanisme 5-baud**: Utilise RTS comme TX bit-banging (pas le UART)
2. **Timing critique**: 200ms/bit pour init, 30ms avant ACK keyword
3. **Baudrate configurable**: 9600 par défaut, 8800 pour 964 via fichier cfg
4. **Protocol KWP1281**: ACK par complément à 1 (0xFF - byte)
5. **Hardware simple**: Transistor + pull-up 510Ω suffisent
6. **Adaptateurs génériques incompatibles**: ELM327/KKL ne fonctionnent PAS

### Différences clés 964 vs 993:

| Aspect | 964 | 993 |
|--------|-----|-----|
| Motronic baudrate | 8800 | 9600 |
| ABS adresse | 0x3D | 0x1F |
| ABS baudrate | 4800 | 9600 |
| Drive Block | Non | Oui (workaround) |
| RPM registre | 0x3A | 0x39 |

### Nouveautés v4 vs v3:

- System Adaptation (+60s timeout)
- Support Alarm (0x40)
- Support Tiptronic (0x29)
- CSV logging avec timestamp
- Support UINT16 pour valeurs 16-bit
- Configs pré-faites 964/993 en °C et °F

### Pour implémenter sur ESP32:

1. Utiliser GPIO pour init 5-baud (pas UART)
2. Configurer UART à 8800 (964) ou 9600 (993) après handshake
3. Implémenter ACK inter-octets (0xFF - byte)
4. Interface hardware : 2N7000 + 510Ω pull-up + diviseur tension RX
5. Adaptateur 19-pin si véhicule pré-1996

Ces informations permettent une implémentation complète sur ESP32 sans dépendre du logiciel Windows original.

---

*Document généré par reverse engineering de ScanTool.exe v3 (2004) et v4 (2006)*
*Auteur original du logiciel: Doug Boyce*
*Analyse: Claude Code - Janvier 2026*
