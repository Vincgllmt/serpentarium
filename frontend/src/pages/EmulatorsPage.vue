<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { API_URL } from '../config'
import type { Emulator } from '../types/emulator'
import { formatBytes } from '../utils/format'

const emulators = ref<Emulator[]>([])
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  loading.value = true
  try {
    const res = await fetch(`${API_URL}/api/emulators`)
    if (!res.ok) throw new Error('Impossible de charger les emulateurs')
    emulators.value = await res.json()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Erreur inconnue'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <p v-if="error" class="mb-6 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
      {{ error }}
    </p>
    <p v-else-if="loading" class="mb-6 text-sm text-zinc-400">Chargement...</p>

    <p v-else-if="!emulators.length" class="text-sm text-zinc-400">
      Aucun emulateur trouve dans <code class="text-zinc-300">roms/emulator/</code>.
    </p>

    <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
      <article
        v-for="emulator in emulators"
        :key="emulator.name"
        class="rounded-xl bg-zinc-800/60 p-5 ring-1 ring-white/5"
      >
        <h3 class="text-lg font-semibold capitalize text-white">{{ emulator.name }}</h3>
        <p class="mt-1 text-sm text-zinc-400">
          {{ emulator.file_count }} fichier(s) &middot; {{ formatBytes(emulator.size) }}
        </p>
      </article>
    </div>
  </div>
</template>
