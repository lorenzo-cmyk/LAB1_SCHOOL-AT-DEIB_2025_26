<template>
  <div ref="topbar" class="topbar theme-dark">
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
          <button
            type="button"
            class="menu-action"
            @click="
              $emit('new-topology');
              closeFileMenu();
            "
          >
            {{ $t("menu.newTopology") }}
          </button>
          <button
            type="button"
            class="menu-action"
            @click="
              closeFileMenu();
              openFileDialog();
            "
          >
            {{ $t("menu.openTopology") }}
          </button>
          <button
            type="button"
            class="menu-action"
            @click="
              $emit('save-topology');
              closeFileMenu();
            "
          >
            {{ $t("menu.saveTopology") }}
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
          <button
            type="button"
            class="menu-action"
            @click="
              $emit('collapse-all-views');
              closeViewMenu();
            "
          >
            {{ $t("menu.collapseViews") }}
          </button>
          <button
            type="button"
            class="menu-action"
            @click="
              $emit('expand-all-views');
              closeViewMenu();
            "
          >
            {{ $t("menu.expandViews") }}
          </button>
          <div class="menu-separator"></div>
          <label class="menu-checkbox">
            <input
              type="checkbox"
              :checked="settings.showHostIp"
              @change="
                $emit('update-setting', 'showHostIp', $event.target.checked)
              "
            />
            {{ $t("menu.showHostIp") }}
          </label>
          <label class="menu-checkbox">
            <input
              type="checkbox"
              :checked="settings.showSwitchDpids"
              @change="
                $emit(
                  'update-setting',
                  'showSwitchDpids',
                  $event.target.checked,
                )
              "
            />
            {{ $t("menu.showSwitchDpids") }}
          </label>
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
  },
  emits: [
    "new-topology",
    "save-topology",
    "collapse-all-views",
    "expand-all-views",
    "update-setting",
    "file-upload",
  ],
  data() {
    return {
      fileMenuOpen: false,
      viewMenuOpen: false,
      boundHandleGlobalClick: null,
    };
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
      if (this.viewMenuOpen && !topbar.contains(event.target)) {
        this.viewMenuOpen = false;
      }
    },
    isAnyMenuOpen() {
      return this.fileMenuOpen || this.viewMenuOpen;
    },
    openMenuByKey(menuKey) {
      this.fileMenuOpen = false;
      this.viewMenuOpen = false;
      if (menuKey === "file") this.fileMenuOpen = true;
      if (menuKey === "view") this.viewMenuOpen = true;
    },
    handleMenuHover(menuKey) {
      if (!this.isAnyMenuOpen()) return;
      if (menuKey === "file" && this.fileMenuOpen) return;
      if (menuKey === "view" && this.viewMenuOpen) return;
      this.openMenuByKey(menuKey);
    },
    toggleFileMenu() {
      this.viewMenuOpen = false;
      this.fileMenuOpen = !this.fileMenuOpen;
    },
    toggleViewMenu() {
      this.fileMenuOpen = false;
      this.viewMenuOpen = !this.viewMenuOpen;
    },
    closeFileMenu() {
      this.fileMenuOpen = false;
    },
    closeViewMenu() {
      this.viewMenuOpen = false;
    },
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
