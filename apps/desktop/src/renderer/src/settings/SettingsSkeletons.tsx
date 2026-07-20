import { Skeleton } from '@/components/ui/skeleton'

/** Placeholder de carga para el panel OpenRouter en Settings (evita flash de estados vacíos). */
export function OpenRouterSettingsSkeleton() {
  return (
    <div className="flex max-w-xl flex-col gap-4" aria-busy="true" aria-label="Cargando configuración">
      <Skeleton className="h-16 w-full rounded-lg" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-10 w-full rounded-lg" />
      <div className="space-y-2 rounded-lg border border-border p-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    </div>
  )
}

/** Filas de skeleton para la lista de modelos. */
export function ModelListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <ul className="max-h-64 overflow-hidden rounded-lg border border-border" aria-busy="true">
      {Array.from({ length: rows }, (_, index) => (
        <li key={index} className="border-b border-border px-3 py-2 last:border-b-0">
          <Skeleton className="mb-1.5 h-4 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
        </li>
      ))}
    </ul>
  )
}

/** Tarjeta skeleton cuando hay modelo seleccionado pero aún hidratamos prefs. */
export function SelectedModelSkeleton() {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border border-border px-3 py-3">
      <div className="min-w-0 flex-1 space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-64" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-7 w-20" />
        <Skeleton className="h-7 w-16" />
      </div>
    </div>
  )
}
