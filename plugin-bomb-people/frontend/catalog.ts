// Keep artwork out of the component module graph. The host loads community views
// asynchronously, so importing every image as a module makes the first mount wait
// for dozens of transforms and can reject before the view is available. Literal
// URLs are still fingerprinted by Vite builds, while the browser loads the images
// independently after the view has mounted.
const magmaArt = new URL('./assets/maps/01-magma-crucible.webp', import.meta.url).href
const frostArt = new URL('./assets/maps/02-frost-fracture.webp', import.meta.url).href
const neonArt = new URL('./assets/maps/03-neon-reactor.webp', import.meta.url).href
const jungleArt = new URL('./assets/maps/04-jungle-ziggurat.webp', import.meta.url).href
const skyArt = new URL('./assets/maps/05-sky-citadel.webp', import.meta.url).href
const clockworkArt = new URL('./assets/maps/06-clockwork-foundry.webp', import.meta.url).href
const hauntedArt = new URL('./assets/maps/07-haunted-catacombs.webp', import.meta.url).href
const stormArt = new URL('./assets/maps/08-storm-dockyard.webp', import.meta.url).href
const crystalArt = new URL('./assets/maps/09-crystal-rift.webp', import.meta.url).href
const solarArt = new URL('./assets/maps/10-solar-collapse.webp', import.meta.url).href

const redPlayer = new URL('./assets/players/player-01-red.png', import.meta.url).href
const bluePlayer = new URL('./assets/players/player-02-blue.png', import.meta.url).href
const yellowPlayer = new URL('./assets/players/player-03-yellow.png', import.meta.url).href
const greenPlayer = new URL('./assets/players/player-04-green.png', import.meta.url).href
const orangePlayer = new URL('./assets/players/player-05-orange.png', import.meta.url).href
const cyanPlayer = new URL('./assets/players/player-06-cyan.png', import.meta.url).href
const violetPlayer = new URL('./assets/players/player-07-violet.png', import.meta.url).href
const blackGoldPlayer = new URL('./assets/players/player-08-black-gold.png', import.meta.url).href

const bombUp = new URL('./assets/items/item-bomb_up.png', import.meta.url).href
const flameUp = new URL('./assets/items/item-flame_up.png', import.meta.url).href
const speed = new URL('./assets/items/item-speed.png', import.meta.url).href
const kick = new URL('./assets/items/item-kick.png', import.meta.url).href
const punch = new URL('./assets/items/item-punch.png', import.meta.url).href
const throwItem = new URL('./assets/items/item-throw.png', import.meta.url).href
const timer = new URL('./assets/items/item-timer.png', import.meta.url).href
const chain = new URL('./assets/items/item-chain.png', import.meta.url).href
const shield = new URL('./assets/items/item-shield.png', import.meta.url).href
const skull = new URL('./assets/items/item-skull.png', import.meta.url).href
const ghost = new URL('./assets/items/item-ghost.png', import.meta.url).href
const magnet = new URL('./assets/items/item-magnet.png', import.meta.url).href
const ice = new URL('./assets/items/item-ice.png', import.meta.url).href
const swap = new URL('./assets/items/item-swap.png', import.meta.url).href
const star = new URL('./assets/items/item-star.png', import.meta.url).href


export const MAP_ART: Record<string, string> = {
  magma_crucible: magmaArt,
  frost_fracture: frostArt,
  neon_reactor: neonArt,
  jungle_ziggurat: jungleArt,
  sky_citadel: skyArt,
  clockwork_foundry: clockworkArt,
  haunted_catacombs: hauntedArt,
  storm_dockyard: stormArt,
  crystal_rift: crystalArt,
  solar_collapse: solarArt,
}

export const PLAYER_ART = [
  redPlayer,
  bluePlayer,
  yellowPlayer,
  greenPlayer,
  orangePlayer,
  cyanPlayer,
  violetPlayer,
  blackGoldPlayer,
]

export const ITEM_ART: Record<string, string> = {
  bomb_up: bombUp,
  flame_up: flameUp,
  speed,
  kick,
  punch,
  throw: throwItem,
  timer,
  chain,
  shield,
  skull,
  ghost,
  magnet,
  ice,
  swap,
  star,
}
