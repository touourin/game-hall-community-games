<script setup lang="ts">
import type { PlayerView, ResultView, SuitView } from '../types'
import SuitIcon from './SuitIcon.vue'

const props = defineProps<{
  result: ResultView
  players: PlayerView[]
  suits: SuitView[]
  canRestart: boolean
}>()
const emit = defineEmits<{ restart: [] }>()

function playerName(playerId: string) {
  return props.players.find(player => player.id === playerId)?.displayName ?? playerId
}
</script>

<template>
  <section class="score-overlay" role="dialog" aria-modal="true" aria-labelledby="score-title">
    <small>终局结算 · {{ result.reason === 'player-exit' ? '退赛结束' : '抽牌堆耗尽' }}</small>
    <h2 id="score-title">{{ result.summaryZh }}</h2>
    <div class="score-grid">
      <article v-for="row in result.scores" :key="row.playerId" :class="{ winner: row.winner, ineligible: !row.eligible }">
        <header><span>#{{ row.rank ?? '—' }}</span><strong>{{ playerName(row.playerId) }}</strong><b>{{ row.total }} 分</b></header>
        <div class="suit-scores">
          <span v-for="suit in suits" :key="suit.id" :title="suit.nameZh" :style="{ '--suit-color': suit.color }">
            <SuitIcon :suit="suit.id" :size="19" :label="suit.nameZh"/><b>{{ row.suitSubtotals[suit.id] }}</b>
          </span>
        </div>
        <footer><span>银行 {{ row.bankCardCount }} 张</span><span v-if="row.cardAdjustments">特性 +{{ row.cardAdjustments }}</span><strong v-if="row.winner">胜者</strong><em v-if="!row.eligible">已退出</em></footer>
      </article>
    </div>
    <button v-if="canRestart" class="restart" type="button" @click="emit('restart')">再来一局</button>
  </section>
</template>

<style scoped>
.score-overlay { position: absolute; z-index: 30; inset: clamp(12px, 3vw, 38px); overflow: auto; padding: clamp(18px, 3vw, 34px); border: 1px solid #b28a4a; border-radius: 24px; color: #fff9ea; background: linear-gradient(145deg, #102b2aee, #071c1bdd); box-shadow: 0 30px 90px #020908e8, inset 0 1px #fff2; backdrop-filter: blur(20px); }
.score-overlay > small { color: #f2c96d; font: 800 11px/1.2 system-ui; letter-spacing: .16em; }
.score-overlay h2 { margin: 7px 0 20px; font-size: clamp(23px, 4vw, 40px); }
.score-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.score-grid article { padding: 14px; border: 1px solid #557370; border-radius: 15px; background: #183c3a; }
.score-grid article.winner { border-color: #f2c96d; box-shadow: 0 0 28px #b28a4a44; }
.score-grid article.ineligible { opacity: .55; }
.score-grid header { display: grid; grid-template-columns: auto 1fr auto; align-items: baseline; gap: 8px; }
.score-grid header span { color: #b28a4a; font-weight: 900; }
.score-grid header b { color: #f2c96d; font-size: 22px; }
.suit-scores { display: grid; grid-template-columns: repeat(5, 1fr); gap: 5px; margin: 12px 0; }
.suit-scores span { display: flex; align-items: center; justify-content: center; gap: 3px; padding: 4px; border-radius: 7px; color: var(--suit-color); background: #0b2827; }
.suit-scores b { color: #fff9ea; font-size: 11px; }
.score-grid footer { display: flex; flex-wrap: wrap; gap: 7px 12px; color: #afc0b9; font-size: 11px; }
.score-grid footer strong { color: #f2c96d; }
.score-grid footer em { color: #ffada2; font-style: normal; }
.restart { display: block; min-width: 180px; margin: 22px auto 0; padding: 12px 22px; border: 0; border-radius: 12px; color: #102725; background: #f2c96d; font-weight: 900; cursor: pointer; }
@media (max-width: 560px) {
  .score-overlay { position: fixed; inset: 8px; border-radius: 18px; }
  .score-grid { grid-template-columns: 1fr; }
}
</style>
