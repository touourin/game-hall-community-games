<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(defineProps<{
  enabled: boolean
  pending?: boolean
  finalDuel?: boolean
}>(), { pending: false, finalDuel: false })

const emit = defineEmits<{ ring: [method: 'pointer' | 'touch' | 'keyboard' | 'button'] }>()
const pressed = ref(false)
let lastPointerAt = 0
let releaseTimer: ReturnType<typeof setTimeout> | undefined

function pulse(): void {
  pressed.value = true
  if (releaseTimer) clearTimeout(releaseTimer)
  releaseTimer = setTimeout(() => { pressed.value = false }, 100)
}

function onPointer(event: PointerEvent): void {
  if (!props.enabled || event.button !== 0) return
  event.preventDefault()
  lastPointerAt = Date.now()
  pulse()
  emit('ring', event.pointerType === 'touch' ? 'touch' : 'pointer')
}

function onClick(event: MouseEvent): void {
  if (!props.enabled || Date.now() - lastPointerAt < 400) return
  if (event.detail !== 0) return
  pulse()
  emit('ring', 'button')
}

function onKey(event: KeyboardEvent): void {
  if (!props.enabled || event.repeat) return
  event.preventDefault()
  event.stopPropagation()
  pulse()
  emit('ring', 'keyboard')
}
</script>

<template>
  <button
    type="button"
    class="bell-button"
    :class="{ pressed, pending, 'final-duel': finalDuel }"
    :disabled="!enabled"
    :aria-label="enabled ? '按铃，当前可用' : '按铃，当前不可用'"
    data-zone="bell_zone"
    data-action="ring-bell"
    @pointerdown="onPointer"
    @click="onClick"
    @keydown.space="onKey"
    @keydown.enter="onKey"
  >
    <span class="bell-halo" aria-hidden="true" />
    <svg viewBox="0 0 160 160" aria-hidden="true">
      <defs>
        <linearGradient id="bell-metal" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#fff0a9"/><stop offset=".22" stop-color="#d9b45e"/>
          <stop offset=".55" stop-color="#9a6a28"/><stop offset=".76" stop-color="#f0d27b"/><stop offset="1" stop-color="#7b501d"/>
        </linearGradient>
        <radialGradient id="bell-top" cx="35%" cy="25%">
          <stop offset="0" stop-color="#fff3b7"/><stop offset=".5" stop-color="#d2a64d"/><stop offset="1" stop-color="#76501f"/>
        </radialGradient>
      </defs>
      <ellipse cx="80" cy="132" rx="57" ry="13" fill="#3e2b19" opacity=".5"/>
      <path d="M38 119h84c-4-15-9-20-13-37-5-25-14-40-29-40S56 57 51 82c-4 17-9 22-13 37z" fill="url(#bell-metal)" stroke="#68451d" stroke-width="6"/>
      <path d="M48 112h64" stroke="#fff1ac" stroke-width="5" stroke-linecap="round" opacity=".52"/>
      <path d="M54 91c3-23 10-39 22-43" fill="none" stroke="#fff2ad" stroke-width="7" stroke-linecap="round" opacity=".38"/>
      <rect x="25" y="113" width="110" height="23" rx="10" fill="url(#bell-metal)" stroke="#68451d" stroke-width="6"/>
      <ellipse cx="80" cy="43" rx="21" ry="13" fill="#8d6126"/>
      <rect x="66" y="24" width="28" height="27" rx="10" fill="url(#bell-top)" stroke="#68451d" stroke-width="6"/>
      <ellipse cx="80" cy="25" rx="10" ry="5" fill="#fff0a0" opacity=".6"/>
    </svg>
    <strong>{{ pending ? '已发送' : '抢铃' }}</strong>
    <small>{{ finalDuel ? '最终铃' : 'SPACE' }}</small>
  </button>
</template>

<style scoped>
.bell-button{position:relative;display:grid;width:clamp(96px,10vw,142px);min-width:64px;aspect-ratio:1;place-items:center;padding:0;border:0;border-radius:50%;color:#fff7dc;background:radial-gradient(circle,rgba(255,221,129,.18),rgba(7,31,29,.18) 68%,transparent 70%);cursor:pointer;filter:drop-shadow(0 13px 12px rgba(0,0,0,.38));touch-action:manipulation;-webkit-tap-highlight-color:transparent}.bell-button svg{position:absolute;inset:3%;width:94%;height:94%;transition:transform 80ms ease,filter 120ms ease}.bell-button strong{position:absolute;top:72%;padding:2px 8px;border-radius:999px;color:#fffdf4;background:rgba(16,40,36,.82);font-size:clamp(10px,.9vw,14px);letter-spacing:.12em;box-shadow:0 2px 6px rgba(0,0,0,.28)}.bell-button small{position:absolute;top:88%;color:#e9cf8c;font:800 clamp(7px,.65vw,10px)/1 ui-monospace,monospace;letter-spacing:.12em}.bell-halo{position:absolute;inset:5%;border:2px solid rgba(234,199,111,.22);border-radius:50%;transition:transform 100ms ease,border-color 100ms ease}.bell-button:hover:not(:disabled) svg{filter:brightness(1.08)}.bell-button:focus-visible{outline:3px solid #f7d774;outline-offset:4px}.bell-button.pressed svg{transform:translateY(5px) scale(.97)}.bell-button.pressed .bell-halo,.bell-button.pending .bell-halo{border-color:#fff0a8;transform:scale(1.16)}.bell-button.pending .bell-halo{animation:bell-wait 700ms ease-in-out infinite alternate}.bell-button.final-duel .bell-halo{border-color:#efb35a;box-shadow:0 0 26px rgba(239,179,90,.58)}.bell-button:disabled{cursor:not-allowed;filter:grayscale(.35) brightness(.72);opacity:.72}@keyframes bell-wait{to{transform:scale(1.23);opacity:.38}}@media(max-width:759px){.bell-button{width:88px}.bell-button strong{top:70%;font-size:9px}.bell-button small{font-size:7px}}@media(prefers-reduced-motion:reduce){.bell-button svg,.bell-halo{transition:none!important}.bell-button.pending .bell-halo{animation:none;border-width:4px}}
</style>

<style scoped>
.bell-button { width: clamp(96px, 10vw, 136px); }

@media (max-width: 759px) {
  .bell-button { width: 88px; }
}
</style>
