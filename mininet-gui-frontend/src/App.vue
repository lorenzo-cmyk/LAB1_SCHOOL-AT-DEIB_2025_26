<script setup>
import NetworkGraph from "./components/NetworkGraph.vue";
</script>

<template>
  <NetworkGraph />
</template>

<style>
html {
  height: 100%;
  width: 100%;
}

:root {
  --oxford-blue: #101d42ff;
}

body {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
  background-color: var(--oxford-blue);
}

#app {
  /* display: flex;
    flex-direction: column; */
  display: block;
  height: 100%;
  margin: 0;
  padding: 0;
}
</style>
