# DevStudio Pro

IDE Python + Builder de mods Minecraft (Forge/NeoForge/Fabric/Quilt)

## Fonctionnalités
- Éditeur multi-onglets avec coloration syntaxique (Python, Java, Groovy)
- Build de mods Minecraft avec JDK auto-téléchargé
- Instances Minecraft offline (aucun compte requis)
- Serveur local de test
- Build Python → .exe avec système de MàJ automatique
- Intégration GitHub (commit, push, releases)

## Installation

### Windows
1. Téléchargez Python 3.10+ sur https://python.org (cochez "Add to PATH")
2. Téléchargez `run.bat` et `DevStudioPro.pyw`
3. Double-cliquez sur `run.bat`

### macOS / Linux
```bash
chmod +x run.sh && ./run.sh
```

## Licence
CC BY-NC 4.0 — Usage non-commercial uniquement.
Voir [LICENSE](LICENSE).
```

**`.gitignore`** (évite de pousser des fichiers inutiles)
```
# DevStudio Pro
.venv/
__pycache__/
*.pyc
dist/
build/

# Minecraft / Java
.jdk/
mc/
mdk/
*.log

# IDE
.vscode/
.idea/
