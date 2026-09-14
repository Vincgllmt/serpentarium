export interface Game {
  id: number
  title: string
  platform: string
  filename: string
  size: number
  crc32: string | null
  cover_url: string | null
  year: number | null
}
