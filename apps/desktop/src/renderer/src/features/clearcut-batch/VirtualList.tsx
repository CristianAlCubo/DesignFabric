import { useEffect, useRef, useState, type ReactNode, type UIEvent } from 'react'

import { cn } from '@/lib/utils'

interface VirtualListProps<T> {
  items: T[]
  rowHeight: number
  overscan?: number
  className?: string
  getKey: (item: T, index: number) => string
  renderRow: (item: T, index: number) => ReactNode
}

/** Lista virtualizada simple (altura fija) para colas de cientos de ítems. */
export function VirtualList<T>({
  items,
  rowHeight,
  overscan = 8,
  className,
  getKey,
  renderRow
}: VirtualListProps<T>) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportHeight, setViewportHeight] = useState(320)

  useEffect(() => {
    const node = containerRef.current
    if (!node) return

    const update = (): void => setViewportHeight(node.clientHeight)
    update()

    const observer = new ResizeObserver(update)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const totalHeight = items.length * rowHeight
  const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan)
  const visibleCount = Math.ceil(viewportHeight / rowHeight) + overscan * 2
  const endIndex = Math.min(items.length, startIndex + visibleCount)
  const offsetY = startIndex * rowHeight

  function handleScroll(event: UIEvent<HTMLDivElement>): void {
    setScrollTop(event.currentTarget.scrollTop)
  }

  return (
    <div
      ref={containerRef}
      className={cn('min-h-0 flex-1 overflow-auto', className)}
      onScroll={handleScroll}
    >
      <div className="relative w-full" style={{ height: totalHeight }}>
        <div className="absolute inset-x-0 top-0" style={{ transform: `translateY(${offsetY}px)` }}>
          {items.slice(startIndex, endIndex).map((item, offset) => {
            const index = startIndex + offset
            return (
              <div key={getKey(item, index)} style={{ height: rowHeight }}>
                {renderRow(item, index)}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
