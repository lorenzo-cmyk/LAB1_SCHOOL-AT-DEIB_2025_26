<script>
import { getNodeStats, listFlows, updateHost } from "@/core/api";

export default {
  props: ["stats"],
  emits: ["hostUpdated", "editController"],
  data() {
    return {
      activeTab: "details",
      tabs: [{ key: "details", labelKey: "node.tabs.details" }],
      localStats: this.stats,
      isEditingHost: false,
      hostEdit: {
        ip: "",
      },
      hostEditBusy: false,
      hostEditError: "",
      flowDump: "",
      flowBusy: false,
      flowError: "",
    };
  },
  computed: {
    isDetailsTab() {
      return this.activeTab === "details";
    },
    isController() {
      return this.localStats?.type === "controller";
    },
    isFlowTableTab() {
      return this.activeTab === "flows";
    },
    isArpTableTab() {
      return this.activeTab === "arp";
    },
    filteredDetails() {
      const { flow_table, arp_table, ...details } = this.localStats || {};
      if (this.isHost) {
        const { default_route, interfaces, ...rest } = details;
        return rest;
      }
      return details;
    },
    isSwitch() {
      return (
        this.localStats?.type === "sw" || this.localStats?.type === "switch"
      );
    },
    isHost() {
      return this.localStats?.type === "host";
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
        if (value?.type === "sw" || value?.type === "switch") {
          this.refreshFlows();
        }
      },
    },
  },
  methods: {
    triggerControllerEdit() {
      if (!this.localStats?.id) return;
      this.$emit("editController", this.localStats.id);
    },
    setTab(tabKey) {
      this.activeTab = tabKey;
    },
    formatMatchFields(matchFields) {
      return Object.entries(matchFields || {})
        .map(([key, value]) => `${key}: ${value}`)
        .join(", ");
    },
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
        const payload = {
          ip: this.hostEdit.ip,
        };
        const response = await updateHost(this.localStats.id, payload);
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
      } catch (error) {
        this.hostEditError = this.$t("node.errors.updateHost");
      } finally {
        this.hostEditBusy = false;
      }
    },
    async refreshFlows() {
      if (!this.localStats?.id || !this.isSwitch) return;
      this.flowBusy = true;
      this.flowError = "";
      try {
        const response = await listFlows(this.localStats.id);
        this.flowDump = response?.flows || "";
        const refreshed = await getNodeStats(this.localStats.id);
        if (refreshed) {
          this.localStats = refreshed;
        }
      } catch (error) {
        this.flowError = this.$t("node.errors.refreshFlows");
      } finally {
        this.flowBusy = false;
      }
    },
  },
  created() {
    if (this.stats?.type === "sw" || this.stats?.type === "switch") {
      this.tabs.push({ key: "flows", labelKey: "node.tabs.flowTable" });
    }
    if (this.stats?.type === "host") {
      this.tabs.push({ key: "arp", labelKey: "node.tabs.arpTable" });
    }
  },
};
</script>

<template>
  <div class="modal-ui node-stats">
    <div class="modal-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="modal-tab"
        :class="{ 'is-active': activeTab === tab.key }"
        @click="setTab(tab.key)"
      >
        {{ tab.labelKey ? $t(tab.labelKey) : tab.label }}
      </button>
    </div>

    <div class="tab-content modal-tab-panels">
      <div class="modal-ui tab-panel" :class="{ 'is-hidden': !isDetailsTab }">
        <div v-if="isController" class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">
              {{ $t("node.controllerSection") }}
            </div>
            <button class="modal-button" @click="triggerControllerEdit">
              {{ $t("node.editController") }}
            </button>
          </div>
        </div>

        <div v-if="isHost" class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">
              {{ $t("node.hostConfigSection") }}
            </div>
            <div class="modal-actions">
              <button
                v-if="!isEditingHost"
                class="modal-button"
                @click="startHostEdit"
              >
                {{ $t("actions.edit") }}
              </button>
              <div v-else class="modal-actions">
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
              </div>
            </div>
          </div>
          <p v-if="hostEditError" class="modal-error">{{ hostEditError }}</p>
          <div v-if="isEditingHost" class="modal-form-grid">
            <label class="modal-field">
              {{ $t("node.hostIp") }}
              <input v-model="hostEdit.ip" type="text" class="modal-input" />
            </label>
          </div>
        </div>

        <div class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">
              {{ $t("node.detailsSection") }}
            </div>
          </div>
          <div class="modal-table__wrapper">
            <table class="modal-table modal-table--compact">
              <tbody>
                <tr v-for="(value, key) in filteredDetails" :key="key">
                  <th scope="row">{{ key }}</th>
                  <td>{{ value }}</td>
                </tr>
                <tr v-if="isHost && !isEditingHost">
                  <th scope="row">{{ $t("node.defaultRoute") }}</th>
                  <td>{{ localStats?.default_route || "" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="modal-ui tab-panel" :class="{ 'is-hidden': !isFlowTableTab }">
        <div class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">
              {{ $t("node.flowTableSection") }}
            </div>
            <div class="modal-actions">
              <button
                class="modal-button"
                :disabled="flowBusy"
                @click="refreshFlows"
              >
                {{ $t("actions.refresh") }}
              </button>
            </div>
          </div>
          <p v-if="flowError" class="modal-error">{{ flowError }}</p>
          <div class="modal-table__wrapper">
            <table class="modal-table">
              <thead>
                <tr>
                  <th>{{ $t("node.flow.headers.flowId") }}</th>
                  <th>{{ $t("node.flow.headers.cookie") }}</th>
                  <th>{{ $t("node.flow.headers.duration") }}</th>
                  <th>{{ $t("node.flow.headers.table") }}</th>
                  <th>{{ $t("node.flow.headers.packets") }}</th>
                  <th>{{ $t("node.flow.headers.bytes") }}</th>
                  <th>{{ $t("node.flow.headers.idleTimeout") }}</th>
                  <th>{{ $t("node.flow.headers.priority") }}</th>
                  <th>{{ $t("node.flow.headers.matchFields") }}</th>
                  <th>{{ $t("node.flow.headers.actions") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(flow, index) in localStats?.flow_table || []"
                  :key="index"
                >
                  <td>{{ index + 1 }}</td>
                  <td>{{ flow.cookie }}</td>
                  <td>{{ flow.duration }}</td>
                  <td>{{ flow.table }}</td>
                  <td>{{ flow.n_packets }}</td>
                  <td>{{ flow.n_bytes }}</td>
                  <td>{{ flow.idle_timeout }}</td>
                  <td>{{ flow.priority }}</td>
                  <td>{{ formatMatchFields(flow.match_fields) }}</td>
                  <td>{{ flow.actions }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="flow-dump">
            <div class="modal-section__title">
              {{ $t("node.flow.rawDump") }}
            </div>
            <pre class="modal-pre">{{ flowDump }}</pre>
          </div>
        </div>
      </div>

      <div class="modal-ui tab-panel" :class="{ 'is-hidden': !isArpTableTab }">
        <div class="modal-section">
          <div class="modal-section__header">
            <div class="modal-section__title">
              {{ $t("node.arpTableSection") }}
            </div>
          </div>
          <div class="modal-table__wrapper">
            <table class="modal-table">
              <thead>
                <tr>
                  <th>{{ $t("node.arp.ip") }}</th>
                  <th>{{ $t("node.arp.mac") }}</th>
                  <th>{{ $t("node.arp.interface") }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="entry in localStats?.arp_table || []"
                  :key="entry.ip"
                >
                  <td>{{ entry.ip }}</td>
                  <td>{{ entry.mac }}</td>
                  <td>{{ entry.interface }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
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

.flow-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
  margin-bottom: 12px;
}

.flow-delete {
  padding: 4px 8px;
}

.flow-dump {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
