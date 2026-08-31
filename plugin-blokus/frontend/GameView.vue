<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Check, Expand, FlipHorizontal2,
  HelpCircle, Minimize, RotateCw, Sparkles, Trophy,
} from '@lucide/vue'
import {
  PluginButton, PluginIconButton, PluginModal, usePluginGameActions,
  type ArcadeSnapshot,
} from '@game-hall/plugin-sdk'
import {
  PIECES, SIZE, findPlacement, inside, legalAnchors, placementError, signedPoints, transform,
  type BlokusGame, type BlokusPlayer, type Cell, type Piece,
} from './rules'

const props = defineProps<{ snapshot: ArcadeSnapshot }>()
const actions = usePluginGameActions()
const game = computed(() => props.snapshot.game as unknown as BlokusGame)
const players = computed(() => game.value.players ?? [])
const board = computed(() => game.value.board ?? Array.from({ length: SIZE }, () => Array<number>(SIZE).fill(-1)))
const spectator = computed(() => props.snapshot.viewer?.mode === 'spectator')
const me = computed(() => spectator.value ? undefined : players.value.find((player) => player.id === props.snapshot.self.id))
const current = computed(() => players.value.find((player) => player.id === game.value.currentPlayerId))
const finished = computed(() => props.snapshot.phase === 'finished')
const canAct = computed(() => !spectator.value && props.snapshot.phase === 'playing'
  && game.value.isMyTurn && game.value.currentPlayerId === props.snapshot.self.id
  && props.snapshot.actions.canAct && me.value?.status === 'active')
const inspectedId = ref<string | null>(null)
const inspected = computed(() => players.value.find((player) => player.id === inspectedId.value)
  ?? me.value ?? current.value ?? players.value[0])
const ownTray = computed(() => inspected.value?.id === me.value?.id && !!me.value)
const canPreview = computed(() => ownTray.value && props.snapshot.phase === 'playing' && me.value?.status === 'active')
const colorIndex = computed(() => players.value.findIndex((player) => player.id === me.value?.id))
const selectedId = ref<string | null>(null)
const selected = computed(() => PIECES.find((piece) => piece.id === selectedId.value))
const rotation = ref(0)
const flipped = ref(false)
const anchor = ref<Cell | null>(null)
const pending = ref(false)
const showRules = ref(false)
const zoomed = ref(false)
const notice = ref('')
const boardSvg = ref<SVGSVGElement | null>(null)
const boardPanel = ref<HTMLElement | null>(null)
const shape = computed(() => selected.value ? transform(selected.value.cells, rotation.value, flipped.value) : [])
const preview = computed<Cell[]>(() => anchor.value
  ? shape.value.map(([x, y]) => [x + anchor.value![0], y + anchor.value![1]]) : [])
const firstMove = computed(() => me.value?.remainingPieces.length === 21)
const previewError = computed(() => !selected.value ? '先选一块棋块，再点击棋盘定位'
  : !anchor.value ? '点击棋盘设置落点'
    : placementError(board.value, colorIndex.value, preview.value, firstMove.value))
const anchors = computed(() => canPreview.value && selected.value
  ? legalAnchors(board.value, colorIndex.value, firstMove.value) : [])
const ready = computed(() => canAct.value && selected.value && anchor.value && !previewError.value && !pending.value)
const occupied = computed(() => board.value.flatMap((row, y) => row.flatMap((color, x) => color < 0 ? [] : [{ x, y, color }])))
const visiblePreview = computed(() => preview.value.filter(([x, y]) => inside(x, y)))
const lastCells = computed(() => game.value.lastMove?.cells ?? [])
const ranking = computed(() => [...players.value].sort((a, b) => (a.rank ?? 5) - (b.rank ?? 5)))
const gridPath = Array.from({ length: SIZE + 1 }, (_, index) => `M${index * 20} 0V400M0 ${index * 20}H400`).join(' ')
const colorClasses = ['blue', 'yellow', 'red', 'green']
const cornerNames = ['左上角', '右上角', '右下角', '左下角']
const statusNames = { active: '等待', blocked: '无处可放', finished: '全部放完', forfeited: '已弃权' }
const sizeGroups = [5, 4, 3, 2, 1]

function name(id: string | null | undefined): string {
  return props.snapshot.players.find((player) => player.id === id)?.name ?? '玩家'
}

function playerStatus(player: BlokusPlayer): string {
  if (finished.value) return `第 ${player.rank} 名 · ${signedPoints(player.points)} 分`
  if (player.status !== 'active') return statusNames[player.status]
  if (props.snapshot.players.find(member => member.id === player.id)?.connected === false) return '暂时离线 · 保留座位'
  return player.id === game.value.currentPlayerId ? '正在落子' : '等待回合'
}

function pieceViewBox(piece: Piece): string {
  const width = Math.max(...piece.cells.map(([x]) => x)) + 1
  const height = Math.max(...piece.cells.map(([, y]) => y)) + 1
  return `${(width * 10 - 52) / 2} ${(height * 10 - 42) / 2} 52 42`
}

function clearSelection(): void {
  selectedId.value = null
  anchor.value = null
  rotation.value = 0
  flipped.value = false
  notice.value = ''
}

watch([
  () => props.snapshot.roundNumber,
  () => game.value.turnNumber,
  () => props.snapshot.phase,
  () => props.snapshot.self.id,
  () => props.snapshot.viewer?.mode,
], clearSelection)
watch(inspectedId, clearSelection)

function selectPiece(piece: Piece): void {
  if (!canPreview.value || !me.value?.remainingPieces.includes(piece.id) || pending.value) return
  selectedId.value = piece.id
  rotation.value = 0
  flipped.value = false
  notice.value = ''
  if (firstMove.value) {
    const move = findPlacement(board.value, colorIndex.value, piece, true)
    if (move) {
      anchor.value = [move.x, move.y]
      rotation.value = move.rotation
      flipped.value = move.flipped
    }
  } else anchor.value = null
  if (typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 900px)').matches) {
    boardPanel.value?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }
}

function point(event: PointerEvent): void {
  if (!canPreview.value || !selected.value || pending.value || !boardSvg.value) return
  const rect = boardSvg.value.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  const x = Math.floor((event.clientX - rect.left) / rect.width * SIZE)
  const y = Math.floor((event.clientY - rect.top) / rect.height * SIZE)
  if (inside(x, y)) {
    anchor.value = [x, y]
    notice.value = ''
  }
}

function nudge(dx: number, dy: number): void {
  if (!canPreview.value || !selected.value || pending.value) return
  const [x, y] = anchor.value ?? me.value?.corner ?? [0, 0]
  anchor.value = [Math.max(0, Math.min(19, x + dx)), Math.max(0, Math.min(19, y + dy))]
  notice.value = ''
}

function rotate(): void {
  if (canPreview.value && selected.value && !pending.value) rotation.value = (rotation.value + 1) % 4
}

function flip(): void {
  if (canPreview.value && selected.value && !pending.value) flipped.value = !flipped.value
}

function suggest(): void {
  if (!canPreview.value || !selected.value || pending.value) return
  const move = findPlacement(board.value, colorIndex.value, selected.value, firstMove.value)
  if (!move) {
    notice.value = '这块目前没有合法落点，请换一块试试。'
    return
  }
  rotation.value = move.rotation
  flipped.value = move.flipped
  anchor.value = [move.x, move.y]
  notice.value = '已找到一个可放位置，确认后才会落子。'
}

async function place(): Promise<void> {
  if (!ready.value || !selected.value || !anchor.value) return
  pending.value = true
  try {
    const ok = await actions.action('place', {
      pieceId: selected.value.id, x: anchor.value[0], y: anchor.value[1],
      rotation: rotation.value, flipped: flipped.value, turnNumber: game.value.turnNumber,
    })
    if (ok) clearSelection()
    else notice.value = '落子未提交，请查看房间提示并重新选择。'
  } catch {
    notice.value = '连接暂时中断，请等待重连后再试。'
  } finally {
    pending.value = false
  }
}

function keydown(event: KeyboardEvent): void {
  if (!canPreview.value || !selected.value) return
  const key = event.key.toLowerCase()
  const directions: Record<string, Cell> = { arrowleft: [-1, 0], arrowright: [1, 0], arrowup: [0, -1], arrowdown: [0, 1] }
  const direction = directions[key]
  if (!direction && !['r', 'f', 'enter', 'escape'].includes(key)) return
  event.preventDefault()
  if (direction) nudge(...direction)
  if (key === 'r') rotate()
  if (key === 'f') flip()
  if (key === 'enter') void place()
  if (key === 'escape') clearSelection()
}

async function restart(): Promise<void> {
  if (pending.value || spectator.value || !props.snapshot.actions.canRestart) return
  pending.value = true
  try { await actions.restart() } finally { pending.value = false }
}
</script>

<template>
  <section class="blokus" :class="me?.color ?? 'blue'" aria-label="四人方格对局">
    <header class="game-heading">
      <div><p class="eyebrow">FOUR CORNERS · 20 × 20</p><h2>四人方格</h2></div>
      <PluginButton variant="secondary" @click="showRules = true"><HelpCircle :size="17" /> 玩法</PluginButton>
    </header>

    <div class="player-grid" aria-label="四位玩家与起始角">
      <button v-for="(player, index) in players" :key="player.id" type="button"
        class="player-card" :class="[player.color, { current: current?.id === player.id && !finished, inspected: inspected?.id === player.id }]"
        :aria-pressed="inspected?.id === player.id" :aria-label="`查看${name(player.id)}的棋块，${cornerNames[index]}`"
        @click="inspectedId = player.id">
        <span class="player-title"><i class="color-dot" /><strong>{{ name(player.id) }}</strong><small v-if="player.id === me?.id">你</small></span>
        <span class="corner-label">{{ player.colorName }}方 · {{ cornerNames[index] }}</span>
        <span class="player-metric"><b>{{ player.remainingSquares }}</b> <small>格未放 · {{ player.remainingPieces.length }} 块</small></span>
        <span class="player-status">{{ playerStatus(player) }}</span>
      </button>
    </div>

    <div class="turn-strip" :class="{ mine: canAct }" role="status">
      <i class="turn-light" />
      <div>
        <strong v-if="finished">本局已结束</strong>
        <strong v-else-if="canAct">轮到你了 · {{ me?.colorName }}方落子</strong>
        <strong v-else-if="me?.status === 'blocked'">你已无合法落点 · 等待其他玩家完成</strong>
        <strong v-else-if="me?.status === 'finished'">你的 21 块已全部放完</strong>
        <strong v-else-if="me?.status === 'forfeited'">你已弃权 · 可继续查看棋局</strong>
        <strong v-else>{{ spectator ? '观战中' : '等待回合' }} · {{ name(current?.id) }}正在落子</strong>
        <span>{{ finished ? '按剩余方格数从少到多排名' : firstMove && canAct ? '第一块必须覆盖你的起始角' : '同色角接，不可边接；不同颜色可以相邻' }}</span>
      </div>
      <small>已落 {{ game.moveCount ?? 0 }} 块</small>
    </div>

    <section v-if="finished" class="result-panel" aria-label="最终排名积分">
      <div class="result-heading"><Trophy :size="24" /><div><p class="eyebrow">FINAL STANDINGS</p><h3>{{ name(ranking[0]?.id) }}获得冠军</h3></div></div>
      <div class="ranking-list">
        <div v-for="player in ranking" :key="player.id" class="ranking-row" :class="player.color" :aria-label="`${name(player.id)}第${player.rank}名，${signedPoints(player.points)}分`">
          <span class="rank-number">{{ player.rank }}</span><i class="color-dot" />
          <div><strong>{{ name(player.id) }}{{ player.id === me?.id ? '（你）' : '' }}</strong><small>{{ player.remainingSquares }} 格 / {{ player.remainingPieces.length }} 块未放{{ player.status === 'forfeited' ? ' · 弃权' : '' }}</small></div>
          <b class="rank-points">{{ signedPoints(player.points) }} <small>分</small></b>
        </div>
      </div>
      <p class="muted-note">{{ snapshot.statsEligible === false ? '本局含游客，不记录账号战绩，也不计入大厅排行榜。' : '本局按名次结算：第 1 名 +2，第 2 名 +1，第 3 名 0，第 4 名 −1。单局积分可在战绩说明中查看。' }}</p>
      <PluginButton v-if="snapshot.actions.canRestart && !spectator" :disabled="pending" @click="restart">再来一局</PluginButton>
    </section>

    <div class="workbench">
      <div ref="boardPanel" class="board-panel">
        <div class="panel-heading"><h3>{{ finished ? '终局棋盘' : '棋盘' }}</h3><PluginButton variant="secondary" compact @click="zoomed = !zoomed"><Minimize v-if="zoomed" :size="16" /><Expand v-else :size="16" />{{ zoomed ? '适应宽度' : '放大棋盘' }}</PluginButton></div>
        <div class="board-scroll" :class="{ zoomed }">
          <svg ref="boardSvg" class="board-svg" viewBox="0 0 400 400" tabindex="0" role="application"
            aria-label="20×20 方格棋盘，选择棋块后点击定位，方向键微调，R 旋转，F 翻转，回车确认"
            @pointerdown="point" @keydown="keydown">
            <title>四人方格棋盘：蓝左上、黄右上、红右下、绿左下</title>
            <rect class="board-base" width="400" height="400" />
            <rect v-for="cell in occupied" :key="`${cell.x}:${cell.y}`" :class="['tile', colorClasses[cell.color]]" :x="cell.x * 20 + 1" :y="cell.y * 20 + 1" width="18" height="18" rx="2" />
            <path :d="gridPath" class="grid-lines" />
            <g v-for="(player, index) in players" :key="player.id" :class="player.color" class="corner-marker">
              <rect v-if="board[player.corner[1]]?.[player.corner[0]] === -1" :x="player.corner[0] * 20 + 2" :y="player.corner[1] * 20 + 2" width="16" height="16" rx="3" />
              <text v-if="board[player.corner[1]]?.[player.corner[0]] === -1" :x="player.corner[0] * 20 + 10" :y="player.corner[1] * 20 + 14">{{ index + 1 }}</text>
            </g>
            <circle v-for="[x, y] in anchors" :key="`anchor:${x}:${y}`" class="anchor-dot" :cx="x * 20 + 10" :cy="y * 20 + 10" r="2.2" />
            <rect v-for="[x, y] in lastCells" :key="`last:${x}:${y}`" class="last-tile" :x="x * 20 + 4" :y="y * 20 + 4" width="12" height="12" rx="1" />
            <rect v-for="[x, y] in visiblePreview" :key="`preview:${x}:${y}`" :class="['preview-tile', { invalid: !!previewError }]" :x="x * 20 + 1" :y="y * 20 + 1" width="18" height="18" rx="2" />
          </svg>
        </div>
        <p class="board-caption">20 × 20 · {{ zoomed ? '可滚动棋盘查看四角' : '角落数字对应蓝、黄、红、绿的出手顺序' }}</p>

        <div v-if="!finished && me" class="placement-controls" aria-label="落子操作">
          <div class="selection-line"><strong>{{ selected ? `${selected.id} · ${selected.size} 格` : '选择你的棋块' }}</strong><span>{{ anchor ? `左上定位 ${anchor[0] + 1} 列 / ${anchor[1] + 1} 行` : '点棋盘定位，再确认落子' }}</span></div>
          <div class="transform-controls">
            <PluginButton variant="secondary" :disabled="!selected || !canPreview || pending" @click="rotate"><RotateCw :size="17" />旋转</PluginButton>
            <PluginButton variant="secondary" :disabled="!selected || !canPreview || pending" @click="flip"><FlipHorizontal2 :size="17" />翻转</PluginButton>
            <PluginButton variant="secondary" :disabled="!selected || !canPreview || pending" @click="suggest"><Sparkles :size="17" />找落点</PluginButton>
          </div>
          <div class="nudge-controls" aria-label="逐格微调">
            <PluginIconButton label="向左一格" :disabled="!selected || !canPreview || pending" @click="nudge(-1, 0)"><ArrowLeft :size="18" /></PluginIconButton>
            <PluginIconButton label="向上一格" :disabled="!selected || !canPreview || pending" @click="nudge(0, -1)"><ArrowUp :size="18" /></PluginIconButton>
            <PluginIconButton label="向下一格" :disabled="!selected || !canPreview || pending" @click="nudge(0, 1)"><ArrowDown :size="18" /></PluginIconButton>
            <PluginIconButton label="向右一格" :disabled="!selected || !canPreview || pending" @click="nudge(1, 0)"><ArrowRight :size="18" /></PluginIconButton>
          </div>
          <p class="placement-status" :class="{ valid: !previewError && !!selected }" role="status">{{ notice || previewError || '位置合法，可以确认落子' }}</p>
          <PluginButton block :disabled="!ready" @click="place"><Check :size="18" />{{ pending ? '正在提交…' : canAct ? '确认落子' : '等待你的回合' }}</PluginButton>
          <small class="keyboard-note">棋盘聚焦后：方向键微调 · R 旋转 · F 翻转 · Enter 确认</small>
        </div>
      </div>

      <aside class="inventory" :class="inspected?.color ?? 'blue'" aria-label="棋块库">
        <div class="panel-heading"><div><p class="eyebrow">PIECE LIBRARY</p><h3>{{ ownTray ? '你的棋块' : `${name(inspected?.id)}的棋块` }}</h3></div><span class="piece-count">{{ inspected?.remainingPieces.length ?? 21 }}<small> / 21</small></span></div>
        <p class="inventory-note">{{ !ownTray ? '公开棋块库 · 仅供查看' : canPreview ? '选择一块，旋转或翻转后放到棋盘上。' : '查看本局剩余棋块。' }}<br />每人共 89 小格，灰色棋块已使用。</p>
        <PluginButton v-if="me && !ownTray" variant="secondary" block @click="inspectedId = me.id">返回我的棋块</PluginButton>
        <div v-for="size in sizeGroups" :key="size" class="piece-group">
          <div class="group-label"><span>{{ size }} 格块</span><span>{{ PIECES.filter(piece => piece.size === size && inspected?.remainingPieces.includes(piece.id)).length }} 块可用</span></div>
          <div class="piece-grid">
            <button v-for="piece in PIECES.filter(piece => piece.size === size)" :key="piece.id" type="button" class="piece-button"
              :class="{ selected: selectedId === piece.id && ownTray, used: !inspected?.remainingPieces.includes(piece.id) }"
              :disabled="!canPreview || pending || !inspected?.remainingPieces.includes(piece.id)"
              :aria-label="`${piece.id}，${size} 格${!inspected?.remainingPieces.includes(piece.id) ? '，已使用' : ''}`"
              :aria-pressed="selectedId === piece.id && ownTray" @click="selectPiece(piece)">
              <svg :viewBox="pieceViewBox(piece)" aria-hidden="true"><rect v-for="[x, y] in piece.cells" :key="`${x}:${y}`" :x="x * 10 + .5" :y="y * 10 + .5" width="9" height="9" rx="1" /></svg>
              <span>{{ piece.id }}</span><Check v-if="!inspected?.remainingPieces.includes(piece.id)" class="used-check" :size="12" />
            </button>
          </div>
        </div>
        <div class="scoring-note"><Trophy :size="17" /><p>名次积分<br /><strong>+2 <i>/</i> +1 <i>/</i> 0 <i>/</i> −1</strong></p><small>剩余格数越少<br />名次越靠前</small></div>
      </aside>
    </div>

    <div v-if="game.events?.length" class="event-log" aria-label="对局动态"><h3>对局动态</h3><p v-for="(event, index) in [...game.events].reverse()" :key="index">{{ event }}</p></div>

    <PluginModal v-if="showRules" title="四人方格 · 玩法" aria-label="四人方格玩法规则" size="medium" mobile-sheet @close="showRules = false">
      <div class="rule-content">
        <section><h3>四人，从四角出发</h3><p>棋盘为 20×20。每人 21 块，共 89 小格：1 个单格块、1 个双格块、2 个三格块、5 个四格块、12 个五格块。四人的形状完全相同。</p><p>首局由大厅按房间设置安排座位，依次分配蓝、黄、红、绿，分别从左上、右上、右下、左下角开始，按此顺序轮流行动。四人准备后再来一局，座位向前轮换一位，让每人依次体验四个起始角。</p></section>
        <section><h3>每回合放一块</h3><ol><li>首块必须覆盖自己的起始角格。</li><li>之后每块至少与一块自己的棋块角接；同色绝不能边接。不同颜色可以边接或角接。</li><li>可以旋转、翻转，但不能重叠、越界或移动已落下的棋块。</li><li>选择棋块后点击棋盘定位，用旋转、翻转和方向按钮微调，再点「确认落子」。小圆点提示可角接的空格，「找落点」可寻找当前棋块的一个合法位置。</li><li>只有全部剩余棋块都无处可放，才会自动跳过；不能主动跳过。已放完的玩家也自动跳过，其他人继续。</li></ol></section>
        <section><h3>终局与名次积分</h3><p>所有人都放完或无处可放时结束。按剩余小方格数从少到多排名：第 1 名 +2 分，第 2 名 +1 分，第 3 名 0 分，第 4 名 −1 分。</p><p>本平台补充同分规则：剩余格数相同时，剩余块数少者优先；仍相同则本局出手顺序较后的玩家优先，保证四个独立名次。不使用经典版的放完奖励分。</p><p>主动退出或掉线超时视为弃权，已落棋块保留。弃权者排在其他玩家之后，多人弃权时越早弃权名次越后；仅剩一位未弃权玩家时立即结算。</p><p>单局名次分保存在战绩说明中。大厅排行榜沿用胜负规则，不累计名次分。含游客的对局可以游玩，但不记录账号战绩，也不计入大厅排行榜。</p></section>
        <p class="rule-source">规则参考 <a href="https://service.mattel.com/instruction_sheets/BJV44-Eng.pdf" target="_blank" rel="noopener noreferrer">Mattel Blokus 官方说明</a>；名次积分及同分、弃权排序为本平台规则。</p>
      </div>
    </PluginModal>
  </section>
</template>

<style scoped>
.blokus { --piece: var(--piece-blue); --piece-blue: #478bd0; --piece-yellow: #d5a32c; --piece-red: #d86b63; --piece-green: #4c9e87; width: min(100%, 1160px); min-width: 0; max-width: 100%; margin: 0 auto; color: var(--text); display: grid; gap: 18px; }
.blue { --piece: var(--piece-blue); }.yellow { --piece: var(--piece-yellow); }.red { --piece: var(--piece-red); }.green { --piece: var(--piece-green); }
.blokus * { box-sizing: border-box; }.game-heading, .panel-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; min-width: 0; }.game-heading h2 { font-size: clamp(24px, 3vw, 34px); margin: 2px 0 0; letter-spacing: .06em; }.eyebrow { margin: 0 0 5px; font-size: 10px; font-weight: 700; letter-spacing: .14em; color: var(--muted); }.blokus h3 { margin: 0; font-size: 16px; }.panel-heading h3 { overflow-wrap: anywhere; }.player-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }.player-card { position: relative; display: grid; gap: 7px; min-width: 0; padding: 13px; border: 1px solid var(--line); border-top: 3px solid var(--piece); border-radius: 13px; background: var(--surface-elevated); box-shadow: var(--shadow-contact); color: var(--text); text-align: left; font: inherit; cursor: pointer; }.player-card.current { background: color-mix(in srgb, var(--piece) 9%, var(--surface-elevated)); border-color: color-mix(in srgb, var(--piece) 70%, var(--line)); }.player-card.inspected { outline: 1px solid color-mix(in srgb, var(--piece) 45%, transparent); outline-offset: 2px; }.player-title { display: flex; align-items: center; gap: 7px; min-width: 0; }.player-title strong { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.player-title small { font-size: 10px; padding: 1px 4px; border-radius: 4px; border: 1px solid var(--line); }.color-dot { width: 9px; height: 9px; border-radius: 3px; flex-shrink: 0; background: var(--piece); }.corner-label, .player-metric small { font-size: 11px; color: var(--text-soft); }.player-metric b { font-size: 24px; font-variant-numeric: tabular-nums; font-weight: 650; }.player-status { font-size: 11px; color: var(--text-soft); }.player-card.current .player-status { font-weight: 700; color: var(--text); }
.turn-strip { display: flex; align-items: center; gap: 11px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface-inset); }.turn-strip.mine { border-color: color-mix(in srgb, var(--piece) 55%, var(--line)); background: color-mix(in srgb, var(--piece) 6%, var(--surface-elevated)); }.turn-light { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }.mine .turn-light { background: var(--piece); box-shadow: 0 0 0 4px color-mix(in srgb, var(--piece) 12%, transparent); }.turn-strip > div { flex: 1; min-width: 0; display: grid; gap: 4px; }.turn-strip strong { font-size: 14px; overflow-wrap: anywhere; }.turn-strip span, .turn-strip > small { font-size: 11px; color: var(--text-soft); }.turn-strip > small { white-space: nowrap; }
.workbench { display: grid; grid-template-columns: minmax(0, 1fr) 320px; align-items: start; gap: 20px; }.board-panel, .inventory { min-width: 0; border: 1px solid var(--line); border-radius: 16px; padding: 16px; background: var(--surface-elevated); box-shadow: var(--shadow-raised); }.board-panel { scroll-margin-top: 16px; }.panel-heading > button { min-height: 44px; }.board-scroll { width: 100%; overflow: auto; overscroll-behavior: contain; margin-top: 13px; border: 1px solid var(--line-strong); border-radius: 7px; background: var(--surface-inset); }.board-svg { display: block; width: 100%; aspect-ratio: 1; touch-action: pan-x pan-y; user-select: none; cursor: crosshair; }.board-scroll.zoomed .board-svg { width: 170%; min-width: 600px; }.board-base { fill: var(--surface-inset); }.tile { fill: var(--piece); stroke: color-mix(in srgb, var(--piece) 70%, var(--text)); stroke-width: .5; }.grid-lines { stroke: var(--line-strong); stroke-width: .65; fill: none; pointer-events: none; }.corner-marker rect { fill: color-mix(in srgb, var(--piece) 15%, var(--surface-inset)); stroke: var(--piece); stroke-width: 1.8; }.corner-marker text { font: 700 11px sans-serif; fill: var(--text); text-anchor: middle; }.anchor-dot { fill: var(--piece); opacity: .8; pointer-events: none; }.last-tile { fill: none; stroke: #162432; stroke-opacity: .7; stroke-width: 1; pointer-events: none; }.preview-tile { fill: color-mix(in srgb, var(--piece) 65%, transparent); stroke: var(--text); stroke-width: 1.3; stroke-dasharray: 3 2; pointer-events: none; }.preview-tile.invalid { fill: color-mix(in srgb, var(--text) 20%, transparent); stroke: var(--text); stroke-dasharray: 1.5 1.5; }.board-caption { color: var(--muted); font-size: 10px; text-align: center; margin: 8px 0 0; }.placement-controls { display: grid; gap: 10px; border-top: 1px solid var(--line); padding-top: 14px; margin-top: 13px; }.selection-line { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px; }.selection-line strong { font-size: 13px; }.selection-line span { color: var(--text-soft); font-size: 11px; }.transform-controls { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }.nudge-controls { display: flex; justify-content: center; gap: 10px; }.nudge-controls > * { min-width: 44px; min-height: 44px; }.placement-status { margin: 0; min-height: 18px; font-size: 12px; color: var(--text-soft); text-align: center; overflow-wrap: anywhere; }.placement-status.valid { color: var(--text); }.keyboard-note { color: var(--muted); font-size: 10px; text-align: center; }
.inventory { display: grid; gap: 13px; }.piece-count { color: var(--text); font-size: 22px; font-variant-numeric: tabular-nums; white-space: nowrap; }.piece-count small { color: var(--muted); font-size: 12px; }.inventory-note { font-size: 11px; color: var(--text-soft); line-height: 1.8; margin: 0; }.piece-group { display: grid; gap: 7px; }.group-label { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--muted); }.group-label span:first-child { color: var(--text-soft); font-weight: 650; }.piece-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }.piece-button { position: relative; min-width: 0; min-height: 68px; display: grid; justify-items: center; align-content: center; gap: 1px; border: 1px solid var(--line); border-radius: 8px; background: var(--control-surface); color: var(--text-soft); font: inherit; cursor: pointer; padding: 4px; }.piece-button > svg:not(.used-check) { display: block; width: 100%; max-width: 56px; height: 42px; }.piece-button rect { fill: var(--piece); stroke: color-mix(in srgb, var(--piece) 70%, var(--text)); stroke-width: .4; }.piece-button span { font-size: 9px; letter-spacing: .03em; }.piece-button:disabled { cursor: default; }.piece-button.used { opacity: .34; }.piece-button.used rect { fill: var(--muted); stroke: var(--muted); }.piece-button.selected { border-color: var(--piece); background: color-mix(in srgb, var(--piece) 12%, var(--control-surface)); outline: 1px solid var(--piece); }.used-check { width: 12px; height: 12px; position: absolute; top: 4px; right: 4px; }.piece-button:not(:disabled):hover { border-color: var(--piece); }.scoring-note { display: flex; gap: 10px; align-items: center; border-top: 1px solid var(--line); padding-top: 13px; color: var(--text-soft); }.scoring-note p { margin: 0; font-size: 10px; line-height: 1.8; }.scoring-note strong { font-size: 14px; color: var(--text); font-variant-numeric: tabular-nums; }.scoring-note i { font-style: normal; font-weight: 400; color: var(--muted); padding: 0 4px; }.scoring-note > small { margin-left: auto; font-size: 10px; line-height: 1.7; }
.result-panel { padding: 22px; display: grid; gap: 15px; border: 1px solid var(--line-strong); border-radius: 16px; background: var(--surface-elevated); }.result-heading { display: flex; gap: 12px; align-items: center; }.result-heading h3 { overflow-wrap: anywhere; }.ranking-list { display: grid; gap: 1px; }.ranking-row { display: flex; align-items: center; gap: 12px; padding: 12px 4px; border-bottom: 1px solid var(--line); min-width: 0; }.rank-number { font-size: 22px; width: 24px; color: var(--muted); }.ranking-row > div { min-width: 0; display: grid; gap: 3px; }.ranking-row strong { font-size: 13px; overflow-wrap: anywhere; }.ranking-row small { font-size: 11px; color: var(--text-soft); }.rank-points { margin-left: auto; font-size: 24px; white-space: nowrap; }.rank-points small { font-weight: 400; }.muted-note { font-size: 12px; color: var(--text-soft); line-height: 1.7; margin: 0; }.event-log { border-top: 1px solid var(--line); padding-top: 15px; }.event-log h3 { font-size: 12px; margin-bottom: 8px; }.event-log p { margin: 4px 0; color: var(--text-soft); font-size: 11px; }.rule-content { display: grid; gap: 12px; color: var(--text); line-height: 1.85; font-size: 13px; }.rule-content h3 { font-size: 15px; margin: 0; }.rule-content p { margin: 7px 0; }.rule-content ol { padding-left: 22px; margin: 7px 0; }.rule-content li { margin-bottom: 5px; }.rule-source { font-size: 11px; color: var(--text-soft); }.rule-source a { color: var(--text); text-decoration: underline; }.blokus :focus-visible { outline: 2px solid var(--text); outline-offset: 3px; }
@media (max-width: 900px) { .workbench { grid-template-columns: minmax(0, 1fr); gap: 14px; }.inventory .piece-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }.inventory { padding: 16px; }.blokus { gap: 14px; }.keyboard-note { display: none; } }
@media (max-width: 520px) { .player-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }.player-card { padding: 10px; gap: 4px; }.player-metric b { font-size: 21px; }.player-title strong { font-size: 12px; }.corner-label, .player-metric small, .player-status { font-size: 10px; }.board-panel, .inventory { padding: 10px; border-radius: 12px; }.turn-strip { padding: 11px; }.turn-strip > small { display: none; }.turn-strip strong { font-size: 12px; }.turn-strip span { font-size: 10px; }.inventory .piece-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }.transform-controls { gap: 5px; }.transform-controls > * { padding-inline: 6px; font-size: 12px; min-width: 0; min-height: 44px; }.result-panel { padding: 14px; }.rank-points { font-size: 22px; }.ranking-row { gap: 8px; }.eyebrow { font-size: 9px; }.game-heading h2 { font-size: 25px; }.selection-line { justify-content: center; }.scoring-note > small { font-size: 9px; } }
@media (prefers-reduced-motion: reduce) { .blokus * { scroll-behavior: auto; } }
</style>
