<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import GameCard from '../components/GameCard.vue'
import { API_URL } from '../config'
import type { Game } from '../types/game'

const games = ref<Game[]>([])
const query = ref('')
const selectedPlatform = ref('')
const loading = ref(false)
const scanning = ref(false)
const enriching = ref(false)
const error = ref('')

async function loadGames() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_URL}/api/games`)
    if (!res.ok) throw new Error('Impossible de charger la bibliotheque')
    games.value = await res.json()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    loading.value = false
  }
}

async function triggerScan() {
  scanning.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_URL}/api/scan`, { method: 'POST' })
    if (!res.ok) throw new Error('Le scan a echoue')
    await loadGames()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    scanning.value = false
  }
}

async function triggerEnrich() {
  enriching.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_URL}/api/enrich-all`, { method: 'POST' })
    if (!res.ok) throw new Error("L'enrichissement a echoue")
    await loadGames()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    enriching.value = false
  }
}

onMounted(loadGames)

const platforms = computed(() =>
  [...new Set(games.value.map((game) => game.platform))].sort((a, b) => a.localeCompare(b)),
)

const filteredGames = computed(() =>
  games.value
    .filter((game) => game.title.toLowerCase().includes(query.value.toLowerCase()))
    .filter((game) => !selectedPlatform.value || game.platform === selectedPlatform.value),
)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center gap-3">
      <input
        v-model="query"
        type="text"
        placeholder="Rechercher un jeu..."
        class="w-full max-w-xs rounded-lg bg-white/5 px-4 py-2 text-sm outline-none ring-1 ring-white/10 placeholder:text-zinc-500 focus:ring-indigo-500"
      />
      <select
        v-model="selectedPlatform"
        class="rounded-lg bg-white/5 px-4 py-2 text-sm outline-none ring-1 ring-white/10 focus:ring-indigo-500"
      >
        <option value="">Toutes les plateformes</option>
        <option v-for="platform in platforms" :key="platform" :value="platform">{{ platform }}</option>
      </select>
      <button
        :disabled="scanning"
        class="whitespace-nowrap rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        @click="triggerScan"
      >
        {{ scanning ? 'Scan en cours...' : 'Scanner roms/' }}
      </button>
      <button
        :disabled="enriching"
        class="whitespace-nowrap rounded-lg bg-white/5 px-4 py-2 text-sm font-medium text-white ring-1 ring-white/10 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
        @click="triggerEnrich"
      >
        {{ enriching ? 'Enrichissement...' : 'Enrichir les jaquettes' }}
      </button>
    </div>

    <p v-if="error" class="mb-6 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
      {{ error }}
    </p>
    <p v-else-if="loading" class="mb-6 text-sm text-zinc-400">Chargement...</p>
    <p v-else class="mb-6 text-sm text-zinc-400">{{ filteredGames.length }} jeu(x)</p>

    <div class="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      <GameCard v-for="game in filteredGames" :key="game.id" :game="game" />
    </div>
  </div>
</template>
