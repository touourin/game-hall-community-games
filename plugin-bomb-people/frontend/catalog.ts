import magmaArt from './assets/maps/01-magma-crucible.webp'
import frostArt from './assets/maps/02-frost-fracture.webp'
import neonArt from './assets/maps/03-neon-reactor.webp'
import jungleArt from './assets/maps/04-jungle-ziggurat.webp'
import skyArt from './assets/maps/05-sky-citadel.webp'
import clockworkArt from './assets/maps/06-clockwork-foundry.webp'
import hauntedArt from './assets/maps/07-haunted-catacombs.webp'
import stormArt from './assets/maps/08-storm-dockyard.webp'
import crystalArt from './assets/maps/09-crystal-rift.webp'
import solarArt from './assets/maps/10-solar-collapse.webp'

import redPlayer from './assets/players/player-01-red.png'
import bluePlayer from './assets/players/player-02-blue.png'
import yellowPlayer from './assets/players/player-03-yellow.png'
import greenPlayer from './assets/players/player-04-green.png'
import orangePlayer from './assets/players/player-05-orange.png'
import cyanPlayer from './assets/players/player-06-cyan.png'
import violetPlayer from './assets/players/player-07-violet.png'
import blackGoldPlayer from './assets/players/player-08-black-gold.png'

import bombUp from './assets/items/item-bomb_up.png'
import flameUp from './assets/items/item-flame_up.png'
import speed from './assets/items/item-speed.png'
import kick from './assets/items/item-kick.png'
import punch from './assets/items/item-punch.png'
import throwItem from './assets/items/item-throw.png'
import timer from './assets/items/item-timer.png'
import chain from './assets/items/item-chain.png'
import shield from './assets/items/item-shield.png'
import skull from './assets/items/item-skull.png'
import ghost from './assets/items/item-ghost.png'
import magnet from './assets/items/item-magnet.png'
import ice from './assets/items/item-ice.png'
import swap from './assets/items/item-swap.png'
import star from './assets/items/item-star.png'


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
