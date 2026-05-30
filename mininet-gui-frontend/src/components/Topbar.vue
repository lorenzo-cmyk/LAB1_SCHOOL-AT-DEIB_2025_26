<template>
  <div ref="topbar" :class="['topbar', themeClass]">
    <div class="topbar-title">{{ $t("app.title") }}</div>
    <div class="menu-bar">
      <div class="menu-item-wrapper" @mouseenter="handleMenuHover('file')">
        <button
          type="button"
          class="menu-item"
          :class="{ open: fileMenuOpen }"
          @click.stop="toggleFileMenu"
        >
          {{ $t("menu.file") }}
        </button>
        <div v-if="fileMenuOpen" class="menu-dropdown" @click.stop>
          <button type="button" class="menu-action" @click="$emit('new-topology'); closeFileMenu()">
            {{ $t("menu.newTopology") }}
          </button>
          <button type="button" class="menu-action" @click="closeFileMenu(); openFileDialog()">
            {{ $t("menu.openTopology") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('save-topology'); closeFileMenu()">
            {{ $t("menu.saveTopology") }}
          </button>
          <div class="menu-separator"></div>
          <button type="button" class="menu-action" @click="$emit('export-script'); closeFileMenu()">
            {{ $t("menu.exportScript") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('export-sniffer'); closeFileMenu()">
            {{ $t("menu.exportSniffer") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('export-png'); closeFileMenu()">
            {{ $t("menu.exportPng") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('export-addressing-plan'); closeFileMenu()">
            {{ $t("menu.exportAddressing") }}
          </button>
          <div class="menu-separator"></div>
          <button type="button" class="menu-action" @click="$emit('open-settings'); closeFileMenu()">
            {{ $t("menu.settings") }}
          </button>
        </div>
      </div>
      <div class="menu-item-wrapper" @mouseenter="handleMenuHover('view')">
        <button
          type="button"
          class="menu-item"
          :class="{ open: viewMenuOpen }"
          @click.stop="toggleViewMenu"
        >
          {{ $t("menu.view") }}
        </button>
        <div v-if="viewMenuOpen" class="menu-dropdown" @click.stop>
          <button type="button" class="menu-action" @click="$emit('collapse-all-views'); closeViewMenu()">
            {{ $t("menu.collapseViews") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('expand-all-views'); closeViewMenu()">
            {{ $t("menu.expandViews") }}
          </button>
          <div class="menu-separator"></div>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showHosts" @change="$emit('update-show-hosts', $event.target.checked)" />
            {{ $t("menu.showHosts") }}
          </label>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showControllers" @change="$emit('update-show-controllers', $event.target.checked)" />
            {{ $t("menu.showControllers") }}
          </label>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showSpecialSwitches" @change="$emit('update-setting', 'showSpecialSwitches', $event.target.checked)" />
            {{ $t("menu.showSpecialSwitches") }}
          </label>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showSpecialControllers" @change="$emit('update-setting', 'showSpecialControllers', $event.target.checked)" />
            {{ $t("menu.showSpecialControllers") }}
          </label>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showHostIp" @change="$emit('update-setting', 'showHostIp', $event.target.checked)" />
            {{ $t("menu.showHostIp") }}
          </label>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showSwitchDpids" @change="$emit('update-setting', 'showSwitchDpids', $event.target.checked)" />
            {{ $t("menu.showSwitchDpids") }}
          </label>
          <label class="menu-checkbox">
            <input type="checkbox" :checked="settings.showPortLabels" @change="$emit('update-setting', 'showPortLabels', $event.target.checked)" />
            {{ $t("menu.showPortLabels") }}
          </label>
          <div class="menu-separator"></div>
          <label class="menu-checkbox">
            <input
              type="checkbox"
              :checked="settings.theme === 'light'"
              @change="$emit('update-setting', 'theme', $event.target.checked ? 'light' : 'dark')"
            />
            {{ $t("menu.lightTheme") }}
          </label>
        </div>
      </div>
      <div class="menu-item-wrapper" @mouseenter="handleMenuHover('run')">
        <button
          type="button"
          class="menu-item"
          :class="{ open: runMenuOpen }"
          @click.stop="toggleRunMenu"
        >
          {{ $t("menu.run") }}
        </button>
        <div v-if="runMenuOpen" class="menu-dropdown" @click.stop>
          <button
            type="button"
            class="menu-action"
            @click="$emit('start-network'); closeRunMenu()"
            :disabled="networkStarted || networkCommandInFlight || !mininetConnected"
          >
            {{ $t("menu.startNetwork") }}
          </button>
          <button
            type="button"
            class="menu-action"
            @click="$emit('stop-network'); closeRunMenu()"
            :disabled="!networkStarted || networkCommandInFlight || !mininetConnected"
          >
            {{ $t("menu.stopNetwork") }}
          </button>
          <button
            type="button"
            class="menu-action"
            @click="$emit('restart-network'); closeRunMenu()"
            :disabled="networkCommandInFlight || !mininetConnected"
          >
            {{ $t("menu.restartNetwork") }}
          </button>
        </div>
      </div>
      <div class="menu-item-wrapper" @mouseenter="handleMenuHover('tools')">
        <button
          type="button"
          class="menu-item"
          :class="{ open: toolsMenuOpen }"
          @click.stop="toggleToolsMenu"
        >
          {{ $t("menu.tools") }}
        </button>
        <div v-if="toolsMenuOpen" class="menu-dropdown" @click.stop>
          <button type="button" class="menu-action" @click="$emit('run-iperf'); closeToolsMenu()">
            {{ $t("menu.runIperf") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('run-pingall'); closeToolsMenu()">
            {{ $t("menu.runPingall") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('generate-topology'); closeToolsMenu()">
            {{ $t("menu.generateTopology") }}
          </button>
          <div class="menu-separator"></div>
          <button type="button" class="menu-action" @click="$emit('start-sniffer'); closeToolsMenu()">
            {{ $t("menu.startSniffer") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('stop-sniffer'); closeToolsMenu()">
            {{ $t("menu.stopSniffer") }}
          </button>
        </div>
      </div>
      <div class="menu-item-wrapper" @mouseenter="handleMenuHover('help')">
        <button
          type="button"
          class="menu-item"
          :class="{ open: helpMenuOpen }"
          @click.stop="toggleHelpMenu"
        >
          {{ $t("menu.help") }}
        </button>
        <div v-if="helpMenuOpen" class="menu-dropdown" @click.stop>
          <button type="button" class="menu-action" @click="$emit('open-usage'); closeHelpMenu()">
            {{ $t("menu.usage") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('open-docs'); closeHelpMenu()">
            {{ $t("menu.openDocs") }}
          </button>
          <button type="button" class="menu-action" @click="$emit('open-about'); closeHelpMenu()">
            {{ $t("menu.about") }}
          </button>
        </div>
      </div>
    </div>
    <input
      ref="topologyFileInput"
      type="file"
      accept=".json"
      class="menu-file-input"
      @change="handleFileUpload"
    />
  </div>
</template>

<script>
export default {
  name: "Topbar",
  props: {
    settings: { type: Object, required: true },
    networkStarted: { type: Boolean, default: false },
    networkCommandInFlight: { type: Boolean, default: false },
    mininetConnected: { type: Boolean, default: true },
  },
  emits: [
    "start-network", "stop-network", "restart-network",
    "new-topology", "open-topology", "save-topology",
    "export-script", "export-sniffer", "export-png", "export-addressing-plan",
    "open-settings",
    "run-iperf", "run-pingall", "generate-topology",
    "start-sniffer", "stop-sniffer",
    "collapse-all-views", "expand-all-views",
    "open-usage", "open-docs", "open-about",
    "update-show-hosts", "update-show-controllers", "update-setting",
    "file-upload",
  ],
  data() {
    return {
      fileMenuOpen: false,
      helpMenuOpen: false,
      runMenuOpen: false,
      toolsMenuOpen: false,
      viewMenuOpen: false,
      boundHandleGlobalClick: null,
    };
  },
  computed: {
    themeClass() {
      return this.settings?.theme === "light" ? "theme-light" : "theme-dark";
    },
  },
  mounted() {
    this.bindTopbarEvents();
  },
  beforeUnmount() {
    this.unbindTopbarEvents();
  },
  methods: {
    bindTopbarEvents() {
      if (!this.boundHandleGlobalClick) {
        this.boundHandleGlobalClick = this.handleGlobalClick.bind(this);
      }
      document.addEventListener("click", this.boundHandleGlobalClick);
    },
    unbindTopbarEvents() {
      if (this.boundHandleGlobalClick) {
        document.removeEventListener("click", this.boundHandleGlobalClick);
      }
    },
    handleGlobalClick(event) {
      const topbar = this.$refs.topbar;
      if (!topbar) return;
      if (this.fileMenuOpen && !topbar.contains(event.target)) {
        this.fileMenuOpen = false;
      }
      if (this.helpMenuOpen && !topbar.contains(event.target)) {
        this.helpMenuOpen = false;
      }
      if (this.runMenuOpen && !topbar.contains(event.target)) {
        this.runMenuOpen = false;
      }
      if (this.toolsMenuOpen && !topbar.contains(event.target)) {
        this.toolsMenuOpen = false;
      }
      if (this.viewMenuOpen && !topbar.contains(event.target)) {
        this.viewMenuOpen = false;
      }
    },
    isAnyMenuOpen() {
      return (
        this.fileMenuOpen ||
        this.helpMenuOpen ||
        this.runMenuOpen ||
        this.toolsMenuOpen ||
        this.viewMenuOpen
      );
    },
    openMenuByKey(menuKey) {
      this.fileMenuOpen = false;
      this.helpMenuOpen = false;
      this.runMenuOpen = false;
      this.toolsMenuOpen = false;
      this.viewMenuOpen = false;
      if (menuKey === "file") this.fileMenuOpen = true;
      if (menuKey === "help") this.helpMenuOpen = true;
      if (menuKey === "run") this.runMenuOpen = true;
      if (menuKey === "tools") this.toolsMenuOpen = true;
      if (menuKey === "view") this.viewMenuOpen = true;
    },
    handleMenuHover(menuKey) {
      if (!this.isAnyMenuOpen()) return;
      if (menuKey === "file" && this.fileMenuOpen) return;
      if (menuKey === "help" && this.helpMenuOpen) return;
      if (menuKey === "run" && this.runMenuOpen) return;
      if (menuKey === "tools" && this.toolsMenuOpen) return;
      if (menuKey === "view" && this.viewMenuOpen) return;
      this.openMenuByKey(menuKey);
    },
    toggleFileMenu() {
      this.helpMenuOpen = false;
      this.runMenuOpen = false;
      this.toolsMenuOpen = false;
      this.viewMenuOpen = false;
      this.fileMenuOpen = !this.fileMenuOpen;
    },
    toggleHelpMenu() {
      this.fileMenuOpen = false;
      this.runMenuOpen = false;
      this.toolsMenuOpen = false;
      this.viewMenuOpen = false;
      this.helpMenuOpen = !this.helpMenuOpen;
    },
    toggleToolsMenu() {
      this.fileMenuOpen = false;
      this.helpMenuOpen = false;
      this.runMenuOpen = false;
      this.viewMenuOpen = false;
      this.toolsMenuOpen = !this.toolsMenuOpen;
    },
    toggleViewMenu() {
      this.fileMenuOpen = false;
      this.helpMenuOpen = false;
      this.runMenuOpen = false;
      this.toolsMenuOpen = false;
      this.viewMenuOpen = !this.viewMenuOpen;
    },
    toggleRunMenu() {
      this.fileMenuOpen = false;
      this.helpMenuOpen = false;
      this.toolsMenuOpen = false;
      this.viewMenuOpen = false;
      this.runMenuOpen = !this.runMenuOpen;
    },
    closeFileMenu() { this.fileMenuOpen = false; },
    closeHelpMenu() { this.helpMenuOpen = false; },
    closeToolsMenu() { this.toolsMenuOpen = false; },
    closeViewMenu() { this.viewMenuOpen = false; },
    closeRunMenu() { this.runMenuOpen = false; },
    openFileDialog() {
      this.$refs.topologyFileInput?.click();
    },
    handleFileUpload(event) {
      const file = event.target.files?.[0];
      if (file) {
        this.$emit("file-upload", file);
      }
      if (event.target) event.target.value = "";
    },
  },
};
</script>

<style scoped>
.topbar {
  height: 32px;
  background: var(--theme-topbar-bg);
  color: var(--theme-topbar-color);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 12px;
  border-bottom: 1px solid var(--theme-topbar-border);
  position: relative;
  z-index: 6;
  font-size: 0.85rem;
}

.topbar-title {
  font-weight: 600;
  letter-spacing: 0.2px;
  margin-right: 8px;
}

.menu-bar {
  display: flex;
  align-items: center;
  gap: 4px;
}

.menu-item-wrapper {
  position: relative;
}

.menu-item {
  background: transparent;
  border: none;
  color: inherit;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.menu-item:hover,
.menu-item.open {
  background: var(--theme-menu-hover);
}

.menu-item:disabled {
  color: #7a7a7a;
  cursor: default;
}

.menu-dropdown {
  position: absolute;
  top: 28px;
  left: 0;
  background: var(--theme-dropdown-bg);
  border: 1px solid var(--theme-dropdown-border);
  border-radius: 6px;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 240px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.35);
}

.menu-action {
  background: transparent;
  border: none;
  color: var(--theme-app-color);
  padding: 6px 10px;
  text-align: left;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
}

.menu-action:hover {
  background: var(--theme-menu-hover);
}

.menu-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--theme-app-color);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.82rem;
  cursor: pointer;
}

.menu-checkbox:hover {
  background: var(--theme-menu-hover);
}

.menu-checkbox input {
  accent-color: #007acc;
}

.menu-separator {
  height: 1px;
  margin: 4px 0;
  background: var(--theme-topbar-border);
}

.menu-file-input {
  display: none;
}
</style>
