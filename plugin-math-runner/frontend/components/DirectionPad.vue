<script setup lang="ts">
import { computed } from 'vue'
import {
  RUNNER_ACTION_META,
  laneLabel,
  type RunnerAction,
  type RunnerActionMeta,
  type RunnerOption,
} from '../types'

const props = withDefaults(defineProps<{
  options?: RunnerOption[]
  selectedAction?: RunnerAction | null
  disabled?: boolean
}>(), {
  options: () => [],
  selectedAction: null,
  disabled: false,
})

const emit = defineEmits<{
  choose: [action: RunnerAction]
}>()

const optionMap = computed(() => new Map(
  props.options.map((option) => [option.action, option]),
))

function optionFor(action: RunnerAction) {
  return optionMap.value.get(action)
}

function buttonLabel(meta: RunnerActionMeta): string {
  const option = optionFor(meta.id)
  return option
    ? `${laneLabel(option.lane)}，按 ${meta.key} ${meta.label}，等式 ${option.equation}`
    : `${meta.label}在当前桥面题段不可用`
}
</script>

<template>
  <nav class="direction-pad" aria-label="跑酷键盘与触控控制">
    <button
      v-for="meta in RUNNER_ACTION_META"
      :key="meta.id"
      type="button"
      class="direction-button"
      :class="[
        `direction-button--${meta.id}`,
        {
          'direction-button--blocked': !optionFor(meta.id),
          'direction-button--selected': selectedAction === meta.id,
        },
      ]"
      :disabled="disabled || !optionFor(meta.id)"
      :aria-label="buttonLabel(meta)"
      :data-control="meta.id"
      @click="emit('choose', meta.id)"
    >
      <span class="direction-symbol" aria-hidden="true">{{ meta.symbol }}</span>
      <span class="direction-copy">
        <b>{{ meta.label }}</b>
        <small>{{ meta.key }}</small>
      </span>
      <span v-if="!optionFor(meta.id)" class="direction-lock" aria-hidden="true">×</span>
    </button>
  </nav>
</template>

<style scoped>
.direction-pad {
  display: grid;
  grid-template-columns: repeat(3, minmax(58px, 78px));
  grid-template-rows: repeat(2, minmax(56px, 68px));
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.direction-button {
  position: relative;
  display: grid;
  grid-template-columns: auto auto;
  place-content: center;
  align-items: center;
  gap: 7px;
  min-width: 0;
  min-height: 56px;
  border: 1px solid color-mix(in srgb, var(--mr-accent) 34%, var(--mr-line));
  border-radius: 16px;
  padding: 8px;
  color: var(--mr-copy-primary);
  background:
    linear-gradient(150deg, color-mix(in srgb, var(--mr-metal-glass) 82%, transparent), var(--mr-surface-inset));
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 12%, transparent);
  font: inherit;
  cursor: pointer;
  touch-action: manipulation;
  transition: transform 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
}

.direction-button:not(:disabled):hover,
.direction-button:not(:disabled):focus-visible {
  outline: none;
  border-color: var(--mr-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--mr-accent) 22%, transparent);
  transform: translateY(-2px);
}

.direction-button:not(:disabled):active { transform: translateY(1px) scale(.97); }
.direction-button--jump { grid-column: 2; grid-row: 1; }
.direction-button--left { grid-column: 1; grid-row: 2; }
.direction-button--slide { grid-column: 2; grid-row: 2; }
.direction-button--right { grid-column: 3; grid-row: 2; }

.direction-symbol {
  color: var(--mr-accent);
  font-size: 25px;
  font-weight: 950;
  line-height: 1;
}

.direction-copy { display: grid; justify-items: start; line-height: 1; }
.direction-copy b { font-size: 11px; }
.direction-copy small { margin-top: 4px; color: var(--mr-copy-secondary); font-size: 8px; font-weight: 900; letter-spacing: .12em; }

.direction-button--selected {
  border-color: var(--mr-accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--mr-accent) 28%, transparent), 0 7px 18px color-mix(in srgb, var(--mr-shadow) 20%, transparent);
}

.direction-button--blocked {
  border-style: dashed;
  opacity: .52;
  filter: grayscale(.7);
  cursor: default;
}

.direction-lock {
  position: absolute;
  top: 6px;
  right: 8px;
  color: var(--mr-warning);
  font-size: 10px;
  font-weight: 950;
}

@media (max-width: 480px) {
  .direction-pad {
    grid-template-columns: repeat(3, minmax(58px, 72px));
    grid-template-rows: repeat(2, 56px);
    gap: 7px;
  }

  .direction-button { min-height: 56px; border-radius: 15px; }
}

@media (orientation: landscape) and (max-height: 620px) {
  .direction-pad {
    grid-template-columns: repeat(3, minmax(44px, 1fr));
    grid-template-rows: repeat(2, minmax(44px, 52px));
    gap: 5px;
    max-width: 210px;
  }

  .direction-button {
    min-height: 44px;
    gap: 3px;
    border-radius: 10px;
    padding: 4px 3px;
  }

  .direction-symbol { font-size: 18px; }
  .direction-copy b { font-size: 9px; }
  .direction-copy small { margin-top: 2px; font-size: 6px; }
  .direction-lock { top: 3px; right: 5px; font-size: 8px; }
}

@media (prefers-reduced-motion: reduce) {
  .direction-button { transition: none; }
}
</style>
