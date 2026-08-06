<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import type { CardView } from '../types'

import eventBack from '../../image/card-event-back.svg'
import eventFront from '../../image/card-event-front.svg'
import personalBack from '../../image/card-personal-back.svg'
import personalFront from '../../image/card-personal-front.svg'

const props = withDefaults(defineProps<{
  card?: CardView | null
  kind?: 'personal' | 'event'
  back?: boolean
  compact?: boolean
  focusable?: boolean
}>(), {
  card: null,
  kind: 'personal',
  back: false,
  compact: false,
  focusable: true,
})

const root = ref<HTMLElement | null>(null)
const detail = ref<HTMLElement | null>(null)
const detailVisible = ref(false)
const detailStyle = ref<Record<string, string>>({})

const art = computed(() => {
  if (props.kind === 'event') return props.back ? eventBack : eventFront
  return props.back ? personalBack : personalFront
})

const tooltipId = computed(() => (
  props.card ? `card-detail-${props.card.instanceId.replace(/[^a-zA-Z0-9_-]/g, '-')}` : undefined
))

function positionDetail() {
  const anchor = root.value
  const popover = detail.value
  if (!anchor || !popover) return

  const anchorBox = anchor.getBoundingClientRect()
  const viewportGap = 12
  const width = Math.min(380, window.innerWidth - viewportGap * 2)
  const height = popover.offsetHeight
  let left = anchorBox.left + anchorBox.width / 2 - width / 2
  left = Math.max(viewportGap, Math.min(left, window.innerWidth - width - viewportGap))

  let top = anchorBox.top - height - viewportGap
  if (top < viewportGap) top = anchorBox.bottom + viewportGap
  if (top + height > window.innerHeight - viewportGap) {
    top = Math.max(viewportGap, window.innerHeight - height - viewportGap)
  }

  detailStyle.value = {
    left: `${Math.round(left)}px`,
    top: `${Math.round(top)}px`,
    width: `${Math.round(width)}px`,
  }
}

async function showDetail() {
  if (props.back || !props.card) return
  detailVisible.value = true
  await nextTick()
  positionDetail()
  window.addEventListener('resize', positionDetail)
  window.addEventListener('scroll', positionDetail, true)
}

function hideDetail() {
  detailVisible.value = false
  window.removeEventListener('resize', positionDetail)
  window.removeEventListener('scroll', positionDetail, true)
}

onBeforeUnmount(hideDetail)
</script>

<template>
  <div
    ref="root"
    class="card-face"
    :class="[{ back, compact }, kind]"
    :tabindex="!back && card && focusable ? 0 : undefined"
    :aria-describedby="!back && card ? tooltipId : undefined"
    @mouseenter="showDetail"
    @mouseleave="hideDetail"
    @focusin="showDetail"
    @focusout="hideDetail"
  >
    <div class="card-art">
      <img :src="art" alt="" draggable="false">
      <div v-if="!back && card" class="card-title">
        <strong>{{ card.name }}</strong>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="card-detail">
        <aside
          v-if="detailVisible && card"
          :id="tooltipId"
          ref="detail"
          class="card-detail-popover"
          :class="kind"
          :style="detailStyle"
          role="tooltip"
        >
          <header>
            <small>{{ card.strength }} · {{ card.subtype }}</small>
            <strong>{{ card.name }}</strong>
          </header>
          <dl>
            <div><dt>类别</dt><dd>{{ card.category }}</dd></div>
            <div><dt>目标</dt><dd>{{ card.targetLabel }}</dd></div>
            <div><dt>时机</dt><dd>{{ card.timing }}</dd></div>
          </dl>
          <p>{{ card.text }}</p>
          <footer>{{ card.durationText }}</footer>
        </aside>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.card-face { position: relative; z-index: 1; width: 100%; aspect-ratio: 5 / 7; min-width: 0; border-radius: 10px; container-type: inline-size; outline: 0; }
.card-face:hover,.card-face:focus-visible { z-index: 15; }
.card-face:focus-visible .card-art { outline: 2px solid var(--gold); outline-offset: 3px; }
.card-art { position: absolute; inset: 0; overflow: hidden; border-radius: inherit; isolation: isolate; box-shadow: 0 8px 22px color-mix(in srgb, var(--bg) 38%, transparent); }
.card-art > img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; user-select: none; }
.card-title { position: absolute; inset: 48% 8% 12%; display: grid; place-items: center; padding: 7%; color: #12394a; text-align: center; }
.event .card-title { color: #522b2b; }
.card-title strong { display: -webkit-box; max-width: 100%; overflow: hidden; font-family: "Songti SC", "STSong", serif; font-size: clamp(12px, 10.5cqw, 27px); font-weight: 900; letter-spacing: .02em; line-height: 1.15; overflow-wrap: anywhere; text-wrap: balance; -webkit-box-orient: vertical; -webkit-line-clamp: 4; }
.back { transform-style: preserve-3d; }

.card-detail-popover { --card-accent: #49c6c1; --card-deep: #083f51; position: fixed; z-index: 1000; display: grid; gap: 11px; max-height: min(430px, calc(100dvh - 24px)); overflow-y: auto; border: 1px solid color-mix(in srgb, var(--card-accent) 58%, white 10%); border-radius: 18px; padding: 17px; color: #eaf7f4; background: radial-gradient(circle at 92% 0, color-mix(in srgb, var(--card-accent) 22%, transparent), transparent 38%), color-mix(in srgb, var(--card-deep) 94%, #061410); box-shadow: 0 24px 70px rgb(0 0 0 / 48%); pointer-events: none; }
.card-detail-popover.event { --card-accent: #f0a052; --card-deep: #4b2630; }
.card-detail-popover header { display: grid; gap: 4px; border-bottom: 1px solid color-mix(in srgb, var(--card-accent) 34%, transparent); padding-bottom: 10px; }
.card-detail-popover header small { color: var(--card-accent); font-size: 11px; font-weight: 900; letter-spacing: .07em; }
.card-detail-popover header strong { font-family: "Songti SC", "STSong", serif; font-size: clamp(22px, 3vw, 30px); line-height: 1.15; text-wrap: balance; }
.card-detail-popover dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 7px; margin: 0; }
.card-detail-popover dl div { min-width: 0; display: grid; gap: 3px; border-radius: 10px; padding: 8px; background: rgb(255 255 255 / 6%); }
.card-detail-popover dt { color: color-mix(in srgb, var(--card-accent) 82%, white); font-size: 9px; font-weight: 900; }
.card-detail-popover dd { overflow: hidden; margin: 0; color: #fff; font-size: 11px; font-weight: 750; text-overflow: ellipsis; white-space: nowrap; }
.card-detail-popover p { margin: 0; color: #f6f4eb; font-size: 14px; font-weight: 750; line-height: 1.65; }
.card-detail-popover footer { border-top: 1px solid rgb(255 255 255 / 11%); padding-top: 9px; color: color-mix(in srgb, var(--card-accent) 66%, white); font-size: 11px; line-height: 1.5; }
.card-detail-enter-active,.card-detail-leave-active { transition: opacity .14s ease, transform .14s ease; }
.card-detail-enter-from,.card-detail-leave-to { opacity: 0; transform: translateY(6px) scale(.98); }

@media (max-width: 520px) {
  .card-title strong { font-size: clamp(11px, 11cqw, 20px); }
  .card-detail-popover { padding: 14px; }
  .card-detail-popover dl { grid-template-columns: 1fr; }
  .card-detail-popover p { font-size: 13px; }
}
@media (prefers-reduced-motion: reduce) {
  .card-detail-enter-active,.card-detail-leave-active { transition: none; }
}
</style>
