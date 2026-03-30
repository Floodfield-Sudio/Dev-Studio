# [DevStudio Pro](https://github.com/Floodfield-Sudio/Dev-Studio)

**IDE Python + Builder de mods Minecraft** — tout-en-un, sans droits administrateur.

[![License: Polyform NC 1.0](https://img.shields.io/badge/License-Polyform%20NC%201.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

---

## Fonctionnalités

### 🐍 Mode Python
- Éditeur multi-onglets avec coloration syntaxique complète (mots-clés, builtins, docstrings `"""` / `'''`, f-strings…)
- Numéros de ligne, repli des blocs `class`/`def`, surbrillance ligne courante
- Auto-injection des dépendances pip à la sauvegarde
- Build `.exe` / binaire Linux/macOS via PyInstaller (`--onefile`)
- Système de versions **dev → stable** avec promotion en un clic
- `_updater.py` embarqué : vérification des MàJ au démarrage via GitHub Releases
- Génération automatique de `installer.pyw` — installeur modulaire compilable en `.exe`

### ⛏ Mode Minecraft
- Loaders supportés : **Forge**, **NeoForge**, **Fabric**, **Quilt**
- Versions : 1.7.10, 1.12.2, 1.16.5, 1.18.2, 1.19.x, 1.20.x, 1.21.x
- JDK 8 / 17 / 21 téléchargé automatiquement (sans droits admin)
- Compilation `gradlew build` avec logs en temps réel et coloration
- Injection automatique du Gradle wrapper depuis le MDK en cache
- Création de nouveaux projets mod depuis le MDK (Forge, NeoForge, Fabric, Quilt)

### 🎮 Instances Minecraft
- Instances isolées Vanilla / Forge / NeoForge / Fabric / Quilt
- Mode **OFFLINE total** — aucun compte Mojang requis
- Lancement solo (singleplayer) hors-ligne
- Serveur local dédié (LAN / multijoueur, `online-mode=false`)
- Copie automatique du mod compilé dans chaque instance après build
- Terminal serveur intégré (commandes `/op`, `/say`, `/stop`, etc.)
- Ressources partagées entre toutes les instances (un seul téléchargement)

### 🐙 GitHub
- Système de **sync par dossier** : seuls les fichiers listés dans `github_files.txt` sont publiés
- Clone / connexion d'un dépôt existant (avec ou sans fichiers distants déjà présents)
- `git add + commit + push` en un clic — **⬆ Sync + Push**
- Pull pour récupérer les modifications distantes
- Création de Releases GitHub avec upload automatique du `.jar` ou `.exe`
- Token stocké dans les paramètres (saisi une seule fois)

### ⚙ Modules
- Architecture modulaire : activez/désactivez chaque fonctionnalité indépendamment
- Modules disponibles : Python, Minecraft Java, Instances MC, GitHub, MàJ automatique
- Extensible (C/C++, autres langages…)

---

## Distribution

### Comment ça fonctionne

Le **Build DEV** (onglet 🐍 Python) génère automatiquement :

| Fichier | Rôle |
|---|---|
| `dist/dev/MonApp.exe` | Exécutable compilé (dev) |
| `dist/stable/MonApp.exe` | Exécutable public (après promotion) |
| `version_info.py` | Version courante importée par l'app |
| `_updater.py` | Module de MàJ automatique à intégrer dans votre app |
| `version.json` | Canaux dev / stable |
| `install_dev.bat` / `.sh` | Installeurs directs pour les utilisateurs finaux |
| `installer.pyw` | Installeur modulaire (compilable en `.exe`) |

### Intégrer les MàJ automatiques dans votre app

Ajoutez ces deux lignes au démarrage de votre `main.py` :

```python
from _updater import check_and_update
check_and_update()  # silencieux si à jour, télécharge et relance si nouvelle version
```

Au lancement, l'app vérifie GitHub Releases. Si une nouvelle version est disponible, elle se télécharge et se remplace automatiquement. Si pas d'internet → l'app démarre normalement.

### Cycle de release

```
[Développement]  →  🔧 Build DEV  →  Tests
                                        ↓
                              🚀 Promouvoir DEV → STABLE
                                        ↓
                         Onglet 🐙 GitHub → Créer Release
                         (joint dist/stable/MonApp.exe)
                                        ↓
                    Les utilisateurs reçoivent la MàJ automatiquement
                    au prochain lancement de l'app
```

---

## Installation

### Windows
1. Téléchargez [Python 3.10+](https://python.org) — cochez **"Add Python to PATH"**
2. Téléchargez `DevStudioPro.pyw` et `run.bat` depuis les [Releases](../../releases)
3. Placez les deux fichiers dans le **même dossier**
4. Double-cliquez sur `run.bat`

L'app s'installe dans `%APPDATA%\FFS\DevStudio\`, PyQt6 est installé automatiquement au premier lancement.

### macOS / Linux
```bash
# Téléchargez DevStudioPro.pyw et run.sh dans le même dossier
chmod +x run.sh
./run.sh
```

---

## Utilisation rapide

### Projet Python
1. **📂 Ouvrir projet** → sélectionner le dossier
2. Éditer les fichiers (double-clic dans l'explorateur)
3. **▶ Exécuter (F5)** pour tester
4. Onglet **🐍 Python** → renseigner Nom, version, GitHub repo, point d'entrée
5. **🔧 Build DEV** → génère l'exe + `_updater.py` + `installer.pyw`
6. Tester le build, puis **🚀 Promouvoir DEV → STABLE**
7. Onglet **🐙 GitHub** → **Créer Release** + joindre l'exe

### Mod Minecraft
1. Ouvrir le dossier du mod (détection automatique si `gradlew` présent)
2. Onglet **⛏ Minecraft** → choisir loader + version MC
3. Télécharger le JDK si nécessaire (bouton automatique)
4. **⬇ Télécharger MDK** (une seule fois par loader/version)
5. **🔨 Build** → compile, les logs défilent en temps réel
6. Onglet **🎮 Instances** → créer une instance, installer, lancer en solo ou serveur LAN

### Publier sur GitHub
1. Onglet **🐙 GitHub** → renseigner Remote URL + Token
2. **⬇ Cloner / Connecter** le dépôt (gère les dépôts déjà existants avec fichiers)
3. Lister les fichiers à publier dans la zone **Fichiers publiés**
4. Écrire un message de commit → **⬆ Sync + Push**

---

## Structure générée (build Python)

```
mon-projet/
├── main.py                 ← votre code
├── version_info.py         ← version courante (généré automatiquement)
├── _updater.py             ← module MàJ auto (généré — à importer dans main.py)
├── version.json            ← canaux dev / stable (généré)
├── installer.pyw           ← installeur modulaire (généré — compilable en .exe)
├── install_dev.bat         ← installeur direct Windows (généré)
├── install_dev.sh          ← installeur direct Linux/macOS (généré)
├── .devstudio/
│   ├── github/             ← clone git local (dossier de sync GitHub)
│   └── github_files.txt    ← liste des fichiers à publier sur GitHub
└── dist/
    ├── dev/
    │   └── MonApp.exe      ← build de développement
    └── stable/
        └── MonApp.exe      ← build public (après promotion DEV → STABLE)
```

---

## Licence

**Polyform Noncommercial License 1.0.0** — utilisation non-commerciale uniquement.

Vous pouvez librement utiliser, modifier et partager ce logiciel pour tout usage **personnel, éducatif, associatif ou de recherche**. Tout usage commercial est interdit sans accord préalable.

Voir [LICENSE](LICENSE) pour le texte complet.

---

## Crédits

Développé par [Floodfield-Sudio](https://github.com/Floodfield-Sudio).  
Construit avec [PyQt6](https://pypi.org/project/PyQt6/), [PyInstaller](https://pyinstaller.org).  
Voir nos autres projets : [Notre Site Web](https://floodfield-sudio.github.io/FFS.index/).
