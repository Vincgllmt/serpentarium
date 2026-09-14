<script setup lang="ts">
import type { Game } from '../types/game'

defineProps<{ game: Game }>()
</script>

<template>
  <article
    class="group relative aspect-[3/4] overflow-hidden rounded-xl bg-zinc-800 shadow-lg shadow-black/30 transition-transform duration-200 hover:-translate-y-1 hover:shadow-xl hover:shadow-black/50"
  >
    <img
      v-if="game.cover_url"
      :src="game.cover_url"
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
      class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent p-3 pt-8 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
    >
      <h3 class="truncate text-sm font-semibold text-white">{{ game.title }}</h3>
      <p class="text-xs text-white/60">{{ game.platform }}<span v-if="game.year"> · {{ game.year }}</span></p>
    </div>
  </article>
</template>
