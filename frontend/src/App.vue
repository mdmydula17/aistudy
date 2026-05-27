<template>
  <div id="app">
    <header class="app-header">
      <h1 @click="$router.push('/')" class="logo">Info-Arbitrage Dashboard</h1>
      <nav>
        <router-link to="/">任务列表</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f2f5;
  color: #333;
}

.app-header {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: white;
  padding: 16px 32px;
  display: flex;
  align-items: center;
  gap: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.logo {
  cursor: pointer;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

nav a {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.2s;
}

nav a:hover,
nav a.router-link-active {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.app-main {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}
</style>
