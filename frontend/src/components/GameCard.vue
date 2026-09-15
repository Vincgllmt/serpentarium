<script setup lang="ts">
import { API_URL } from '../config'
import type { Game } from '../types/game'

const { game } = defineProps<{ game: Game }>()

const downloadUrl = `${API_URL}/api/games/${game.id}/download`
// cover_url est soit une jaquette mise en cache localement (chemin relatif
// /covers/...), soit (ancien scrape) une URL distante absolue.
const coverUrl = game.cover_url?.startsWith('/') ? `${API_URL}${game.cover_url}` : game.cover_url
</script>

<template>
  <a
    :href="downloadUrl"
    class="group relative block aspect-[3/4] overflow-hidden rounded-xl bg-zinc-800 shadow-lg shadow-black/30 transition-transform duration-200 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/50"
  >
    <img
      v-if="coverUrl"
      :src="coverUrl"
      :alt="game.title"
      class="h-full w-full object-cover"
      loading="lazy"
    />
    <div
      v-else
      class="flex h-full w-full items-center justify-center bg-gradient-to-br from-indigo-700 via-purple-700 to-zinc-900 p-4 text-center"
    >
      <span class="text-sm font-semibold text-white/80">{{ game.title }}</span>
    </div>

    <div
      class="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
    >
      <span class="rounded-full bg-white/10 p-3 ring-1 ring-white/30">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6 text-white">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0-4-4m4 4 4-4M5 21h14" />
        </svg>
      </span>
    </div>

    <div
      class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-3 pt-8"
    >
      <h3 class="truncate text-sm font-semibold text-white">{{ game.title }}</h3>
      <p class="text-xs text-white/60">{{ game.platform }}<span v-if="game.year"> · {{ game.year }}</span></p>
    </div>
  </a>
</template>
