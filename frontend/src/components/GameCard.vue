<script setup lang="ts">
import { computed, ref } from 'vue'
import { API_URL } from '../config'
import type { Game } from '../types/game'

const { game } = defineProps<{ game: Game }>()
const emit = defineEmits<{ updated: [game: Game] }>()

const downloadUrl = `${API_URL}/api/games/${game.id}/download`
// cover_url est soit une jaquette mise en cache localement (chemin relatif
// /covers/...), soit (ancien scrape) une URL distante absolue.
const coverUrl = computed(() =>
  game.cover_url?.startsWith('/') ? `${API_URL}${game.cover_url}` : game.cover_url,
)

const rescraping = ref(false)
const rescrapeError = ref(false)

async function rescrape() {
  rescraping.value = true
  rescrapeError.value = false
  try {
    const res = await fetch(`${API_URL}/api/games/${game.id}/enrich?force=true`, { method: 'POST' })
    if (!res.ok) throw new Error('echec du rescrape')
    emit('updated', await res.json())
  } catch {
    rescrapeError.value = true
  } finally {
    rescraping.value = false
  }
}
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

    <button
      type="button"
      title="Recharger les infos de ce jeu"
      :disabled="rescraping"
      class="absolute right-2 top-2 rounded-full bg-black/60 p-1.5 opacity-0 ring-1 ring-white/20 transition-opacity duration-200 hover:bg-black/80 group-hover:opacity-100 disabled:cursor-wait disabled:opacity-100"
      @click.stop.prevent="rescrape"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        class="h-4 w-4 text-white"
        :class="{ 'animate-spin': rescraping }"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99"
        />
      </svg>
    </button>
    <span
      v-if="rescrapeError"
      title="Le rechargement a echoue"
      class="absolute right-1 top-1 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-zinc-900"
    ></span>

    <div
      class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-3 pt-8"
    >
      <h3 class="truncate text-sm font-semibold text-white">{{ game.title }}</h3>
      <p class="text-xs text-white/60">{{ game.platform }}<span v-if="game.year"> · {{ game.year }}</span></p>
    </div>
  </a>
</template>
