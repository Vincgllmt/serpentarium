<script setup lang="ts"></script>

<template>
  <div class="min-h-screen bg-zinc-950 text-zinc-100">
    <header class="border-b border-white/5 bg-zinc-950/80 px-6 py-5 backdrop-blur">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <h1 class="text-xl font-bold tracking-tight">🐍 Serpentarium</h1>
        <nav class="flex gap-2 text-sm">
          <RouterLink
            to="/"
            class="rounded-lg px-3 py-1.5 transition-colors"
            :class="$route.path === '/' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
          >
            Bibliotheque
          </RouterLink>
          <RouterLink
            to="/emulators"
            class="rounded-lg px-3 py-1.5 transition-colors"
            :class="$route.path === '/emulators' ? 'bg-white/10 text-white' : 'text-zinc-400 hover:text-white'"
          >
            Emulateurs
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-8">
      <RouterView />
    </main>
  </div>
</template>
