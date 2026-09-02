const cards = [
  { color: 'red', kind: 'number', value: '7', label: '赤红 7' },
  { color: 'yellow', kind: 'number', value: '3', label: '琥珀 3' },
  { color: 'green', kind: 'skip', value: '⊘', label: '翠绿 跳过' },
  { color: 'blue', kind: 'reverse', value: '↻', label: '湛蓝 反转' },
  { color: 'red', kind: 'draw-two', value: '+2', label: '赤红 +2' },
  { color: 'wild', kind: 'wild', value: '✦', label: '万能变色' },
  { color: 'wild', kind: 'wild-draw-four', value: '+4', label: '万能 +4' },
  { color: 'back', kind: 'back', value: '', label: '棱镜牌背' },
]

const effects = {
  skip: { symbol: '⊘', title: '时间切断', copy: '下一位玩家被跳过', card: ['red', '⊘'] },
  reverse: { symbol: '↻', title: '轨道反转', copy: '行动方向已经反转', card: ['blue', '↻'] },
  'draw-two': { symbol: '+2', title: '能量汲取 +2', copy: '惩罚链增加 2，目标可继续叠加', card: ['yellow', '+2'], stack: 2, contribution: 2 },
  wild: { symbol: '✦', title: '光谱重构', copy: '下一种颜色已经指定', card: ['wild', '✦'] },
  'wild-draw-four': { symbol: '+4', title: '棱镜奇点 +4', copy: '惩罚链已经累计至 +6', card: ['wild', '+4'], stack: 6, contribution: 4 },
  'take-penalty': { symbol: '+6', title: '累计惩罚坠落', copy: '目标摸 6 张并跳过本回合', card: ['yellow', '+6'], contribution: 6 },
  'catch-uno': { symbol: '!', title: '漏喊捕获', copy: '漏喊者立即摸 2 张', card: ['red', '+2'] },
  uno: { symbol: 'UNO!', title: '最后一张宣告', copy: '宣告成功，进入决胜时刻', card: ['blue', '1'] },
}

const gallery = document.querySelector('#cardGallery')
const overlay = document.querySelector('#effectOverlay')
const stage = document.querySelector('#arenaStage')
const topCard = document.querySelector('#topCard')
const penaltyReactor = document.querySelector('#penaltyReactor')

function cardMarkup(card) {
  if (card.kind === 'back') {
    return `<article class="card-sample"><div class="demo-card back" role="img" aria-label="${card.label}"><div class="card-inner"></div></div><span>${card.label}</span></article>`
  }
  const wildShards = card.color === 'wild'
    ? '<i class="shard red"></i><i class="shard yellow"></i><i class="shard green"></i><i class="shard blue"></i>'
    : ''
  return `<article class="card-sample">
    <div class="demo-card ${card.color} ${card.kind}" role="img" aria-label="${card.label}">
      <div class="card-inner"><span class="corner">${card.value}</span><strong>${wildShards}${card.value}</strong><span class="corner bottom">${card.value}</span></div>
    </div>
    <span>${card.label}</span>
  </article>`
}

gallery.innerHTML = cards.map(cardMarkup).join('')

function playEffect(name) {
  const effect = effects[name]
  if (!effect) return
  overlay.className = 'effect-overlay'
  stage.classList.remove('impact', 'has-penalty')
  void overlay.offsetWidth

  overlay.querySelector('.effect-symbol').textContent = effect.symbol
  overlay.querySelector('.effect-copy b').textContent = effect.title
  overlay.querySelector('.effect-copy span').textContent = effect.copy
  const stackBadge = overlay.querySelector('.effect-stack')
  stackBadge.textContent = effect.stack > effect.contribution ? `累计 +${effect.stack}` : ''
  overlay.classList.add('active', `effect-${name}`)
  topCard.className = `demo-card ${effect.card[0]}`
  topCard.querySelector('strong').textContent = effect.card[1]
  topCard.querySelectorAll('.corner').forEach((corner) => { corner.textContent = effect.card[1] })
  if (effect.stack) {
    stage.classList.add('has-penalty')
    penaltyReactor.querySelector('strong').textContent = `+${effect.stack}`
  }
  if (name === 'wild-draw-four' || name === 'take-penalty') stage.classList.add('impact')
}

document.querySelectorAll('[data-effect]').forEach((button) => {
  button.addEventListener('click', () => playEffect(button.dataset.effect))
})

setTimeout(() => playEffect('reverse'), 450)
