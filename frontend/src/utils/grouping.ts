import type { Game, GameGroup } from '../types/game'

// Le titre nettoye cote backend garde un suffixe "- Nom du DLC" quand il
// provient d'un nom de fichier du style "Jeu - Nom du DLC.ext" ; on s'en sert
// comme cle de regroupement pour reunir base/update/DLC d'un meme jeu.
// Les symboles ™/®/© sont retires de la cle car ils sont ajoutes de facon
// incoherente selon la source (ex: le fichier de base d'un jeu Switch n'a
// parfois pas le "™" que son update/DLC ont).
function rootTitle(title: string): string {
  return title
    .split(' - ')[0]
    .replace(/[™®©]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

export function groupGames(games: Game[]): GameGroup[] {
  const groups = new Map<string, Game[]>()
  for (const game of games) {
    const key = `${game.platform}::${rootTitle(game.title)}`
    const list = groups.get(key)
    if (list) list.push(game)
    else groups.set(key, [game])
  }

  return [...groups.entries()].map(([key, variants]) => {
    const sorted = [...variants].sort((a, b) => b.size - a.size)
    return { key, primary: sorted[0], variants: sorted }
  })
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
