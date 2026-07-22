<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Object3D } from 'three'
import type { ThemeMode } from '../../composables/useTheme'

interface DataFlowSceneProps {
  variant: 'login' | 'dashboard'
  theme: ThemeMode
  quality: 'auto' | 'high' | 'low'
  reducedMotion?: boolean
}

const props = withDefaults(defineProps<DataFlowSceneProps>(), {
  quality: 'auto',
  reducedMotion: false,
})
const emit = defineEmits<{ ready: []; fallback: [] }>()

const host = ref<HTMLElement>()
const canvas = ref<HTMLCanvasElement>()
const ready = ref(false)
const fallback = ref(false)

let dispose: (() => void) | undefined
let updateTheme: ((theme: ThemeMode) => void) | undefined
let destroyed = false

function actualTheme(): ThemeMode {
  return document.documentElement.dataset.theme === 'light' ? 'light' : props.theme
}

async function initialize() {
  if (!host.value || !canvas.value) return
  if (window.matchMedia('(max-width: 768px)').matches) {
    fallback.value = true
    emit('fallback')
    return
  }

  try {
    const THREE = await import('three')
    if (destroyed || !host.value || !canvas.value) return
    const container = host.value
    const surface = canvas.value
    const reducedMotion = props.reducedMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const quality = props.quality === 'auto'
      ? ((window.devicePixelRatio || 1) > 1.5 ? 'high' : 'low')
      : props.quality
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(props.variant === 'login' ? 54 : 45, 1, .1, 100)
    camera.position.set(0, 0, props.variant === 'login' ? 11 : 13)

    const renderer = new THREE.WebGLRenderer({
      canvas: surface,
      alpha: true,
      antialias: quality !== 'low',
      powerPreference: 'high-performance',
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality === 'high' ? 1.75 : 1.4))
    renderer.outputColorSpace = THREE.SRGBColorSpace

    const root = new THREE.Group()
    root.rotation.x = props.variant === 'login' ? -.06 : -.16
    scene.add(root)

    const frameMaterial = new THREE.LineBasicMaterial({ transparent: true, opacity: .19 })
    const laneMaterial = new THREE.LineBasicMaterial({ transparent: true, opacity: .25 })
    const messageMaterial = new THREE.MeshBasicMaterial({ transparent: true, opacity: .92 })
    const deliveredMaterial = new THREE.MeshBasicMaterial({ transparent: true, opacity: .8 })
    const particleMaterial = new THREE.PointsMaterial({ size: props.variant === 'login' ? .045 : .035, transparent: true, opacity: .55, sizeAttenuation: true })

    const frameGeometry = new THREE.EdgesGeometry(new THREE.BoxGeometry(10, 6, .04))
    const frames: InstanceType<typeof THREE.LineSegments>[] = []
    const frameCount = props.variant === 'login' ? 14 : 9
    for (let index = 0; index < frameCount; index += 1) {
      const frame = new THREE.LineSegments(frameGeometry, frameMaterial)
      frame.position.z = 5 - index * 2.7
      frame.scale.setScalar(1 + index * .026)
      root.add(frame)
      frames.push(frame)
    }

    const lanes = [-2.4, -1.2, 0, 1.2, 2.4]
    lanes.forEach((x) => {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x, -1.7 + Math.abs(x) * .08, 5),
        new THREE.Vector3(x * .46, 0, -34),
      ])
      root.add(new THREE.Line(geometry, laneMaterial))
    })

    const particleCount = props.variant === 'login'
      ? (quality === 'low' ? 420 : 860)
      : (quality === 'high' ? 520 : 320)
    const positions = new Float32Array(particleCount * 3)
    for (let index = 0; index < particleCount; index += 1) {
      positions[index * 3] = (Math.random() - .5) * 12
      positions[index * 3 + 1] = (Math.random() - .5) * 7
      positions[index * 3 + 2] = 6 - Math.random() * 42
    }
    const particleGeometry = new THREE.BufferGeometry()
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particles = new THREE.Points(particleGeometry, particleMaterial)
    root.add(particles)

    const messageGeometry = new THREE.BoxGeometry(.13, .13, .38)
    const messages: Array<{ mesh: InstanceType<typeof THREE.Mesh>; speed: number; lane: number }> = []
    const messageCount = props.variant === 'login' ? 22 : 10
    for (let index = 0; index < messageCount; index += 1) {
      const mesh = new THREE.Mesh(messageGeometry, index % 6 === 0 ? deliveredMaterial : messageMaterial)
      const lane = lanes[index % lanes.length]
      mesh.position.set(lane * .46, (index % 3 - 1) * .34, -32 + (index / messageCount) * 38)
      root.add(mesh)
      messages.push({ mesh, speed: .032 + (index % 4) * .006, lane })
    }

    const nodeGeometry = new THREE.TorusGeometry(1.05, .035, 8, 72)
    const nodeMaterial = new THREE.MeshBasicMaterial({ transparent: true, opacity: .52 })
    const nodes = [-24, -12, 1.8].map((z, index) => {
      const node = new THREE.Mesh(nodeGeometry, nodeMaterial)
      node.position.set(0, 0, z)
      node.scale.setScalar(index === 1 ? 1.35 : .9)
      root.add(node)
      return node
    })

    updateTheme = (theme: ThemeMode) => {
      const light = theme === 'light'
      const accent = new THREE.Color(light ? '#047ead' : '#12a8e8')
      frameMaterial.color.copy(new THREE.Color(light ? '#2a5c74' : '#4e7994'))
      laneMaterial.color.copy(accent)
      messageMaterial.color.copy(accent)
      deliveredMaterial.color.copy(new THREE.Color(light ? '#067c61' : '#16c79a'))
      particleMaterial.color.copy(new THREE.Color(light ? '#47758c' : '#d7eff8'))
      nodeMaterial.color.copy(accent)
      scene.fog = new THREE.FogExp2(light ? '#edf5f8' : '#07111e', light ? .025 : .031)
    }
    updateTheme(actualTheme())

    const pointer = { x: 0, y: 0 }
    const onPointer = (event: PointerEvent) => {
      const bounds = container.getBoundingClientRect()
      pointer.x = ((event.clientX - bounds.left) / bounds.width - .5) * 2
      pointer.y = ((event.clientY - bounds.top) / bounds.height - .5) * 2
    }
    container.addEventListener('pointermove', onPointer, { passive: true })

    const resize = () => {
      const width = Math.max(1, container.clientWidth)
      const height = Math.max(1, container.clientHeight)
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(container)
    resize()

    let paused = document.hidden
    const onVisibility = () => { paused = document.hidden }
    document.addEventListener('visibilitychange', onVisibility)
    const rootObserver = new MutationObserver(() => updateTheme?.(actualTheme()))
    rootObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })

    const clock = new THREE.Clock()
    let frameId = 0
    const render = () => {
      frameId = window.requestAnimationFrame(render)
      if (paused) return
      const elapsed = clock.getElapsedTime()
      if (!reducedMotion) {
        messages.forEach((message) => {
          message.mesh.position.z += message.speed * 2.3
          const perspective = (message.mesh.position.z + 34) / 39
          message.mesh.position.x = message.lane * (.46 + perspective * .54)
          if (message.mesh.position.z > 6) message.mesh.position.z = -33
        })
        frames.forEach((frame, index) => { frame.position.z += .008 + index * .0004; if (frame.position.z > 6) frame.position.z -= frameCount * 2.7 })
        nodes.forEach((node, index) => { node.rotation.z = elapsed * (.07 + index * .025) })
        particles.rotation.z = elapsed * .008
        camera.position.x += (pointer.x * .34 - camera.position.x) * .035
        camera.position.y += (-pointer.y * .22 - camera.position.y) * .035
      }
      camera.lookAt(0, 0, -12)
      renderer.render(scene, camera)
    }
    render()
    ready.value = true
    emit('ready')

    dispose = () => {
      window.cancelAnimationFrame(frameId)
      resizeObserver.disconnect()
      rootObserver.disconnect()
      document.removeEventListener('visibilitychange', onVisibility)
      container.removeEventListener('pointermove', onPointer)
      const geometries = new Set<{ dispose: () => void }>()
      root.traverse((object: Object3D) => {
        if ('geometry' in object && object.geometry && typeof object.geometry === 'object') {
          geometries.add(object.geometry as { dispose: () => void })
        }
      })
      geometries.forEach((geometry) => geometry.dispose())
      ;[frameMaterial, laneMaterial, messageMaterial, deliveredMaterial, particleMaterial, nodeMaterial].forEach((material) => material.dispose())
      renderer.dispose()
      renderer.forceContextLoss()
    }
  } catch {
    fallback.value = true
    emit('fallback')
  }
}

watch(() => props.theme, (value) => updateTheme?.(value))
onMounted(initialize)
onBeforeUnmount(() => {
  destroyed = true
  dispose?.()
})
</script>

<template>
  <div ref="host" :class="['data-flow-scene', `data-flow-scene--${variant}`, { 'is-ready': ready, 'is-fallback': fallback }]" aria-hidden="true">
    <canvas ref="canvas" class="data-flow-canvas" />
    <div class="data-flow-poster" />
    <div class="data-flow-vignette" />
  </div>
</template>

<style scoped>
.data-flow-scene { position: absolute; inset: 0; overflow: hidden; pointer-events: auto; }
.data-flow-canvas { width: 100%; height: 100%; display: block; opacity: 0; transition: opacity .8s cubic-bezier(.23, 1, .32, 1); }
.data-flow-scene.is-ready .data-flow-canvas { opacity: 1; }
.data-flow-poster { position: absolute; inset: 0; background-position: center; background-size: cover; opacity: 0; transition: opacity .25s ease; }
.data-flow-scene.is-fallback .data-flow-poster { opacity: 1; }
.data-flow-vignette { position: absolute; inset: 0; pointer-events: none; background: linear-gradient(90deg, color-mix(in srgb, var(--app-sidebar) 38%, transparent), transparent 48%, color-mix(in srgb, var(--app-sidebar) 18%, transparent)); }
.data-flow-scene--dashboard { pointer-events: none; }
</style>
