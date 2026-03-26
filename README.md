# [🛠 DevStudio Pro](https://github.com/Floodfield-Sudio/Dev-Studio)

**IDE Python + Builder de mods Minecraft** — tout-en-un, sans droits administrateur.

[![License: Polyform NC 1.0](https://img.shields.io/badge/License-Polyform%20NC%201.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-yellow.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52.svg)](https://pypi.org/project/PyQt6/)

---

## ✨ Fonctionnalités

### 🐍 Mode Python
- Éditeur multi-onglets avec coloration syntaxique complète — mots-clés, builtins, docstrings `"""` / `'''`, f-strings, commentaires
- Numéros de ligne, repli des blocs `class`/`def`, surbrillance ligne courante
- Auto-injection des dépendances pip à la sauvegarde (analyse AST)
- Build `.exe` / binaire Linux / macOS via **PyInstaller** (intégré, installation automatique)
- Génération automatique de `_updater.py` — MàJ silencieuse depuis GitHub Releases au démarrage
- Génération de `installer.pyw` — installeur graphique modulaire à distribuer aux utilisateurs
- Versioning **DEV → STABLE** avec tag Git et Release GitHub en un clic

### ⛏ Mode Minecraft Java
- Loaders supportés : **Forge**, **NeoForge**, **Fabric**, **Quilt**
- Versions MC : 1.7.10, 1.12.2, 1.16.5, 1.18.2, 1.19.x, 1.20.x, 1.21.x
- JDK 8 / 17 / 21 téléchargé automatiquement dans le dossier applicatif (sans droits admin)
- Compilation `gradlew build` avec logs colorés temps réel
- Injection automatique du Gradle wrapper depuis le MDK en cache (plus besoin de commiter `gradlew`)
- Téléchargement et cache du MDK par loader/version

### 🎮 Instances Minecraft
- Instances isolées **Vanilla / Forge / NeoForge / Fabric / Quilt**
- Mode **OFFLINE total** — aucun compte Mojang requis, UUID déterministe
- Réutilisation automatique des assets d'un `.minecraft` existant
- Copie automatique du mod compilé dans les instances après build
- Lancement solo en un clic
- **Serveur local dédié** (LAN / multijoueur, `online-mode=false`)
  - Terminal serveur intégré avec envoi de commandes (`/op`, `/gamemode`…)
  - Suppression automatique du `session.lock` avant démarrage

### 🐙 GitHub
- Système de **sync par dossier** : chaque projet a son clone git local dans `.devstudio/github/`
- Seuls les fichiers listés dans `.devstudio/github_files.txt` sont publiés — les JDK, instances, caches ne remontent jamais
- Push vers un dépôt existant (avec ou sans fichiers déjà présents) — fusion automatique des historiques
- Création de **Release GitHub** avec upload d'asset (`.jar`, `.exe`) — URL-encoding automatique des noms
- Token stocké de façon persistante (QSettings)

### ⚙ Modules
- Architecture modulaire : activez/désactivez Python, Minecraft, Instances, GitHub indépendamment
- Les onglets correspondants apparaissent ou disparaissent dynamiquement

---

## 📥 Installation

### Windows
1. Télécharger **Python 3.10+** sur [python.org](https://python.org) — cocher *"Add to PATH"*
2. Télécharger `DevStudioPro.pyw` et `run.bat` depuis la dernière [Release](../../releases)
3. Double-cliquer sur `run.bat` — PyQt6 s'installe automatiquement au premier lancement

### macOS / Linux
```bash
# Télécharger DevStudioPro.pyw et run.sh
chmod +x run.sh && ./run.sh
```

> Les dépendances Python (PyQt6…) s'installent automatiquement dans un venv isolé.

---

## 🗂 Structure des données

```
Windows : %USERPROFILE%\AppData\Roaming\FFS\DevStudio\
macOS   : ~/Library/Application Support/FFS/DevStudio/
Linux   : ~/.local/share/FFS/DevStudio/

FFS\DevStudio\
├── jdk\jdk8|jdk17|jdk21\     ← JDKs partagés (téléchargés une seule fois)
├── mdk\<Loader>\<version>\   ← MDK Forge/Fabric… en cache
├── mc\
│   ├── versions\             ← Client MC partagé entre toutes les instances
│   ├── libraries\            ← Libs Maven partagées
│   ├── assets\               ← Assets partagés
│   ├── forge_installers\     ← Installeurs Forge réutilisés
│   └── instances\<nom>\
│       ├── game\             ← Dossier .minecraft de l'instance
│       └── server\           ← Serveur dédié de l'instance
└── logs\                     ← Logs de session horodatés
```

---

## 🔨 Build depuis les sources

```bash
git clone https://github.com/Floodfield-Sudio/Dev-Studio.git
cd Dev-Studio
python DevStudioPro.pyw
```

Aucune dépendance à installer manuellement — tout est géré au démarrage.

---

## ⚙ Modules disponibles

| Module | Description |
|---|---|
| 🐍 **Python** | IDE, build EXE, versioning, MàJ auto |
| ⛏ **Minecraft Java** | Build mods Forge/NeoForge/Fabric/Quilt |
| 🎮 **Instances MC** | Instances offline, serveur LAN |
| 🐙 **GitHub** | Sync, push, releases |
| 🔄 **MàJ automatique** | Générateur d'installeur + launcher |

---

## 📸 Aperçu

> *(screenshots à venir)*

---

## 🔮 Roadmap

- [ ] Support C/C++ (compilation CMake)
- [ ] Support NeoForge 1.21.4 instances
- [ ] Dark mode personnalisable (thèmes)
- [ ] Éditeur YAML/TOML avec schéma

---

## 📜 Licence

Ce projet est distribué sous la licence **Polyform Noncommercial 1.0.0**.

✅ **Autorisé :** usage personnel, modification, redistribution non-commerciale, usage associatif ou éducatif  
❌ **Interdit :** vendre le logiciel ou l'accès à celui-ci, l'inclure dans un produit commercial

Voir [LICENSE](LICENSE) pour les détails complets.

---

## 📬 Contact

Ouvre une [issue](../../issues) pour les bugs ou suggestions.  
Voir nos autres projets sur [Notre Site Web](https://floodfield-sudio.github.io/FFS.index/)
