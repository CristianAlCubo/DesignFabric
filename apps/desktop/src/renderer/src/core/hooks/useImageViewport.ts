/**
 * Hook genérico de zoom/pan para visores de imagen. No depende de IPC ni de
 * ninguna feature en particular — movido tal cual desde ClearCut original
 * (Fase 6, parte A) a `core/hooks` porque es reutilizable por cualquier
 * feature que necesite mostrar una imagen con controles de zoom.
 */
import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'

const MIN_SCALE = 0.05
const MAX_SCALE = 32
const ZOOM_BUTTON_FACTOR = 1.25
const ZOOM_WHEEL_FACTOR = 1.12

export interface ImageViewport {
  scale: number
  x: number
  y: number
}

function clampScale(scale: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, scale))
}

function fitViewport(
  containerWidth: number,
  containerHeight: number,
  imageWidth: number,
  imageHeight: number
): ImageViewport {
  if (containerWidth <= 0 || containerHeight <= 0 || imageWidth <= 0 || imageHeight <= 0) {
    return { scale: 1, x: 0, y: 0 }
  }

  const scale = Math.min(containerWidth / imageWidth, containerHeight / imageHeight)
  return {
    scale,
    x: (containerWidth - imageWidth * scale) / 2,
    y: (containerHeight - imageHeight * scale) / 2
  }
}

function zoomAtPoint(
  viewport: ImageViewport,
  nextScale: number,
  originX: number,
  originY: number
): ImageViewport {
  const scale = clampScale(nextScale)
  const ratio = scale / viewport.scale
  return {
    scale,
    x: originX - (originX - viewport.x) * ratio,
    y: originY - (originY - viewport.y) * ratio
  }
}

export function useImageViewport(
  enabled: boolean,
  imageWidth: number | null,
  imageHeight: number | null
) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [viewport, setViewport] = useState<ImageViewport>({ scale: 1, x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const fitScaleRef = useRef(1)
  const userTransformedRef = useRef(false)
  const panRef = useRef<{
    pointerId: number
    startX: number
    startY: number
    originX: number
    originY: number
  } | null>(null)
  const imageSizeRef = useRef({ width: imageWidth, height: imageHeight })
  imageSizeRef.current = { width: imageWidth, height: imageHeight }

  const applyFit = () => {
    const container = containerRef.current
    const { width, height } = imageSizeRef.current
    if (!container || !width || !height) return

    const next = fitViewport(container.clientWidth, container.clientHeight, width, height)
    fitScaleRef.current = next.scale
    userTransformedRef.current = false
    setViewport(next)
  }

  const zoomBy = (factor: number, originX?: number, originY?: number) => {
    const container = containerRef.current
    if (!container) return

    const cx = originX ?? container.clientWidth / 2
    const cy = originY ?? container.clientHeight / 2
    userTransformedRef.current = true
    setViewport((current) => zoomAtPoint(current, current.scale * factor, cx, cy))
  }

  useEffect(() => {
    if (!enabled || !imageWidth || !imageHeight) {
      setViewport({ scale: 1, x: 0, y: 0 })
      fitScaleRef.current = 1
      userTransformedRef.current = false
      return
    }

    applyFit()

    const container = containerRef.current
    if (!container) return

    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      const rect = container.getBoundingClientRect()
      const originX = event.clientX - rect.left
      const originY = event.clientY - rect.top
      const factor = event.deltaY < 0 ? ZOOM_WHEEL_FACTOR : 1 / ZOOM_WHEEL_FACTOR
      zoomBy(factor, originX, originY)
    }

    container.addEventListener('wheel', onWheel, { passive: false })

    const observer =
      typeof ResizeObserver === 'undefined'
        ? null
        : new ResizeObserver(() => {
            if (!userTransformedRef.current) {
              applyFit()
              return
            }

            const { width, height } = imageSizeRef.current
            if (!width || !height) return
            fitScaleRef.current = fitViewport(
              container.clientWidth,
              container.clientHeight,
              width,
              height
            ).scale
          })

    observer?.observe(container)

    return () => {
      container.removeEventListener('wheel', onWheel)
      observer?.disconnect()
    }
  }, [enabled, imageHeight, imageWidth])

  const zoomIn = () => zoomBy(ZOOM_BUTTON_FACTOR)
  const zoomOut = () => zoomBy(1 / ZOOM_BUTTON_FACTOR)
  const resetView = () => applyFit()

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!enabled || event.button !== 0) return

    event.currentTarget.setPointerCapture(event.pointerId)
    panRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: viewport.x,
      originY: viewport.y
    }
    setIsPanning(true)
  }

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const pan = panRef.current
    if (!pan || pan.pointerId !== event.pointerId) return

    userTransformedRef.current = true
    setViewport((current) => ({
      ...current,
      x: pan.originX + (event.clientX - pan.startX),
      y: pan.originY + (event.clientY - pan.startY)
    }))
  }

  const endPan = (event: ReactPointerEvent<HTMLDivElement>) => {
    const pan = panRef.current
    if (!pan || pan.pointerId !== event.pointerId) return

    panRef.current = null
    setIsPanning(false)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId)
    }
  }

  const handleDoubleClick = () => {
    if (!enabled) return
    resetView()
  }

  const zoomPercent =
    fitScaleRef.current > 0 ? Math.round((viewport.scale / fitScaleRef.current) * 100) : 100

  return {
    containerRef,
    viewport,
    isPanning,
    zoomPercent,
    zoomIn,
    zoomOut,
    resetView,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp: endPan,
    handlePointerCancel: endPan,
    handleDoubleClick
  }
}
