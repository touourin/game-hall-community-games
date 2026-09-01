import type { BombEffectKind } from './types'


type AudioContextConstructor = typeof AudioContext

interface WebkitAudioWindow extends Window {
  webkitAudioContext?: AudioContextConstructor
}

export interface BombPeopleSound {
  unlock: () => void
  play: (kind: BombEffectKind) => void
  destroy: () => void
}

export function createBombPeopleSound(): BombPeopleSound {
  let context: AudioContext | null = null
  let master: GainNode | null = null
  let noiseBuffer: AudioBuffer | null = null

  function getContext() {
    if (context || typeof window === 'undefined') return context
    const AudioContextClass = window.AudioContext
      ?? (window as WebkitAudioWindow).webkitAudioContext
    if (!AudioContextClass) return null
    context = new AudioContextClass()
    master = context.createGain()
    master.gain.value = 0.5
    master.connect(context.destination)
    return context
  }

  function unlock() {
    const audio = getContext()
    if (audio?.state === 'suspended') void audio.resume().catch(() => undefined)
  }

  function tone(
    audio: AudioContext,
    start: number,
    frequency: number,
    endFrequency: number,
    duration: number,
    volume: number,
    waveform: OscillatorType = 'sine',
  ) {
    if (!master) return
    const oscillator = audio.createOscillator()
    const gain = audio.createGain()
    oscillator.type = waveform
    oscillator.frequency.setValueAtTime(frequency, start)
    oscillator.frequency.exponentialRampToValueAtTime(Math.max(1, endFrequency), start + duration)
    gain.gain.setValueAtTime(0.0001, start)
    gain.gain.exponentialRampToValueAtTime(volume, start + Math.min(0.012, duration / 4))
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration)
    oscillator.connect(gain).connect(master)
    oscillator.start(start)
    oscillator.stop(start + duration + 0.02)
  }

  function deterministicNoise(audio: AudioContext) {
    if (noiseBuffer) return noiseBuffer
    const length = Math.ceil(audio.sampleRate * 0.48)
    const buffer = audio.createBuffer(1, length, audio.sampleRate)
    const data = buffer.getChannelData(0)
    let seed = 0x6d2b79f5
    for (let index = 0; index < length; index += 1) {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0
      data[index] = (seed / 0xffffffff) * 2 - 1
    }
    noiseBuffer = buffer
    return buffer
  }

  function noise(
    audio: AudioContext,
    start: number,
    duration: number,
    volume: number,
    frequency: number,
    filterType: BiquadFilterType,
  ) {
    if (!master) return
    const source = audio.createBufferSource()
    const filter = audio.createBiquadFilter()
    const gain = audio.createGain()
    source.buffer = deterministicNoise(audio)
    filter.type = filterType
    filter.frequency.setValueAtTime(frequency, start)
    gain.gain.setValueAtTime(volume, start)
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration)
    source.connect(filter).connect(gain).connect(master)
    source.start(start)
    source.stop(start + duration)
  }

  function play(kind: BombEffectKind) {
    const audio = context
    if (!audio || audio.state === 'closed') return
    if (audio.state === 'suspended') void audio.resume().catch(() => undefined)
    const now = audio.currentTime + 0.008
    if (kind === 'bomb_placed') {
      tone(audio, now, 155, 82, 0.13, 0.17, 'triangle')
      tone(audio, now + 0.015, 420, 250, 0.055, 0.06, 'square')
    } else if (kind === 'bomb_exploded') {
      noise(audio, now, 0.42, 0.28, 760, 'lowpass')
      tone(audio, now, 92, 34, 0.44, 0.28, 'sine')
      tone(audio, now + 0.025, 188, 48, 0.26, 0.12, 'sawtooth')
    } else if (kind === 'bomb_kicked') {
      noise(audio, now, 0.08, 0.1, 1_500, 'lowpass')
      tone(audio, now, 176, 78, 0.12, 0.2, 'square')
    } else if (kind === 'bomb_punched') {
      noise(audio, now, 0.1, 0.14, 2_200, 'bandpass')
      tone(audio, now, 285, 92, 0.13, 0.22, 'triangle')
    } else if (kind === 'bomb_thrown') {
      noise(audio, now, 0.22, 0.08, 1_850, 'bandpass')
      tone(audio, now, 460, 155, 0.25, 0.12, 'sine')
    }
  }

  function destroy() {
    const audio = context
    context = null
    master = null
    noiseBuffer = null
    if (audio && audio.state !== 'closed') void audio.close().catch(() => undefined)
  }

  return { unlock, play, destroy }
}
