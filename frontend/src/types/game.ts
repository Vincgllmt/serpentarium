export interface Game {
  id: number
  title: string
  platform: string
  filename: string
  size: number
  crc32: string | null
  cover_url: string | null
  year: number | null
  source: string | null
}

// Plusieurs fichiers (base / mise a jour / DLC d'un meme jeu Switch, par
// exemple) regroupes sous une seule tuile dans la bibliotheque.
export interface GameGroup {
  key: string
  primary: Game
  variants: Game[]
}
