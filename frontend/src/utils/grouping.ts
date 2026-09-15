import type { Game, GameGroup } from '../types/game'

const KEY_SEP = '::'

// Les symboles ™/®/© sont retires car ajoutes de facon incoherente selon la
// source (ex: le fichier de base d'un jeu Switch n'a parfois pas le "™" que
// son update/DLC ont), sinon des variantes du meme jeu ne matcheraient pas.
function normalizedTitle(title: string): string {
  return title.replace(/[™®©]/g, '').replace(/\s+/g, ' ').trim()
}

function groupKey(game: Game): string {
  return `${game.platform}${KEY_SEP}${normalizedTitle(game.title)}`
}

export function groupGames(games: Game[]): GameGroup[] {
  // 1) Regroupe d'abord par titre exact (une fois normalise) : ca suffit a
  // reunir base + update, qui partagent generalement le meme titre nettoye.
  const exactGroups = new Map<string, Game[]>()
  for (const game of games) {
    const key = groupKey(game)
    const list = exactGroups.get(key)
    if (list) list.push(game)
    else exactGroups.set(key, [game])
  }

  // 2) Un titre du style "Jeu - Sous-titre" (DLC) est rattache au groupe
  // "Jeu" SEULEMENT si ce titre exact existe deja parmi les jeux scannes.
  // Sans cette verification, des suites numerotees ("Serie - Episode 2")
  // qui utilisent le meme separateur seraient a tort prises pour du DLC.
  const parentOf = new Map<string, string>()
  for (const key of exactGroups.keys()) {
    const sepIndex = key.indexOf(KEY_SEP)
    const platform = key.slice(0, sepIndex)
    const title = key.slice(sepIndex + KEY_SEP.length)
    const dashIndex = title.indexOf(' - ')
    if (dashIndex === -1) continue

    const parentKey = `${platform}${KEY_SEP}${title.slice(0, dashIndex)}`
    if (parentKey !== key && exactGroups.has(parentKey)) {
      parentOf.set(key, parentKey)
    }
  }

  const groups: GameGroup[] = []
  for (const [key, list] of exactGroups) {
    if (parentOf.has(key)) continue // fusionne dans le groupe parent ci-dessous

    const childLists = [...exactGroups.entries()]
      .filter(([childKey]) => parentOf.get(childKey) === key)
      .map(([, childList]) => childList)

    const variants = [list, ...childLists].flat().sort((a, b) => b.size - a.size)
    groups.push({ key, primary: variants[0], variants })
  }
  return groups
}

export function partLabel(game: Game, group: GameGroup): string {
  const name = game.filename.toLowerCase()
  if (/\[base\]/.test(name)) return 'Jeu de base'
  if (/\[upd(ate)?\]/.test(name)) return 'Mise a jour'
  if (/dlc/.test(name)) {
    const suffix = game.title.split(' - ').slice(1).join(' - ')
    return suffix || 'DLC'
  }
  return game.id === group.primary.id ? 'Fichier principal' : 'Fichier additionnel'
}
