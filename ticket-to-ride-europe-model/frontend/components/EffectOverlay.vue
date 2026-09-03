<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import TrainCard from './TrainCard.vue'
import type { EuropeEvent } from '../types'

const props = withDefaults(defineProps<{ event: EuropeEvent | null; hold?: boolean }>(), { hold: false })
const visible = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

const presentation = computed(() => {
  const type = props.event?.type ?? ''
  return ({
    train_card_drawn: { title: props.event?.source === 'deck' ? '盲抽车票' : '公共车票入手', symbol: '▰', duration: 900 },
    route_claimed: { title: '铁路贯通', symbol: `+${props.event?.points ?? 0}`, duration: 1500 },
    tunnel_cards_revealed: { title: '隧道勘探', symbol: `+${props.event?.extraCost ?? 0}`, duration: 2300 },
    tunnel_extra_paid: { title: '隧道通车', symbol: '✓', duration: 1400 },
    tunnel_declined: { title: '工程撤回', symbol: '↶', duration: 1200 },
    destination_tickets_drawn: { title: '新任务抵达', symbol: props.event?.count ?? 3, duration: 1350 },
    destination_tickets_kept: { title: '任务已封存', symbol: props.event?.keptCount ?? 1, duration: 1050 },
    station_built: { title: '中央车站落成', symbol: '⌂', duration: 1550 },
    final_round_triggered: { title: '最后一轮', symbol: '!', duration: 2500 },
    final_turns_complete: { title: '终点将至', symbol: '◎', duration: 1500 },
    game_scored: { title: '欧洲快车结算', symbol: '★', duration: 2600 },
  } as Record<string, { title: string; symbol: string | number; duration: number }>)[type] ?? null
})

watch(
  () => props.event?.sequence,
  (next, previous) => {
    if (!next || next === previous || !presentation.value) return
    if (timer) clearTimeout(timer)
    visible.value = false
    const reveal = () => {
      visible.value = true
      timer = setTimeout(
        () => { visible.value = false },
        props.hold ? 15_000 : presentation.value?.duration ?? 1200,
      )
    }
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(reveal)
    else setTimeout(reveal, 0)
  },
)

onBeforeUnmount(() => { if (timer) clearTimeout(timer) })
</script>

<template>
  <Transition name="effect-fade">
    <div
      v-if="visible && event && presentation"
      class="rail-effect"
      :class="`rail-effect--${event.type.replaceAll('_', '-')}`"
      :data-effect="event.type"
      role="status"
      aria-live="polite"
    >
      <div class="effect-vignette" />
      <div class="speed-lines" aria-hidden="true"><i v-for="index in 12" :key="index" /></div>

      <div v-if="event.type === 'train_card_drawn'" class="flying-ticket" aria-hidden="true">
        <span /><span /><span />
      </div>

      <div v-if="event.type === 'route_claimed' || event.type === 'tunnel_extra_paid'" class="rail-sweep" aria-hidden="true">
        <i class="sweep-track" /><i class="sweep-engine" /><i class="sweep-glow" />
      </div>

      <div v-if="event.type === 'station_built'" class="station-drop" aria-hidden="true">
        <i class="roof" /><i class="station-body" /><i class="station-ring" />
      </div>

      <div v-if="event.type === 'destination_tickets_drawn' || event.type === 'destination_tickets_kept'" class="ticket-fan" aria-hidden="true">
        <i /><i /><i />
      </div>

      <div v-if="event.type === 'tunnel_cards_revealed'" class="tunnel-reveal">
        <div class="tunnel-mouth" aria-hidden="true"><i /><i /><i /></div>
        <div class="risk-cards">
          <TrainCard v-for="card in event.revealedCards" :key="card.id" :card="card" compact />
        </div>
      </div>

      <div v-if="event.type === 'final_round_triggered'" class="clock-rings" aria-hidden="true"><i /><i /><i /></div>
      <div v-if="event.type === 'game_scored'" class="score-stars" aria-hidden="true"><i v-for="index in 14" :key="index">★</i></div>

      <div class="effect-copy">
        <small>EUROPE RAIL EVENT</small>
        <strong>{{ presentation.title }}</strong>
        <b>{{ presentation.symbol }}</b>
        <p>{{ event.message }}</p>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.rail-effect{position:absolute;z-index:70;inset:0;display:grid;place-items:center;overflow:hidden;pointer-events:none}.effect-vignette{position:absolute;inset:0;background:radial-gradient(circle at center,#06101722 15%,#061017b8 88%);backdrop-filter:blur(1.5px)}.effect-copy{position:relative;z-index:5;display:grid;justify-items:center;width:min(520px,80%);padding:22px 28px;border:1px solid #e5bd6d66;border-radius:24px;color:#f8f2e6;background:linear-gradient(145deg,#112732ee,#0b1821e8);box-shadow:0 25px 80px #000b,0 0 55px #dcae5033;text-align:center}.effect-copy small{font-size:8px;letter-spacing:.24em;color:#9fc2c8}.effect-copy strong{font-size:clamp(24px,4vw,48px);line-height:1.05;letter-spacing:.08em}.effect-copy b{margin-top:5px;color:#f4c66d;font-size:clamp(38px,7vw,76px);line-height:1;text-shadow:0 0 28px #e4af4b99}.effect-copy p{max-width:470px;margin:8px 0 0;color:#cbd9da;font-size:12px}.speed-lines{position:absolute;inset:0;opacity:.4}.speed-lines i{position:absolute;left:-15%;top:calc(var(--i,1)*7%);width:38%;height:2px;background:linear-gradient(90deg,transparent,#d9c17d,transparent);transform:rotate(-12deg);animation:speed-line 1s ease-out infinite}.speed-lines i:nth-child(1){--i:1}.speed-lines i:nth-child(2){--i:2;animation-delay:.1s}.speed-lines i:nth-child(3){--i:3;animation-delay:.2s}.speed-lines i:nth-child(4){--i:4;animation-delay:.3s}.speed-lines i:nth-child(5){--i:5;animation-delay:.4s}.speed-lines i:nth-child(6){--i:6;animation-delay:.5s}.speed-lines i:nth-child(7){--i:7;animation-delay:.6s}.speed-lines i:nth-child(8){--i:8;animation-delay:.7s}.speed-lines i:nth-child(9){--i:9;animation-delay:.8s}.speed-lines i:nth-child(10){--i:10;animation-delay:.9s}.speed-lines i:nth-child(11){--i:11;animation-delay:1s}.speed-lines i:nth-child(12){--i:12;animation-delay:1.1s}.flying-ticket{position:absolute;z-index:3;left:14%;top:48%;width:92px;aspect-ratio:11/17;border:3px solid #ead6ac;border-radius:13px;background:linear-gradient(135deg,#467b91,#183846);box-shadow:0 0 45px #7dd4ee88;animation:ticket-flight .9s cubic-bezier(.1,.7,.2,1) forwards}.flying-ticket span{position:absolute;left:15%;right:15%;height:3px;background:#d9bd7c}.flying-ticket span:nth-child(1){top:28%;transform:rotate(27deg)}.flying-ticket span:nth-child(2){top:48%;transform:rotate(-27deg)}.flying-ticket span:nth-child(3){top:68%;transform:rotate(27deg)}.rail-sweep{position:absolute;z-index:2;left:4%;right:4%;top:57%;height:84px;transform:rotate(-7deg)}.sweep-track{position:absolute;left:0;right:0;top:47px;height:8px;border-block:2px solid #c9a861;background:repeating-linear-gradient(90deg,#151d21 0 20px,#9b8150 20px 25px)}.sweep-engine{position:absolute;left:-120px;top:8px;width:110px;height:48px;border-radius:11px 18px 5px 5px;background:#18272f;box-shadow:inset 0 0 0 3px #d3a652,0 0 30px #e3b95b99;animation:engine-sweep 1.35s cubic-bezier(.15,.75,.25,1) forwards}.sweep-engine::before{content:"";position:absolute;right:12px;top:-18px;width:34px;height:24px;border-radius:6px 6px 0 0;background:#18272f;border:3px solid #d3a652}.sweep-engine::after{content:"";position:absolute;left:17px;bottom:-9px;width:20px;height:20px;border:4px solid #d6dde0;border-radius:50%;background:#091015;box-shadow:56px 0 0 -4px #091015,56px 0 0 0 #d6dde0}.sweep-glow{position:absolute;left:0;top:0;width:38%;height:80px;background:linear-gradient(90deg,transparent,#f2c86333,transparent);animation:engine-sweep 1.35s ease-out forwards}.station-drop{position:absolute;z-index:3;top:18%;width:110px;height:120px;animation:station-drop 1.4s cubic-bezier(.16,.84,.3,1) forwards}.station-body{position:absolute;left:25px;right:25px;bottom:18px;height:57px;border:4px solid #f0cc80;background:#1c3a43;box-shadow:0 13px 18px #0008}.roof{position:absolute;left:11px;right:11px;top:15px;border-left:44px solid transparent;border-right:44px solid transparent;border-bottom:42px solid #c4554f;filter:drop-shadow(0 4px 2px #0006)}.station-ring{position:absolute;left:1px;right:1px;bottom:0;height:18px;border:4px solid #e7b85c;border-radius:50%;animation:ring-pulse 1.2s infinite}.ticket-fan{position:absolute;z-index:3;top:14%;width:290px;height:180px}.ticket-fan i{position:absolute;left:76px;top:10px;width:136px;aspect-ratio:17/11;border:3px solid #a8844b;border-radius:13px;background:linear-gradient(145deg,#fff3d7,#dac594);box-shadow:0 14px 24px #0007;animation:fan-in 1.1s cubic-bezier(.2,.8,.2,1) both}.ticket-fan i:first-child{transform-origin:bottom center;--rotate:-19deg;--x:-60px}.ticket-fan i:nth-child(2){--rotate:0deg;--x:0}.ticket-fan i:nth-child(3){--rotate:19deg;--x:60px}.tunnel-reveal{position:absolute;z-index:4;inset:10% 10% auto;display:grid;justify-items:center}.tunnel-mouth{width:310px;height:140px;border:16px solid #29343a;border-bottom:0;border-radius:160px 160px 0 0;background:radial-gradient(ellipse at 50% 100%,#152630,#03080c 62%);box-shadow:0 -12px 35px #0009,inset 0 0 45px #000}.tunnel-mouth i{position:absolute;width:11px;height:11px;border-radius:3px;background:#516068;animation:rock-shake .18s infinite alternate}.tunnel-mouth i:nth-child(1){margin:32px 0 0 30px}.tunnel-mouth i:nth-child(2){margin:66px 0 0 245px}.tunnel-mouth i:nth-child(3){margin:18px 0 0 210px}.risk-cards{display:flex;gap:12px;margin-top:-58px}.risk-cards :deep(.train-card){animation:risk-flip .65s cubic-bezier(.2,.75,.3,1) both}.risk-cards :deep(.train-card:nth-child(2)){animation-delay:.18s}.risk-cards :deep(.train-card:nth-child(3)){animation-delay:.36s}.clock-rings{position:absolute;inset:0;display:grid;place-items:center}.clock-rings i{position:absolute;width:180px;height:180px;border:3px solid #e9b957;border-radius:50%;animation:clock-ring 1.8s ease-out infinite}.clock-rings i:nth-child(2){animation-delay:.4s}.clock-rings i:nth-child(3){animation-delay:.8s}.score-stars{position:absolute;inset:0}.score-stars i{position:absolute;left:calc((var(--i,1))*7%);top:-10%;color:#f0c367;font-style:normal;font-size:22px;animation:star-fall 2s ease-in infinite}.score-stars i:nth-child(1){--i:1}.score-stars i:nth-child(2){--i:2;animation-delay:.2s}.score-stars i:nth-child(3){--i:3;animation-delay:.5s}.score-stars i:nth-child(4){--i:4;animation-delay:.1s}.score-stars i:nth-child(5){--i:5;animation-delay:.7s}.score-stars i:nth-child(6){--i:6;animation-delay:.3s}.score-stars i:nth-child(7){--i:7;animation-delay:.9s}.score-stars i:nth-child(8){--i:8;animation-delay:.4s}.score-stars i:nth-child(9){--i:9;animation-delay:.65s}.score-stars i:nth-child(10){--i:10;animation-delay:.15s}.score-stars i:nth-child(11){--i:11;animation-delay:.8s}.score-stars i:nth-child(12){--i:12;animation-delay:.25s}.score-stars i:nth-child(13){--i:13;animation-delay:.55s}.score-stars i:nth-child(14){--i:14;animation-delay:.95s}.rail-effect--tunnel-declined .effect-copy{animation:decline-shake .42s ease-in-out 2}.rail-effect--final-round-triggered .effect-copy{border-color:#d65b51;background:linear-gradient(145deg,#3b1719ee,#130d12ef);box-shadow:0 0 90px #c74d4666}.effect-fade-enter-active,.effect-fade-leave-active{transition:opacity .22s ease}.effect-fade-enter-from,.effect-fade-leave-to{opacity:0}@keyframes speed-line{from{transform:translateX(-20%) rotate(-12deg)}to{transform:translateX(400%) rotate(-12deg)}}@keyframes ticket-flight{0%{transform:translate(-30vw,-20vh) rotate(-35deg) scale(.5)}65%{transform:translate(34vw,12vh) rotate(7deg) scale(1.1)}100%{transform:translate(43vw,30vh) rotate(14deg) scale(.2);opacity:0}}@keyframes engine-sweep{to{left:105%}}@keyframes station-drop{0%{transform:translateY(-220px) scale(.75);opacity:0}65%{transform:translateY(15px) scale(1.04);opacity:1}100%{transform:translateY(0) scale(1)}}@keyframes ring-pulse{50%{transform:scale(1.4);opacity:.25}}@keyframes fan-in{from{transform:translate(var(--x),-160px) rotate(var(--rotate)) scale(.55);opacity:0}to{transform:translate(var(--x),0) rotate(var(--rotate));opacity:1}}@keyframes risk-flip{from{transform:perspective(500px) rotateY(90deg) translateY(-60px);opacity:0}to{transform:perspective(500px) rotateY(0);opacity:1}}@keyframes rock-shake{to{transform:translate(3px,-2px) rotate(9deg)}}@keyframes clock-ring{from{transform:scale(.4);opacity:1}to{transform:scale(3.8);opacity:0}}@keyframes star-fall{to{transform:translateY(110vh) rotate(520deg);opacity:.1}}@keyframes decline-shake{25%{transform:translateX(-13px)}75%{transform:translateX(13px)}}@media(max-width:720px){.effect-copy{padding:18px;width:88%}.effect-copy p{font-size:10px}.tunnel-reveal{top:9%;transform:scale(.8)}}@media(prefers-reduced-motion:reduce){.rail-effect *{animation:none!important;transition:none!important}.speed-lines,.score-stars,.clock-rings{display:none}}
.rail-effect--tunnel-cards-revealed .effect-copy{position:absolute;left:50%;bottom:12px;width:min(520px,72%);padding:9px 20px;transform:translateX(-50%)}
.rail-effect--tunnel-cards-revealed .effect-copy small{display:none}
.rail-effect--tunnel-cards-revealed .effect-copy strong{font-size:clamp(20px,3vw,34px)}
.rail-effect--tunnel-cards-revealed .effect-copy b{font-size:clamp(30px,4vw,48px)}
.rail-effect--tunnel-cards-revealed .effect-copy p{margin-top:3px}
</style>
