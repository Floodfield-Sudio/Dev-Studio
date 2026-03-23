# DevStudio Pro

**IDE Python + Builder de mods Minecraft** — tout-en-un, sans droits administrateur.

[![License: Polyform NC 1.0](https://img.shields.io/badge/License-Polyform%20NC%201.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

---

## Fonctionnalités

### 🐍 Mode Python
- Éditeur multi-onglets avec coloration syntaxique complète (mots-clés, builtins, docstrings, f-strings…)
- Numéros de ligne, repli des blocs `class`/`def`, surbrillance ligne courante
- Auto-injection des dépendances pip à la sauvegarde
- Build `.exe` / binaire Linux/macOS via PyInstaller
- Système de versions dev → stable
- MàJ automatique de l'app publiée (via GitHub Releases) *-En cours de développement* 

### ⛏ Mode Minecraft
- Loaders supportés : **Forge**, **NeoForge**, **Fabric**, **Quilt**
- Versions : 1.7.10, 1.12.2, 1.16.5, 1.18.2, 1.19.x, 1.20.x, 1.21.x
- JDK 8 / 17 / 21 téléchargé automatiquement (sans droits admin)
- Compilation `gradlew build` avec logs en temps réel
- Injection automatique du Gradle wrapper depuis le MDK en cache

### 🎮 Instances Minecraft
- Instances isolées Vanilla / Forge / NeoForge / Fabric / Quilt
- Mode **OFFLINE total** — aucun compte Mojang requis
- Lancement solo (singleplayer) hors-ligne
- Serveur local dédié (LAN / multijoueur, `online-mode=false`)
- Copie automatique du mod compilé dans chaque instance
- Terminal serveur intégré (commandes `/op`, `/say`, etc.)

### 🐙 GitHub 
*-en cours de développement*
- `git status / add / commit / push`
- Création de Releases GitHub avec upload automatique du `.jar` ou `.exe`
- Token stocké dans les paramètres (saisi une seule fois)

---

## Installation

### Windows
1. Téléchargez [Python 3.10+](https://python.org) — cochez **"Add Python to PATH"**
2. Téléchargez `DevStudioPro.pyw` et `run.bat` depuis les [Releases](../../releases)
3. Placez les deux fichiers dans le **même dossier**
4. Double-cliquez sur `run.bat`

L'app s'installe dans `%APPDATA%\FFS\DevStudio\`, PyQt6 est installé automatiquement.

### macOS / Linux
```bash
# Téléchargez DevStudioPro.pyw et run.sh
chmod +x run.sh
./run.sh
```

---

## Utilisation rapide

### Projet Python
1. **📂 Ouvrir projet** → sélectionner le dossier
2. Éditer les fichiers (double-clic dans l'explorateur)
3. **▶ Exécuter (F5)** pour tester
4. Onglet **🐍 Python** → renseigner Nom, version, GitHub repo
5. **🔧 Build DEV** → génère l'exe + `_updater.py` + installeurs

### Mod Minecraft
1. Ouvrir le dossier du mod (détection automatique si `gradlew` présent)
2. Onglet **⛏ Minecraft** → choisir loader + version MC
3. Télécharger le JDK si nécessaire (bouton automatique)
4. **🔨 Build** → compile, les logs défilent en temps réel
5. Onglet **🎮 Instances** → créer une instance, installer, lancer

---

## Structure générée (build Python)

```
mon-projet/
├── version_info.py     ← version courante (généré)
├── _updater.py         ← module de MàJ auto (généré)
├── version.json        ← canaux dev / stable (généré)
├── install_dev.bat     ← installeur Windows (généré)
├── install_dev.sh      ← installeur Linux/macOS (généré)
└── dist/
    ├── dev/
    │   └── MonApp.exe  ← build de développement
    └── stable/
        └── MonApp.exe  ← build public après promotion
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
