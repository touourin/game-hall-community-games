<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ArcadeSnapshot } from '@game-hall/plugin-sdk'
import GameView from '../frontend/GameView.vue'
import type {
  DestinationTicketModel, EuropeEvent, EuropeGameView, EuropePlayerView, TrainCardModel,
} from '../frontend/types'
import { setDevPluginActions } from './local-sdk'

type Scene = 'playing' | 'setup' | 'ticket' | 'tunnel' | 'assignment' | 'finished'

const playerCount = ref(Math.min(5, Math.max(3, Number(new URLSearchParams(location.search).get('players')) || 5)))
const scene = ref<Scene>('playing')
const watching = ref(false)
const toolbarOpen = ref(true)
const sequence = ref(30)
const latestEvent = ref<EuropeEvent | null>(null)
const lastAction = ref('尚未操作')

const names = ['晨星', '余烬', '青岚', '琥珀', '星河']
const colors: EuropePlayerView['color'][] = ['ruby', 'sapphire', 'jade', 'amber', 'violet']
const accents: Record<string, string> = {
  purple:'#8562a9',blue:'#3985c3',orange:'#dc812e',white:'#ece9de',green:'#549263',yellow:'#d8b22d',black:'#454b52',red:'#c4544d',locomotive:'#9e799e',
}
const patterns: Record<string, string> = { purple:'diamonds',blue:'waves',orange:'diagonal',white:'grid',green:'triangles',yellow:'horizontal',black:'cross',red:'circles',locomotive:'spectrum' }

function card(id: string, color: TrainCardModel['color']): TrainCardModel {
  const labels: Record<string, string> = { purple:'紫晶车厢',blue:'蓝海车厢',orange:'橙霞车厢',white:'象牙车厢',green:'翠林车厢',yellow:'金穗车厢',black:'黑曜车厢',red:'绯红车厢',locomotive:'彩虹机车' }
  return { id, typeId:`train-${color}`, color, label:labels[color], visual:{ accent:accents[color], pattern:patterns[color], accessibilityCode: color === 'locomotive' ? 'W' : color[0].toUpperCase() } }
}

const market = ['yellow','locomotive','green','red','black'].map((color, index) => card(`market-${color}-${index}`, color as TrainCardModel['color']))
const regularHand = ['white','white','blue','blue','locomotive','red','yellow','green','black'].map((color, index) => card(`hand-${color}-${index}`, color as TrainCardModel['color']))
const tickets: DestinationTicketModel[] = [
  { id:'ticket-london-wien',category:'regular',fromCityId:'london',toCityId:'wien',fromLabel:'伦敦',toLabel:'维也纳',points:10,completed:true },
  { id:'ticket-paris-moskva',category:'regular',fromCityId:'paris',toCityId:'moskva',fromLabel:'巴黎',toLabel:'莫斯科',points:17,completed:false },
  { id:'ticket-lisboa-petrograd',category:'long',fromCityId:'lisboa',toCityId:'petrograd',fromLabel:'里斯本',toLabel:'彼得格勒',points:21,completed:false },
  { id:'ticket-roma-berlin',category:'regular',fromCityId:'roma',toCityId:'berlin',fromLabel:'罗马',toLabel:'柏林',points:9,completed:false },
]

function players(): EuropePlayerView[] {
  return names.slice(0, playerCount.value).map((name, index) => ({
    id:`p${index + 1}`,name,seat:index,color:colors[index],status:'active',score:[32,28,25,19,16][index],
    trainsRemaining:[23,26,29,31,34][index],stationsRemaining:index === 0 ? 2 : 3,
    trainHandCount:index === 0 ? regularHand.length : 4 + index,destinationTicketCount:index === 0 ? 2 : 2 + index % 2,
    initialTicketChoiceSubmitted:true,finalStationAssignmentSubmitted:false,
  }))
}

function result(gamePlayers: EuropePlayerView[]) {
  return {
    reason:'score' as const,winnerPlayerIds:['p1'],ranking:gamePlayers.map(item=>item.id),europeanExpressPlayerIds:['p1'],longestPathLength:27,
    players:gamePlayers.map((item,index)=>({
      playerId:item.id,status:'active',routePoints:42-index*4,destinationPoints:18-index*2,stationPoints:index===0?8:12,
      longestPathPoints:index===0?10:0,total:78-index*8,completedTicketCount:3-index%2,completedTicketIds:['ticket-london-wien'],failedTicketIds:index?['ticket-paris-moskva']:[],stationsUsed:index===0?1:0,longestPathLength:27-index*3,europeanExpress:index===0,rank:index+1,
    })),
  }
}

function makeGame(): EuropeGameView {
  const roster = players()
  const setup = scene.value === 'setup'
  const choice = scene.value === 'ticket'
  const tunnel = scene.value === 'tunnel'
  const assignment = scene.value === 'assignment'
  const done = scene.value === 'finished'
  const phase = setup ? 'setup_ticket_selection' : choice ? 'ticket_choice' : tunnel ? 'tunnel_payment' : assignment ? 'final_station_assignment' : done ? 'finished' : 'turn_idle'
  const ownTunnelPayment = tunnel ? { routeId:'route-paris-zurich',declaredColor:'blue' as const,initialCards:[card('paid-blue-1','blue'),card('paid-blue-2','blue'),card('paid-blue-3','blue')],extraCost:2,paymentMode:'declared-color' as const } : null
  const pendingTunnel = tunnel ? { actorPlayerId:'p1',routeId:'route-paris-zurich',declaredColor:'blue' as const,revealedCards:[card('risk-blue','blue'),card('risk-red','red'),card('risk-loco','locomotive')],extraCost:2,status:'awaiting_payment' } : null
  const ownHand = tunnel ? [card('extra-blue','blue'),card('extra-loco','locomotive'),card('wrong-red','red'),...regularHand.slice(5)] : regularHand
  return {
    schemaVersion:1,gameKey:'ticket-to-ride-europe-base',sceneId:`qa.${scene.value}`,phase,
    rules:{playerCount:playerCount.value,startingTrains:45,startingStations:3,europeanExpressPoints:10,unusedStationPoints:4,doubleRoutesRestricted:playerCount.value<=3},
    turnOrder:roster.map(item=>item.id),currentPlayerId:done?null:'p1',turnNumber:18,players:roster,market,
    trainDeckCount:58,trainDiscardCount:21,destinationDeckCount:29,
    claimedRoutes:[
      {routeId:'route-amsterdam-frankfurt',ownerPlayerId:'p1'},{routeId:'route-frankfurt-paris-a',ownerPlayerId:'p1'},{routeId:'route-paris-zurich',ownerPlayerId:'p2'},{routeId:'route-bruxelles-paris-a',ownerPlayerId:'p2'},
      {routeId:'route-berlin-wien',ownerPlayerId:'p3'},{routeId:'route-wien-zagrab',ownerPlayerId:'p3'},{routeId:'route-madrid-pamplona-a',ownerPlayerId:'p4'},{routeId:'route-kharkiv-rostov',ownerPlayerId:roster[4]?.id ?? 'p2'},
    ],
    stationPlacements:[{cityId:'paris',ownerPlayerId:'p1',borrowedRouteId:null}],hand:watching.value?[]:ownHand,
    destinationTickets:watching.value?[]:tickets.slice(0,2),
    initialTicketOptions:setup?tickets:[],
    pendingTicketChoice:choice?{kind:'turn_draw',minKeep:1,offeredTickets:tickets.slice(0,3)}:null,
    pendingTunnel,ownTunnelPayment,
    legalClaimRouteIds:['route-amsterdam-essen','route-bruxelles-frankfurt','route-essen-frankfurt','route-frankfurt-munchen','route-paris-zurich'],
    stationEligibleCityIds:['amsterdam','berlin','london','madrid','wien'],
    finalRound:null,
    actions:setup?['keep_initial_tickets']:choice?['keep_destination_tickets']:tunnel?['pay_tunnel_extra','decline_tunnel']:assignment?['assign_station_routes']:done?[]:['draw_train_card','claim_route','draw_destination_tickets','build_station'],
    latestEvent:latestEvent.value,
    history:[
      {sequence:1,type:'setup_complete',playerId:'p1',message:'晨星从伦敦站发出第一班列车'},
      {sequence:9,type:'route_claimed',playerId:'p2',routeId:'route-paris-zurich',message:'余烬贯通巴黎至苏黎世'},
      {sequence:18,type:'station_built',playerId:'p1',cityId:'paris',message:'晨星在巴黎建造中央车站'},
      ...(latestEvent.value?[latestEvent.value]:[]),
    ],
    result:done?result(roster):null,
  }
}

const snapshot = computed<ArcadeSnapshot>(() => {
  const game = makeGame()
  const roster = players()
  return {
    revision:sequence.value,roomCode:'EUROPE',gameKey:'plugin-ticket-to-ride-europe',gameName:'欧洲车票之旅',phase:scene.value==='finished'?'finished':'playing',options:{qaHoldAnimations:true},hostId:'p1',self:roster[0],viewer:{mode:watching.value?'spectator':'player'},players:roster,requiredPlayers:2,roundNumber:18,winner:null,winnerPlayerIds:game.result?.winnerPlayerIds??[],winReason:null,
    actions:{canStart:false,canRestart:scene.value==='finished',canAct:true,canKickPlayers:false,canDissolve:true,canEditRules:false,canRequestUndo:false,canRequestDraw:false,canResolveRequest:false},rematchReadyPlayerIds:[],request:null,chat:{maxLength:200,messages:[]},game,
  } as unknown as ArcadeSnapshot
})

const effectNames: Record<string,string> = {
  train_card_drawn:'抽车票',route_claimed:'铺轨',tunnel_cards_revealed:'隧道翻牌',tunnel_extra_paid:'隧道通车',tunnel_declined:'撤回隧道',destination_tickets_drawn:'抽任务',station_built:'建站',final_round_triggered:'最后一轮',game_scored:'结算',
}
function triggerEffect(type:string):void {
  scene.value='playing';sequence.value+=1
  latestEvent.value={sequence:sequence.value,type,playerId:'p1',message:`${names[0]}触发「${effectNames[type]}」视觉效果`,source:'deck',routeId:'route-essen-frankfurt',cityId:'wien',points:4,extraCost:2,count:3,keptCount:1,triggerPlayerId:'p1',remainingPlayerIds:players().map(item=>item.id),revealedCards:[card(`risk-blue-${sequence.value}`,'blue'),card(`risk-red-${sequence.value}`,'red'),card(`risk-loco-${sequence.value}`,'locomotive')]}
}
function setScene(value:Scene):void { scene.value=value;latestEvent.value=null;sequence.value+=1 }

setDevPluginActions({
  action:async(name,payload)=>{lastAction.value=`${name} ${payload?JSON.stringify(payload):''}`;if(name==='draw_train_card')triggerEffect('train_card_drawn');return true},
  rapidAction:async()=>true,restart:async()=>true,publishSpectatorFrame:()=>true,
})
</script>

<template>
  <GameView :snapshot="snapshot" />
  <aside class="qa-toolbar" :class="{ closed:!toolbarOpen }" data-testid="qa-toolbar">
    <button class="qa-toggle" type="button" data-testid="qa-toggle" @click="toolbarOpen=!toolbarOpen">{{ toolbarOpen?'收起 QA':'展开 QA' }}</button>
    <template v-if="toolbarOpen">
      <strong>本地视觉验收台</strong>
      <label>玩家数<select v-model.number="playerCount" data-testid="player-count"><option :value="3">3 人</option><option :value="4">4 人</option><option :value="5">5 人</option></select></label>
      <label>场景<select :value="scene" data-testid="scene-select" @change="setScene(($event.target as HTMLSelectElement).value as Scene)"><option value="playing">常规回合</option><option value="setup">初始任务</option><option value="ticket">抽任务</option><option value="tunnel">隧道补付</option><option value="assignment">终局借线</option><option value="finished">终局结算</option></select></label>
      <label class="check"><input v-model="watching" type="checkbox" data-testid="spectator-toggle">观战视图</label>
      <div class="effects"><button v-for="(label,type) in effectNames" :key="type" type="button" :data-testid="`effect-${type}`" @click="triggerEffect(type)">{{ label }}</button></div>
      <small data-testid="last-action">{{ lastAction }}</small>
    </template>
  </aside>
</template>

<style scoped>
.qa-toolbar{position:fixed;z-index:1000;right:8px;top:72px;display:grid;gap:7px;width:238px;padding:10px;border:1px solid #e7bd6877;border-radius:13px;color:#e9eee9;background:#07151de8;box-shadow:0 15px 40px #000b;backdrop-filter:blur(10px);font-size:11px}.qa-toolbar.closed{top:8px;width:auto;padding:4px}.qa-toolbar label{display:grid;grid-template-columns:65px 1fr;align-items:center;gap:6px}.qa-toolbar select{width:100%;padding:4px;border:1px solid #60767a;border-radius:6px;color:#eef2ec;background:#14272e}.qa-toolbar .check{grid-template-columns:auto 1fr}.effects{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}.effects button,.qa-toggle{border:1px solid #806d48;border-radius:6px;padding:4px;color:#f0dfb2;background:#25383b;cursor:pointer}.qa-toggle{justify-self:end}.qa-toolbar small{overflow:hidden;color:#8eaaac;white-space:nowrap;text-overflow:ellipsis}@media(max-width:760px){.qa-toolbar{top:62px;width:185px}.effects{grid-template-columns:repeat(2,1fr)}}
</style>
