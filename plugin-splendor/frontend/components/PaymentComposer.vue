<script setup lang="ts">
import { computed } from 'vue'
import type { DevelopmentCardView, PieceVector, PlayerView, StandardColor } from '../types'
import { colorInfo, standardColors } from '../types'
import DevelopmentCard from './DevelopmentCard.vue'

const props = defineProps<{ card: DevelopmentCardView, player: PlayerView, payment: PieceVector, busy: boolean }>()
const emit = defineEmits<{ change: [PieceVector], confirm: [], cancel: [] }>()

const effective = computed(() => props.card.payment!.effectiveCost)
const total = computed(() => Object.values(props.payment).reduce((sum, value) => sum + value, 0))

function substituteWithGold(color: StandardColor) {
  if (props.payment[color] <= 0 || props.payment.gold >= props.player.pieces.gold) return
  emit('change', { ...props.payment, [color]: props.payment[color] - 1, gold: props.payment.gold + 1 })
}

function restoreColor(color: StandardColor) {
  const maximum = Math.min(props.player.pieces[color], effective.value[color])
  if (props.payment.gold <= 0 || props.payment[color] >= maximum) return
  emit('change', { ...props.payment, [color]: props.payment[color] + 1, gold: props.payment.gold - 1 })
}
</script>

<template>
<section id="payment_sheet" class="payment-composer" role="dialog" aria-modal="true" aria-labelledby="payment-title">
  <header><div><small>精确支付</small><h3 id="payment-title">购买这张发展卡</h3></div><button type="button" aria-label="关闭支付面板" :disabled="busy" @click="emit('cancel')">×</button></header>
  <div class="payment-layout">
    <DevelopmentCard :card="card" />
    <div class="payment-ledger">
      <div class="payment-head"><span>颜色</span><span>原价</span><span>奖励</span><span>实需</span><span>宝石</span><span>黄金替代</span></div>
      <div v-for="color in standardColors" :key="color" class="payment-row">
        <b><i :style="{ '--row-gem': colorInfo[color].hex }">{{ colorInfo[color].symbol }}</i>{{ colorInfo[color].name }}</b>
        <span>{{ card.cost[color] }}</span><span>{{ player.bonuses[color] }}</span><span>{{ effective[color] }}</span><span>{{ payment[color] }}</span>
        <span class="substitution"><button type="button" :disabled="busy || payment[color] <= 0 || payment.gold >= player.pieces.gold" @click="substituteWithGold(color)">−</button><em>{{ effective[color] - payment[color] }}</em><button type="button" :disabled="busy || payment.gold <= 0 || payment[color] >= Math.min(player.pieces[color], effective[color])" @click="restoreColor(color)">+</button></span>
      </div>
      <div class="payment-total"><span>黄金支付 <b>{{ payment.gold }}</b> / 持有 {{ player.pieces.gold }}</span><strong>共支付 {{ total }} 枚棋子</strong></div>
    </div>
  </div>
  <footer><button type="button" class="ghost-action" :disabled="busy" @click="emit('cancel')">返回牌桌</button><button type="button" class="primary-action" :disabled="busy" @click="emit('confirm')">{{ busy ? '提交中…' : payment.gold ? `确认（含 ${payment.gold} 黄金）` : '确认购买' }}</button></footer>
</section>
</template>
