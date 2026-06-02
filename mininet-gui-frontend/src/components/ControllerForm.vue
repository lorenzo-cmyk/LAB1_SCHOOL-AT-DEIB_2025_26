<template>
  <div class="modal-ui controller-form">
    <form
      class="modal-section controller-form__body"
      @submit.prevent="submitForm"
    >
      <div class="modal-section__header">
        <div class="modal-section__title">{{ titleText }}</div>
      </div>
      <div class="modal-form-grid">
        <template v-if="isRemote">
          <label class="modal-field" for="ip">
            {{ $t("controller.ip") }}
            <input
              id="ip"
              class="modal-input"
              type="text"
              v-model="ip"
              :disabled="isEditMode && !isEditing"
              required
            />
          </label>
        </template>

        <label class="modal-field" for="port">
          {{ $t("controller.port") }}
          <input
            id="port"
            class="modal-input"
            type="number"
            v-model="port"
            :placeholder="''"
            :disabled="(isEditMode && !isEditing) || isDefault"
            required
          />
        </label>
      </div>

      <div class="modal-actions">
        <button
          v-if="isEditMode && !isEditing"
          class="modal-button"
          type="button"
          @click="startEdit"
        >
          {{ $t("actions.edit") }}
        </button>
        <div v-else-if="isEditMode" class="controller-form__edit-actions">
          <button class="modal-button modal-button--primary" type="submit">
            {{ $t("actions.save") }}
          </button>
          <button class="modal-button" type="button" @click="cancelEdit">
            {{ $t("actions.cancel") }}
          </button>
        </div>
        <button v-else class="modal-button modal-button--primary" type="submit">
          {{ $t("actions.create") }}
        </button>
      </div>
    </form>
  </div>
</template>

<script>
export default {
  props: {
    presetType: {
      type: String,
      default: null,
    },
    controller: {
      type: Object,
      default: null,
    },
  },
  emits: ["form-submit", "form-update"],
  data() {
    return {
      type: this.presetType || "remote",
      ip: "127.0.0.1",
      port: 6633,
      isEditing: false,
    };
  },
  computed: {
    isRemote() {
      return this.type === "remote";
    },
    isDefault() {
      return this.type === "default";
    },
    isEditMode() {
      return !!this.controller;
    },
    titleText() {
      if (this.isEditMode) return this.$t("controller.title");
      return this.$t("controller.remoteTitle");
    },
  },
  watch: {
    presetType: {
      immediate: true,
      handler(newType) {
        this.type = newType || "remote";
        this.resetForm();
      },
    },
    controller: {
      immediate: true,
      handler(value) {
        if (!value) return;
        this.type = (value.controller_type || "").toLowerCase() || "remote";
        this.ip = value.ip || "127.0.0.1";
        this.port = value.port ?? "";
        this.isEditing = false;
      },
    },
  },
  methods: {
    resetForm() {
      this.ip = "127.0.0.1";
      this.port = 6633;
      this.isEditing = false;
    },
    startEdit() {
      this.isEditing = true;
    },
    cancelEdit() {
      if (this.controller) {
        this.type =
          (this.controller.controller_type || "").toLowerCase() || "remote";
        this.ip = this.controller.ip || "127.0.0.1";
        this.port = this.controller.port ?? "";
      }
      this.isEditing = false;
    },
    submitForm() {
      const formData = {
        type: this.type,
        ip: this.ip,
        port: Number(this.port),
      };
      if (this.isEditMode) {
        this.$emit("form-update", formData);
        this.isEditing = false;
      } else {
        this.$emit("form-submit", formData);
      }
    },
  },
};
</script>

<style scoped>
.controller-form__edit-actions {
  display: flex;
  gap: 8px;
}
</style>
