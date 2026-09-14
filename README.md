# Serpentarium

Bibliotheque personnelle pour visualiser une collection de ROMs perso : scan du
dossier `roms/`, recuperation automatique des jaquettes/metadonnees, et acces
depuis le reseau local (ex: Steam Deck) pour telecharger les jeux.

Projet perso, non commercial : les ROMs elles-memes ne sont jamais commit ni
redistribuees.

## Structure

```
roms/           Tes ROMs (jamais commit, voir .gitignore)
  emulator/     Exclu du scan de jeux, liste sur la page "Emulateurs"
backend/        API FastAPI (scan, base SQLite, IGDB, telechargement, mDNS)
frontend/       Interface Vue 3 + Tailwind
```

## Backend

Prerequis : Python 3.11+.

```bash
cd backend
python -m venv .venv
./.venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip sous Linux/Mac
cp .env.example .env
```

Remplis `backend/.env` (jamais commit) :

- `ROMS_DIR` : chemin vers le dossier `roms/` (par defaut `../roms`)
- `EMULATORS_DIRNAME` : sous-dossier de `ROMS_DIR` exclu du scan (par defaut `emulator`)
- `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` : identifiants Twitch Developer Console
  (https://dev.twitch.tv/console/apps, libre-service) pour recuperer jaquettes/annee
- `SS_*` : identifiants ScreenScraper.fr (necessite un compte dev approuve
  manuellement par leur equipe ; en attendant, IGDB est la source active)

Lancer le serveur (accessible sur le reseau local) :

```bash
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Au demarrage, le backend annonce aussi `serpentarium.local` sur le reseau via
mDNS (Zeroconf), pour y acceder sans connaitre l'IP locale.

### API

- `GET /api/games` — liste des jeux scannes
- `POST /api/scan` — (re)scanne `ROMS_DIR` (extensions connues, lit le CRC32
  a l'interieur des archives `.zip`/`.7z` sans les extraire)
- `POST /api/games/{id}/enrich` — recupere titre/jaquette/annee via IGDB
- `POST /api/enrich-all` — enrichit tous les jeux (avec pause anti rate-limit)
- `GET /api/games/{id}/download` — telecharge le fichier (supporte les
  requetes `Range`, donc reprise possible en cas de coupure)
- `GET /api/emulators` — liste les dossiers presents sous `roms/emulator/`

## Frontend

Prerequis : Node.js 18+.

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Deux pages : **Bibliotheque** (grille de jeux, scan, enrichissement, clic sur
une jaquette pour telecharger) et **Emulateurs** (contenu de `roms/emulator/`).

L'URL de l'API est deduite dynamiquement du nom d'hote utilise pour charger
la page (`frontend/src/config.ts`), donc ca fonctionne aussi bien en
`localhost`, en IP LAN qu'en `serpentarium.local`.

## Acces depuis un autre appareil du reseau local (ex: Steam Deck)

Une fois les deux serveurs lances avec `--host 0.0.0.0` :

- Par IP : `http://<IP-du-PC>:5173/`
- Par nom (mDNS, marche nativement sur SteamOS/Linux/Mac, sans rien
  configurer côté appareil) : `http://serpentarium.local:5173/`

Si un pare-feu Windows bloque la connexion, autoriser Python/Node sur les
reseaux prives lors du premier lancement.

## Limites connues

- Le matching IGDB se fait par recherche de titre (pas par hash), donc plus
  sensible aux ROMs mal nommees que ne le serait ScreenScraper.
- Le telechargement sert le fichier tel qu'il est sur le disque : une ROM en
  `.7z`/`.zip` est telechargee sous cette forme, pas extraite.
- `SS_DEVID`/`SS_DEVPASSWORD` restent vides tant qu'un compte dev
  ScreenScraper n'a pas ete valide manuellement par leur equipe ; le client
  (`backend/app/screenscraper.py`) est pret mais inactif en attendant.
