<script setup lang="ts">
import type { CardView } from '../types'
import SuitIcon from './SuitIcon.vue'

withDefaults(defineProps<{
  card: CardView
  compact?: boolean
  protected?: boolean
  selected?: boolean
}>(), {
  compact: false,
  protected: false,
  selected: false,
})
</script>

<template>
  <article
    class="loot-card"
    :class="{ compact, protected, selected }"
    :style="{ '--suit-color': card.color }"
    :aria-label="`${card.nameZh} ${card.value}${protected ? '，受保护' : ''}`"
    :data-suit="card.suit"
  >
    <header><strong>{{ card.value }}</strong><span>{{ card.symbol }}</span></header>
    <div class="card-icon"><SuitIcon :suit="card.suit" :size="compact ? 30 : 48" :label="card.nameZh" /></div>
    <b>{{ card.nameZh }}</b>
    <small v-if="!compact">{{ card.summaryZh }}</small>
    <i v-if="protected" title="受保护">保</i>
  </article>
</template>

<style scoped>
.loot-card {
  --suit-color: #53744e;
  position: relative;
  width: clamp(82px, 7.2vw, 112px);
  aspect-ratio: 5 / 7;
  flex: 0 0 auto;
  display: grid;
  grid-template-rows: auto 1fr auto minmax(24px, auto);
  gap: 3px;
  overflow: hidden;
  padding: 6px;
  border: 2px solid #cfb887;
  border-radius: 12px;
  color: #1e2928;
  background: linear-gradient(150deg, #fff7e5, #efe2c4 72%);
  box-shadow: 0 9px 18px #071a1980, inset 0 0 0 1px #fff9ea80;
}
.loot-card header { display: flex; align-items: center; justify-content: space-between; min-height: 26px; padding: 2px 7px; border-radius: 7px; color: #fff9ea; background: var(--suit-color); }
.loot-card header strong { font-size: clamp(17px, 2vw, 23px); line-height: 1; }
.loot-card header span { font-size: 13px; font-weight: 850; }
.card-icon { display: grid; place-items: center; color: var(--suit-color); }
.loot-card b { text-align: center; font-size: 13px; }
.loot-card small { display: -webkit-box; overflow: hidden; color: #5e6965; font-size: 9px; line-height: 1.25; text-align: center; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.loot-card i { position: absolute; top: 4px; right: 4px; display: grid; width: 19px; height: 19px; place-items: center; border: 1px solid #d8c179; border-radius: 50%; color: #fff9ea; background: #4f7f78; font: 800 10px/1 system-ui; }
.loot-card.protected { border-color: #f2c96d; box-shadow: 0 0 0 2px #4f7f78, 0 9px 18px #071a1980, 0 0 22px #4f7f7870; }
.loot-card.selected { transform: translateY(-4px); outline: 3px solid #f2c96d; outline-offset: 2px; }
.loot-card.compact { width: 58px; min-width: 58px; padding: 4px; border-width: 1px; border-radius: 8px; box-shadow: 0 5px 10px #071a1970; }
.loot-card.compact header { min-height: 19px; padding: 1px 4px; border-radius: 5px; }
.loot-card.compact header strong { font-size: 15px; }
.loot-card.compact header span { font-size: 10px; }
.loot-card.compact b { font-size: 10px; }
</style>
