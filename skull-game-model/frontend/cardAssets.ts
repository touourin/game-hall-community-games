import type { DiscKind, ThemeSlug } from './types'

export interface PlayerCardAssets {
  back: string
  flower: string
  skull: string
}

export const CARD_ASSETS: Record<ThemeSlug, PlayerCardAssets> = {
  ember: {
    back: new URL('../assets/player-cards/generated/seat-1-ember-back.svg', import.meta.url).href,
    flower: new URL('../assets/player-cards/generated/seat-1-ember-flower.svg', import.meta.url).href,
    skull: new URL('../assets/player-cards/generated/seat-1-ember-skull.svg', import.meta.url).href,
  },
  tide: {
    back: new URL('../assets/player-cards/generated/seat-2-tide-back.svg', import.meta.url).href,
    flower: new URL('../assets/player-cards/generated/seat-2-tide-flower.svg', import.meta.url).href,
    skull: new URL('../assets/player-cards/generated/seat-2-tide-skull.svg', import.meta.url).href,
  },
  moss: {
    back: new URL('../assets/player-cards/generated/seat-3-moss-back.svg', import.meta.url).href,
    flower: new URL('../assets/player-cards/generated/seat-3-moss-flower.svg', import.meta.url).href,
    skull: new URL('../assets/player-cards/generated/seat-3-moss-skull.svg', import.meta.url).href,
  },
  orchid: {
    back: new URL('../assets/player-cards/generated/seat-4-orchid-back.svg', import.meta.url).href,
    flower: new URL('../assets/player-cards/generated/seat-4-orchid-flower.svg', import.meta.url).href,
    skull: new URL('../assets/player-cards/generated/seat-4-orchid-skull.svg', import.meta.url).href,
  },
  ochre: {
    back: new URL('../assets/player-cards/generated/seat-5-ochre-back.svg', import.meta.url).href,
    flower: new URL('../assets/player-cards/generated/seat-5-ochre-flower.svg', import.meta.url).href,
    skull: new URL('../assets/player-cards/generated/seat-5-ochre-skull.svg', import.meta.url).href,
  },
  slate: {
    back: new URL('../assets/player-cards/generated/seat-6-slate-back.svg', import.meta.url).href,
    flower: new URL('../assets/player-cards/generated/seat-6-slate-flower.svg', import.meta.url).href,
    skull: new URL('../assets/player-cards/generated/seat-6-slate-skull.svg', import.meta.url).href,
  },
}

export function cardAsset(theme: ThemeSlug, kind: DiscKind, faceUp: boolean): string {
  if (!faceUp || kind === 'unknown' || kind === 'last_chance_flower') {
    return CARD_ASSETS[theme].back
  }
  return kind === 'skull' ? CARD_ASSETS[theme].skull : CARD_ASSETS[theme].flower
}

export function privateCardAsset(theme: ThemeSlug, kind: DiscKind): string {
  if (kind === 'skull') return CARD_ASSETS[theme].skull
  if (kind === 'flower') return CARD_ASSETS[theme].flower
  return CARD_ASSETS[theme].back
}

export function discLabel(kind: DiscKind): string {
  if (kind === 'skull') return '骷髅牌'
  if (kind === 'flower') return '花牌'
  if (kind === 'last_chance_flower') return '最后机会花牌'
  return '未知暗牌'
}
