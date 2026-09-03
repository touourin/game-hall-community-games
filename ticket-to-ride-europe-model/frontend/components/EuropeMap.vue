<script setup lang="ts">
import { computed } from 'vue'
import type {
  BoardModel,
  DestinationTicketModel,
  EuropeEvent,
  EuropePlayerView,
  RouteClaimView,
  RouteModel,
  StationView,
} from '../types'

const props = withDefaults(defineProps<{
  board: BoardModel
  players: EuropePlayerView[]
  claimedRoutes: RouteClaimView[]
  stations: StationView[]
  legalRouteIds?: string[]
  stationCityIds?: string[]
  selectedRouteId?: string | null
  selectedCityId?: string | null
  focusedTickets?: DestinationTicketModel[]
  latestEvent?: EuropeEvent | null
  interactive?: boolean
}>(), {
  legalRouteIds: () => [],
  stationCityIds: () => [],
  selectedRouteId: null,
  selectedCityId: null,
  focusedTickets: () => [],
  latestEvent: null,
  interactive: false,
})

const emit = defineEmits<{
  selectRoute: [routeId: string]
  selectCity: [cityId: string]
}>()

const cities = computed(() => new Map(props.board.cities.map(city => [city.id, city])))
const claims = computed(() => new Map(props.claimedRoutes.map(claim => [claim.routeId, claim.ownerPlayerId])))
const players = computed(() => new Map(props.players.map(player => [player.id, player])))
const legal = computed(() => new Set(props.legalRouteIds))
const stationCities = computed(() => new Set(props.stationCityIds))
const focusedCities = computed(() => new Set(props.focusedTickets.flatMap(ticket => [ticket.fromCityId, ticket.toCityId])))

const routeColors: Record<string, string> = {
  purple: '#8562a9', blue: '#3985c3', orange: '#dc812e', white: '#ece9de',
  green: '#549263', yellow: '#d8b22d', black: '#454b52', red: '#c4544d', gray: '#959ba0',
}
const ownerColors: Record<string, string> = {
  ruby: '#d95b58', sapphire: '#4c92d4', jade: '#58a87c', amber: '#e5b24b', violet: '#9c73c5',
}

interface Geometry {
  x1: number
  y1: number
  x2: number
  y2: number
  angle: number
}

function geometry(route: RouteModel): Geometry {
  const start = cities.value.get(route.fromCityId)!.position
  const end = cities.value.get(route.toCityId)!.position
  let x1 = start.x
  let y1 = start.y
  let x2 = end.x
  let y2 = end.y
  if (route.parallelGroupId) {
    const dx = x2 - x1
    const dy = y2 - y1
    const length = Math.hypot(dx, dy) || 1
    const offset = route.trackIndex === 0 ? -7 : 7
    const ox = -dy / length * offset
    const oy = dx / length * offset
    x1 += ox; x2 += ox; y1 += oy; y2 += oy
  }
  return { x1, y1, x2, y2, angle: Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI }
}

function point(route: RouteModel, index: number) {
  const geo = geometry(route)
  const t = (index + 1) / (route.length + 1)
  return {
    x: geo.x1 + (geo.x2 - geo.x1) * t,
    y: geo.y1 + (geo.y2 - geo.y1) * t,
    angle: geo.angle,
  }
}

function routeStroke(route: RouteModel): string {
  const ownerId = claims.value.get(route.id)
  if (!ownerId) return routeColors[route.color]
  return ownerColors[players.value.get(ownerId)?.color ?? 'ruby']
}

function routeClass(route: RouteModel) {
  return {
    claimed: claims.value.has(route.id),
    legal: props.interactive && legal.value.has(route.id),
    selected: props.selectedRouteId === route.id,
    tunnel: route.kind === 'tunnel',
    ferry: route.kind === 'ferry',
    'just-claimed': props.latestEvent?.type === 'route_claimed' && props.latestEvent.routeId === route.id,
  }
}

function stationFor(cityId: string) {
  return props.stations.find(station => station.cityId === cityId)
}

function ownerColor(playerId: string): string {
  return ownerColors[players.value.get(playerId)?.color ?? 'ruby']
}

function activateRoute(routeId: string) {
  if (props.interactive && legal.value.has(routeId)) emit('selectRoute', routeId)
}

function activateCity(cityId: string) {
  if (props.interactive && stationCities.value.has(cityId)) emit('selectCity', cityId)
}
</script>

<template>
  <div class="map-shell" data-testid="europe-map">
    <svg
      class="europe-map"
      :viewBox="`0 0 ${board.coordinateSystem.width} ${board.coordinateSystem.height}`"
      role="img"
      aria-label="欧洲铁路版图，包含 47 座城市和 101 条轨道"
    >
      <defs>
        <radialGradient id="sea" cx="48%" cy="42%" r="72%">
          <stop offset="0" stop-color="#183c4a" />
          <stop offset=".58" stop-color="#102a36" />
          <stop offset="1" stop-color="#0a1a23" />
        </radialGradient>
        <linearGradient id="land" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#34473f" />
          <stop offset=".52" stop-color="#283b36" />
          <stop offset="1" stop-color="#202f2d" />
        </linearGradient>
        <filter id="map-shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="7" stdDeviation="8" flood-color="#000" flood-opacity=".48" />
        </filter>
        <filter id="route-glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="5" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <pattern id="paper-grain" width="28" height="28" patternUnits="userSpaceOnUse">
          <circle cx="4" cy="7" r="1" fill="#fff" opacity=".035" />
          <circle cx="20" cy="18" r="1.2" fill="#000" opacity=".06" />
        </pattern>
      </defs>

      <rect width="1360" height="880" rx="34" fill="url(#sea)" />
      <path class="coast-shadow" d="M28 175 C206 72 412 119 551 67 C732 -2 959 10 1125 96 C1260 166 1333 315 1324 477 C1314 661 1178 814 981 844 C770 875 615 789 469 823 C286 865 91 818 40 686 C-12 551 80 440 49 332 C28 258 1 215 28 175Z" />
      <path class="land" d="M28 175 C206 72 412 119 551 67 C732 -2 959 10 1125 96 C1260 166 1333 315 1324 477 C1314 661 1178 814 981 844 C770 875 615 789 469 823 C286 865 91 818 40 686 C-12 551 80 440 49 332 C28 258 1 215 28 175Z" />
      <path class="mountains" d="M425 584 L478 500 L523 571 L587 419 L642 543 L708 402 L772 553 L839 470 L917 596" />
      <path class="mountains faint" d="M949 339 L1031 270 L1100 349 L1170 242 L1248 342" />
      <path class="sea-route" d="M47 744 Q251 840 442 801 T846 824 T1282 742" />
      <rect width="1360" height="880" rx="34" fill="url(#paper-grain)" />

      <g class="ticket-focus" aria-hidden="true">
        <circle
          v-for="cityId in focusedCities"
          :key="cityId"
          :cx="cities.get(cityId)?.position.x"
          :cy="cities.get(cityId)?.position.y"
          r="25"
        />
      </g>

      <g class="routes">
        <g
          v-for="route in board.routes"
          :key="route.id"
          class="route"
          :class="routeClass(route)"
          :data-route-id="route.id"
          :role="legal.has(route.id) && interactive ? 'button' : undefined"
          :tabindex="legal.has(route.id) && interactive ? 0 : undefined"
          :aria-label="`${cities.get(route.fromCityId)?.labelZhCN}至${cities.get(route.toCityId)?.labelZhCN}，${route.length} 格${route.kind === 'tunnel' ? '隧道' : route.kind === 'ferry' ? '渡轮' : '轨道'}`"
          @click="activateRoute(route.id)"
          @keydown.enter.prevent="activateRoute(route.id)"
          @keydown.space.prevent="activateRoute(route.id)"
        >
          <line class="route-hit" v-bind="geometry(route)" />
          <line class="route-bed" v-bind="geometry(route)" />
          <line
            class="route-line"
            v-bind="geometry(route)"
            :stroke="routeStroke(route)"
          />
          <g class="route-ties" aria-hidden="true">
            <rect
              v-for="index in route.length"
              :key="index"
              :x="point(route, index - 1).x - 7"
              :y="point(route, index - 1).y - 3"
              width="14"
              height="6"
              rx="2"
              :transform="`rotate(${point(route, index - 1).angle} ${point(route, index - 1).x} ${point(route, index - 1).y})`"
              :fill="routeStroke(route)"
            />
          </g>
          <g v-if="route.kind === 'ferry'" class="ferry-marks" aria-hidden="true">
            <g v-for="index in route.locomotivesRequired" :key="index" :transform="`translate(${point(route, index - 1).x} ${point(route, index - 1).y})`">
              <circle r="8" />
              <path d="M-4 2h8V-2H1v-3h-3v3h-2z" />
            </g>
          </g>
          <circle v-if="selectedRouteId === route.id" class="route-start" :cx="geometry(route).x1" :cy="geometry(route).y1" r="12" />
        </g>
      </g>

      <g class="cities">
        <g
          v-for="city in board.cities"
          :key="city.id"
          class="city"
          :class="{ eligible: interactive && stationCities.has(city.id), selected: selectedCityId === city.id, focused: focusedCities.has(city.id) }"
          :data-city-id="city.id"
          :role="stationCities.has(city.id) && interactive ? 'button' : undefined"
          :tabindex="stationCities.has(city.id) && interactive ? 0 : undefined"
          :transform="`translate(${city.position.x} ${city.position.y})`"
          @click="activateCity(city.id)"
          @keydown.enter.prevent="activateCity(city.id)"
          @keydown.space.prevent="activateCity(city.id)"
        >
          <circle class="city-halo" r="13" />
          <circle class="city-node" r="7" />
          <text
            :x="city.position.x > 980 ? -11 : 11"
            :y="city.position.y < 60 ? 22 : -10"
            :text-anchor="city.position.x > 980 ? 'end' : 'start'"
          >{{ city.boardLabel }}</text>
          <text
            class="city-zh"
            :x="city.position.x > 980 ? -11 : 11"
            :y="city.position.y < 60 ? 34 : 3"
            :text-anchor="city.position.x > 980 ? 'end' : 'start'"
          >{{ city.labelZhCN }}</text>
          <g v-if="stationFor(city.id)" class="station" :style="{ '--owner': ownerColor(stationFor(city.id)?.ownerPlayerId ?? '') }" aria-label="火车站">
            <circle r="16" />
            <path d="M-8 8V-6L0-13 8-6V8H3V0h-6v8z" />
          </g>
        </g>
      </g>

      <g class="map-cartouche" transform="translate(35 33)">
        <rect width="283" height="73" rx="14" />
        <text x="18" y="27">EUROPE RAIL NETWORK</text>
        <text class="sub" x="18" y="48">47 CITIES · 101 TRACKS · BASE MAP</text>
        <path d="M18 59H80" /><path class="tunnel-key" d="M103 59h62" /><path class="ferry-key" d="M188 59h62" />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.map-shell{position:relative;width:100%;height:100%;min-height:0;overflow:hidden;border-radius:20px;background:#0b1b24;box-shadow:inset 0 0 0 1px #ffffff12,0 24px 55px #0007}.europe-map{display:block;width:100%;height:100%;filter:saturate(.96);user-select:none}.coast-shadow{fill:#020b0f;opacity:.45;transform:translateY(8px);filter:url(#map-shadow)}.land{fill:url(#land);stroke:#708078;stroke-width:3;opacity:.96}.mountains{fill:none;stroke:#9ca49a22;stroke-width:16;stroke-linejoin:round}.mountains.faint{stroke-width:11;opacity:.55}.sea-route{fill:none;stroke:#6aa7b31c;stroke-width:3;stroke-dasharray:12 13}.ticket-focus circle{fill:#f5d27718;stroke:#f5d27788;stroke-width:3;animation:focus-pulse 1.8s ease-in-out infinite}.route{outline:none}.route-hit{stroke:transparent;stroke-width:24;pointer-events:stroke}.route-bed{stroke:#071116;stroke-width:12;stroke-linecap:round;pointer-events:none}.route-line{stroke-width:7;stroke-linecap:round;opacity:.95;pointer-events:none}.route.tunnel .route-line{stroke-dasharray:13 8}.route.ferry .route-line{stroke-dasharray:4 9}.route-ties rect{stroke:#071116;stroke-width:1.5;pointer-events:none}.route.claimed .route-line{stroke-width:8;filter:drop-shadow(0 2px 2px #0008)}.route.legal{cursor:pointer}.route.legal .route-line{filter:url(#route-glow)}.route.legal:hover .route-line,.route.legal:focus-visible .route-line{stroke:#f4d27a;stroke-width:11}.route.selected .route-line{stroke:#fff0ae;stroke-width:12;filter:url(#route-glow)}.route.selected .route-ties rect{fill:#fff0ae}.route.just-claimed .route-line{stroke-dasharray:900;stroke-dashoffset:900;animation:claim-route 1.15s cubic-bezier(.2,.8,.2,1) forwards}.route-start{fill:none;stroke:#f7d378;stroke-width:3;animation:focus-pulse 1s infinite}.ferry-marks circle{fill:#e8e5d9;stroke:#15222a;stroke-width:2}.ferry-marks path{fill:#17242c}.city{outline:none}.city-halo{fill:#061116aa;stroke:#8fa09666;stroke-width:1}.city-node{fill:#f0d49d;stroke:#101a1f;stroke-width:3}.city text{fill:#f7f0db;font-family:Inter,"Microsoft YaHei",sans-serif;font-size:10px;font-weight:900;letter-spacing:.035em;paint-order:stroke;stroke:#071218;stroke-width:3;stroke-linejoin:round}.city .city-zh{fill:#c8d3cc;font-size:7px;font-weight:700;stroke-width:2.5}.city.eligible{cursor:pointer}.city.eligible .city-halo{fill:#f1c85d38;stroke:#f1c85d;stroke-width:3;animation:city-ready 1.4s ease-in-out infinite}.city.eligible:hover .city-node,.city.eligible:focus-visible .city-node,.city.selected .city-node{fill:#fff4bb;stroke:#eebf57;stroke-width:5}.city.focused .city-node{fill:#fff1a9}.station{--owner:#d95b58}.station circle{fill:#122027;stroke:var(--owner);stroke-width:5;filter:drop-shadow(0 4px 4px #0008)}.station path{fill:var(--owner);stroke:#f7e7bd;stroke-width:1}.map-cartouche rect{fill:#07131ed9;stroke:#8aa09b88}.map-cartouche text{fill:#f4e7cb;font-family:Inter,"Microsoft YaHei",sans-serif;font-size:14px;font-weight:900;letter-spacing:.06em}.map-cartouche .sub{fill:#9eb4b5;font-size:8px;font-weight:700}.map-cartouche path{stroke:#9ca3a6;stroke-width:5}.map-cartouche .tunnel-key{stroke-dasharray:12 7}.map-cartouche .ferry-key{stroke-dasharray:3 8}@keyframes claim-route{to{stroke-dashoffset:0}}@keyframes focus-pulse{50%{opacity:.4;transform:scale(1.15)}}@keyframes city-ready{50%{r:17;opacity:.55}}@media(max-width:760px){.map-cartouche{transform:translate(20px 20px) scale(.78);transform-origin:top left}.city text{font-size:12px}.city .city-zh{display:none}.route-hit{stroke-width:32}}@media(prefers-reduced-motion:reduce){.route.just-claimed .route-line,.ticket-focus circle,.city.eligible .city-halo,.route-start{animation:none!important}}
</style>
