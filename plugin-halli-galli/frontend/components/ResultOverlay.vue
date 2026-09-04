<script setup lang="ts">
import type { HalliGalliResult } from '../types'

defineProps<{ result: HalliGalliResult; canRestart: boolean }>()
const emit = defineEmits<{ restart: [] }>()
</script>

<template>
  <div class="result-scrim" data-zone="result_overlay" role="dialog" aria-modal="true" aria-labelledby="halli-result-title">
    <section class="result-card">
      <header>
        <span>FINAL BELL · 常规规则</span>
        <h2 id="halli-result-title">{{ result.sharedWin ? '并列获胜' : '本局冠军' }}</h2>
        <p>{{ result.reasonZh }}</p>
      </header>
      <div class="ranking" role="table" aria-label="最终持牌数">
        <article v-for="row in result.rows" :key="row.playerId" :class="{ winner: row.won }" role="row">
          <b role="cell">{{ row.rank }}</b>
          <div role="cell"><strong>{{ row.name }}</strong><small>{{ row.status === 'resigned' ? '已离桌' : row.status === 'eliminated' ? '已退出' : '结算在局' }}</small></div>
          <span role="cell">{{ row.drawCount }}<small>暗牌</small></span>
          <span role="cell">{{ row.discardCount }}<small>明牌</small></span>
          <em role="cell">{{ row.totalCount }}<small>总张数</small></em>
        </article>
      </div>
      <footer>
        <p>最高持牌数获胜；相同最高数共同获胜。</p>
        <button type="button" :disabled="!canRestart" data-action="restart" @click="emit('restart')">再来一局</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.result-scrim{position:absolute;z-index:175;inset:0;display:grid;place-items:center;padding:18px;background:rgba(5,18,17,.78);backdrop-filter:blur(5px);animation:result-fade 240ms ease-out both}.result-card{width:min(720px,92vw);max-height:90%;overflow:auto;padding:22px;border:2px solid #d6b56b;border-radius:20px;color:#eef4ef;background:linear-gradient(145deg,#153f39,#0b2926);box-shadow:0 28px 70px rgba(0,0,0,.54),inset 0 0 45px rgba(214,181,107,.08)}.result-card header{text-align:center}.result-card header span{color:#d6b56b;font:900 8px/1 ui-monospace,monospace;letter-spacing:.2em}.result-card h2{margin:6px 0 3px;color:#fff3cd;font:700 clamp(25px,3vw,40px)/1.1 "Songti SC",Georgia,serif}.result-card header p,.result-card footer p{margin:0;color:#adc1bc;font-size:11px}.ranking{display:grid;gap:6px;margin:18px 0}.ranking article{display:grid;grid-template-columns:34px minmax(120px,1fr) 64px 64px 80px;align-items:center;gap:7px;padding:8px 10px;border:1px solid #42645e;border-radius:10px;background:#143631}.ranking article.winner{border-color:#e8c66d;background:linear-gradient(90deg,rgba(195,145,53,.3),#173a35);box-shadow:inset 4px 0 #efcd74}.ranking article>b{display:grid;width:26px;height:26px;place-items:center;border-radius:50%;color:#18312d;background:#d3b46b}.ranking div strong,.ranking div small,.ranking span small,.ranking em small{display:block}.ranking div strong{color:#fff8e6;font-size:13px}.ranking div small,.ranking span small,.ranking em small{color:#8fa7a2;font-size:7px;font-style:normal}.ranking span,.ranking em{color:#e8dbc0;font-size:16px;font-style:normal;text-align:center}.ranking em{color:#ffd977;font-weight:900}.result-card footer{display:flex;align-items:center;justify-content:space-between;gap:12px}.result-card footer button{min-width:130px;min-height:42px;border:1px solid #ffe69a;border-radius:9px;color:#21302a;background:linear-gradient(#f6dc91,#cfa24e);font-weight:900;cursor:pointer}.result-card footer button:disabled{opacity:.45;cursor:not-allowed}@keyframes result-fade{from{opacity:0;transform:scale(.97)}to{opacity:1;transform:scale(1)}}@media(max-width:560px){.result-card{padding:13px}.ranking article{grid-template-columns:28px minmax(75px,1fr) 44px 44px 55px;gap:3px;padding:6px}.ranking div strong{font-size:10px}.ranking span,.ranking em{font-size:12px}.result-card footer{align-items:stretch;flex-direction:column}.result-card footer button{width:100%}}@media(prefers-reduced-motion:reduce){.result-scrim{animation:none}}
</style>
