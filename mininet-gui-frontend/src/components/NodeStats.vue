<script>
import { getNodeStats, listFlows, updateHost, updateController } from "@/core/api";

export default {
  props: ["stats", "networkStarted"],
  emits: ["hostUpdated", "controllerUpdated"],
  data() {
    return {
      localStats: this.stats,
      isEditingHost: false,
      hostEdit: { ip: "" },
      hostEditBusy: false,
      hostEditError: "",
      isEditingController: false,
      controllerEdit: { ip: "", port: "" },
      controllerEditBusy: false,
      controllerEditError: "",
      flowDump: "",
      flowBusy: false,
      flowError: "",
    };
  },
  computed: {
    isController() {
      return this.localStats?.type === "controller";
    },
    isSwitch() {
      return this.localStats?.type === "sw" || this.localStats?.type === "switch";
    },
    isHost() {
      return this.localStats?.type === "host";
    },
    controllerIsRemote() {
      if (!this.isController) return false;
      const s = this.localStats;
      return s.remote || (s.controller_type || "").toLowerCase() === "remote";
    },
    controllerTypeLabel() {
      if (!this.isController) return "";
      return this.controllerIsRemote ? "remote" : "default";
    },
    controllerIp() {
      return this.localStats?.ip || null;
    },
    controllerPort() {
      return this.localStats?.port ?? null;
    },
    controllerOfVersion() {
      return this.localStats?.of_version || "OpenFlow13";
    },
    hostInterfaces() {
      return this.localStats?.interfaces || [];
    },
    hostDefaultRoute() {
      return this.localStats?.default_route || "";
    },
    hostArpTable() {
      return this.localStats?.arp_table || [];
    },
    switchController() {
      return this.localStats?.controller || null;
    },
    switchType() {
      return this.localStats?.switch_type || "ovskernel";
    },
    switchOfVersion() {
      return this.localStats?.of_version || "OpenFlow13";
    },
    hostHasInterfaces() {
      return (this.localStats?.interfaces || []).length > 0;
    },
  },
  watch: {
    stats: {
      immediate: true,
      handler(value) {
        this.localStats = value;
        if (value?.type === "host") {
          this.hostEdit.ip = value?.ip || "";
          this.isEditingHost = false;
          this.hostEditError = "";
        }
        if (value?.type === "controller") {
          this.controllerEdit.ip = value?.ip || "";
          this.controllerEdit.port = value?.port ?? "";
          this.isEditingController = false;
          this.controllerEditError = "";
        }
        if ((value?.type === "sw" || value?.type === "switch") && this.networkStarted) {
          this.refreshFlows();
        }
      },
    },
  },
  methods: {
    startHostEdit() {
      if (!this.isHost) return;
      this.isEditingHost = true;
      this.hostEditError = "";
      this.hostEdit.ip = this.localStats?.ip || "";
    },
    cancelHostEdit() {
      this.isEditingHost = false;
      this.hostEditError = "";
      this.hostEdit.ip = this.localStats?.ip || "";
    },
    async saveHostEdit() {
      if (!this.isHost || !this.localStats?.id) return;
      this.hostEditBusy = true;
      this.hostEditError = "";
      try {
        const response = await updateHost(this.localStats.id, { ip: this.hostEdit.ip });
        if (!response?.host) {
          this.hostEditError = this.$t("node.errors.updateHost");
          return;
        }
        const refreshed = await getNodeStats(this.localStats.id);
        if (refreshed) {
          this.localStats = refreshed;
          this.$emit("hostUpdated", refreshed);
        }
        this.isEditingHost = false;
      } catch {
        this.hostEditError = this.$t("node.errors.updateHost");
      } finally {
        this.hostEditBusy = false;
      }
    },
    startControllerEdit() {
      if (!this.isController || !this.controllerIsRemote) return;
      this.isEditingController = true;
      this.controllerEditError = "";
      this.controllerEdit.ip = this.localStats?.ip || "";
      this.controllerEdit.port = this.localStats?.port ?? "";
    },
    cancelControllerEdit() {
      this.isEditingController = false;
      this.controllerEditError = "";
      this.controllerEdit.ip = this.localStats?.ip || "";
      this.controllerEdit.port = this.localStats?.port ?? "";
    },
    async saveControllerEdit() {
      if (!this.isController || !this.localStats?.id) return;
      this.controllerEditBusy = true;
      this.controllerEditError = "";
      try {
        const payload = {
          controller_type: "remote",
          remote: true,
          ip: this.controllerEdit.ip,
          port: this.controllerEdit.port ? Number(this.controllerEdit.port) : null,
        };
        const updated = await updateController(this.localStats.id, payload);
        if (!updated) {
          this.controllerEditError = this.$t("node.errors.updateController");
          return;
        }
        this.localStats = { ...this.localStats, ...updated };
        this.$emit("controllerUpdated", this.localStats);
        this.isEditingController = false;
      } catch {
        this.controllerEditError = this.$t("node.errors.updateController");
      } finally {
        this.controllerEditBusy = false;
      }
    },
    async refreshFlows() {
      if (!this.localStats?.id || !this.isSwitch || !this.networkStarted) return;
      this.flowBusy = true;
      this.flowError = "";
      try {
        const response = await listFlows(this.localStats.id);
        this.flowDump = response?.flows || "";
        const refreshed = await getNodeStats(this.localStats.id);
        if (refreshed) {
          this.localStats = refreshed;
        }
      } catch {
        this.flowError = this.$t("node.errors.refreshFlows");
      } finally {
        this.flowBusy = false;
      }
    },
  },
};
</script>

<template>
  <div class="modal-ui node-stats">
    <!-- CONTROLLER: single overview view -->
    <template v-if="isController">
      <div class="tab-content modal-tab-panels">
        <div class="modal-section node-header">
          <div class="node-header__top">
            <span class="node-header__name">{{ localStats?.name }}</span>
            <div class="node-header__top-right">
              <span class="node-badge">{{ controllerTypeLabel }}</span>
              <template v-if="controllerIsRemote">
                <button
                  v-if="!isEditingController"
                  class="modal-button"
                  @click="startControllerEdit"
                >
                  {{ $t("actions.edit") }}
                </button>
                <template v-if="isEditingController">
                  <button
                    class="modal-button modal-button--primary"
                    :disabled="controllerEditBusy"
                    @click="saveControllerEdit"
                  >
                    {{ $t("actions.save") }}
                  </button>
                  <button
                    class="modal-button"
                    :disabled="controllerEditBusy"
                    @click="cancelControllerEdit"
                  >
                    {{ $t("actions.cancel") }}
                  </button>
                </template>
              </template>
            </div>
          </div>
          <p v-if="controllerEditError" class="modal-error">{{ controllerEditError }}</p>
          <div class="node-header__fields">
            <div class="node-field">
              <span class="node-field__label">{{ $t("node.controllerOfVersion") }}</span>
              <span class="node-field__value">{{ controllerOfVersion }}</span>
            </div>
            <template v-if="controllerIsRemote">
              <div class="node-field">
                <span class="node-field__label">IP</span>
                <template v-if="isEditingController">
                  <input
                    v-model="controllerEdit.ip"
                    type="text"
                    class="modal-input node-field__input"
                  />
                </template>
                <span v-else class="node-field__value node-field__value--mono">
                  {{ controllerIp || $t("node.controllerNoIp") }}
                </span>
              </div>
              <div class="node-field">
                <span class="node-field__label">{{ $t("controller.port") }}</span>
                <template v-if="isEditingController">
                  <input
                    v-model="controllerEdit.port"
                    type="number"
                    class="modal-input node-field__input node-field__input--narrow"
                  />
                </template>
                <span v-else class="node-field__value node-field__value--mono">
                  {{ controllerPort ?? $t("node.controllerNoPort") }}
                </span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </template>

    <!-- HOST: single overview view -->
    <template v-if="isHost">
      <div class="tab-content modal-tab-panels">
        <div class="modal-section node-header">
          <div class="node-header__top">
            <span class="node-header__name">{{ localStats?.name }}</span>
            <div class="modal-actions">
              <button
                v-if="!isEditingHost && hostHasInterfaces"
                class="modal-button"
                @click="startHostEdit"
              >
                {{ $t("actions.edit") }}
              </button>
              <template v-if="isEditingHost">
                <button
                  class="modal-button modal-button--primary"
                  :disabled="hostEditBusy"
                  @click="saveHostEdit"
                >
                  {{ $t("actions.save") }}
                </button>
                <button
                  class="modal-button"
                  :disabled="hostEditBusy"
                  @click="cancelHostEdit"
                >
                  {{ $t("actions.cancel") }}
                </button>
              </template>
            </div>
          </div>
          <p v-if="hostEditError" class="modal-error">{{ hostEditError }}</p>
          <div class="node-header__fields">
            <div class="node-field">
              <span class="node-field__label">IP</span>
              <template v-if="isEditingHost">
                <input
                  v-model="hostEdit.ip"
                  type="text"
                  class="modal-input node-field__input"
                />
              </template>
              <span v-else class="node-field__value">{{ localStats?.ip }}</span>
            </div>
            <div class="node-field">
              <span class="node-field__label">MAC</span>
              <span class="node-field__value node-field__value--mono">{{ localStats?.mac }}</span>
            </div>
          </div>
        </div>

        <div class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">{{ $t("node.networkInfo") }}</div>
          </div>
          <div class="node-kv-grid">
            <span class="node-kv__key">{{ $t("node.interfaces") }}</span>
            <span class="node-kv__value">
              <span v-if="hostInterfaces.length" class="node-iface-list">
                <code v-for="iface in hostInterfaces" :key="iface" class="node-iface">{{ iface }}</code>
              </span>
              <span v-else class="node-muted">&mdash;</span>
            </span>
            <span class="node-kv__key">{{ $t("node.defaultRoute") }}</span>
            <span class="node-kv__value">
              <code v-if="hostDefaultRoute" class="node-mono">{{ hostDefaultRoute }}</code>
              <span v-else class="node-muted">&mdash;</span>
            </span>
          </div>
        </div>

        <div class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">{{ $t("node.arpTableSection") }}</div>
          </div>
          <div v-if="hostArpTable.length" class="modal-table__wrapper">
            <table class="modal-table modal-table--compact">
              <thead>
                <tr>
                  <th>{{ $t("node.arp.ip") }}</th>
                  <th>{{ $t("node.arp.mac") }}</th>
                  <th>{{ $t("node.arp.interface") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entry in hostArpTable" :key="entry.ip">
                  <td><code class="node-mono">{{ entry.ip }}</code></td>
                  <td><code class="node-mono">{{ entry.mac }}</code></td>
                  <td>{{ entry.interface }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="node-muted">{{ $t("node.arpEmpty") }}</div>
        </div>
      </div>
    </template>

    <!-- SWITCH: single overview view -->
    <template v-if="isSwitch">
      <div class="tab-content modal-tab-panels">
        <div class="modal-section node-header">
          <div class="node-header__top">
            <span class="node-header__name">{{ localStats?.name }}</span>
            <span class="node-badge">{{ switchOfVersion }}</span>
          </div>
          <div class="node-header__fields">
            <div class="node-field">
              <span class="node-field__label">{{ $t("node.switchType") }}</span>
              <span class="node-field__value">{{ switchType }}</span>
            </div>
            <div class="node-field">
              <span class="node-field__label">{{ $t("node.switchPorts") }}</span>
              <span class="node-field__value">{{ localStats?.ports || 0 }}</span>
            </div>
            <div class="node-field">
              <span class="node-field__label">{{ $t("node.switchController") }}</span>
              <span class="node-field__value">
                <code v-if="switchController" class="node-mono">{{ switchController }}</code>
                <span v-else class="node-muted">&mdash;</span>
              </span>
            </div>
          </div>
        </div>

        <div class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">{{ $t("node.flowTableSection") }}</div>
            <div v-if="networkStarted" class="modal-actions">
              <button
                class="modal-button"
                :disabled="flowBusy"
                @click="refreshFlows"
              >
                {{ $t("actions.refresh") }}
              </button>
            </div>
          </div>
          <template v-if="networkStarted">
            <p v-if="flowError" class="modal-error">{{ flowError }}</p>
            <pre v-if="flowDump" class="modal-pre">{{ flowDump }}</pre>
            <div v-else class="node-muted">{{ $t("node.flowsEmpty") }}</div>
          </template>
          <div v-else class="node-muted">{{ $t("node.flowsNetworkStopped") }}</div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.node-stats {
  min-width: 520px;
}

.tab-content {
  width: 80vw;
  max-height: 420px;
  overflow-y: auto;
  text-align: left;
}

.node-header__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.node-header__top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-header__name {
  font-size: 16px;
  font-weight: 700;
  color: #e6f2ff;
}

.node-badge {
  display: inline-block;
  background: #1a3a4a;
  border: 1px solid #007acc44;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #8cc8ff;
}

.node-header__fields {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.node-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-field__label {
  font-size: 11px;
  font-weight: 600;
  color: #9b9b9b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.node-field__value {
  font-size: 13px;
  color: #cccccc;
}

.node-field__value--mono {
  font-family: monospace;
  font-size: 12px;
}

.node-field__input {
  padding: 4px 8px;
  font-size: 13px;
}

.node-field__input--narrow {
  width: 80px;
}

.node-kv-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 16px;
  align-items: baseline;
}

.node-kv__key {
  font-size: 11px;
  font-weight: 600;
  color: #9b9b9b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.node-kv__value {
  font-size: 12px;
  color: #cccccc;
}

.node-iface-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.node-iface {
  background: #1a3a4a;
  border: 1px solid #007acc44;
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 11px;
  color: #8cc8ff;
}

.node-mono {
  font-family: monospace;
  font-size: 12px;
  color: #cccccc;
}

.node-muted {
  color: #666666;
  font-size: 12px;
}
</style>
