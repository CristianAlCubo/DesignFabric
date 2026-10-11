import { useEffect, useMemo, useState, type PointerEvent } from 'react'
import { Check, Loader2, Ruler, Save, Shirt, TriangleAlert } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'

import { AppButton } from '../../core/components/AppButton'
import { ImageInputZone } from '../../core/imaging/ImageInputZone'
import { useNavigationStore } from '../../core/state/navigationStore'
import { useMockupStore } from '../mockups/store'
import type { Point } from './store'
import { useMockupTemplateStore } from './store'

type CornerIndex = 0 | 1 | 2 | 3

export function MockupTemplatePanel() {
  const photoPath = useMockupTemplateStore((state) => state.photoPath)
  const photoPreview = useMockupTemplateStore((state) => state.photoPreview)
  const name = useMockupTemplateStore((state) => state.name)
  const id = useMockupTemplateStore((state) => state.id)
  const baseSize = useMockupTemplateStore((state) => state.baseSize)
  const corners = useMockupTemplateStore((state) => state.corners)
  const maskDataUrl = useMockupTemplateStore((state) => state.maskDataUrl)
  const pxPerCm = useMockupTemplateStore((state) => state.pxPerCm)
  const chestWidthCm = useMockupTemplateStore((state) => state.chestWidthCm)
  const maxPrintWidthCm = useMockupTemplateStore((state) => state.maxPrintWidthCm)
  const maxPrintHeightCm = useMockupTemplateStore((state) => state.maxPrintHeightCm)
  const displacementStrengthPx = useMockupTemplateStore((state) => state.displacementStrengthPx)
  const shadingStrength = useMockupTemplateStore((state) => state.shadingStrength)
  const highlightStrength = useMockupTemplateStore((state) => state.highlightStrength)
  const isPreparing = useMockupTemplateStore((state) => state.isPreparing)
  const isSaving = useMockupTemplateStore((state) => state.isSaving)
  const savedTemplate = useMockupTemplateStore((state) => state.savedTemplate)
  const error = useMockupTemplateStore((state) => state.error)

  const setPhotoSource = useMockupTemplateStore((state) => state.setPhotoSource)
  const setName = useMockupTemplateStore((state) => state.setName)
  const setId = useMockupTemplateStore((state) => state.setId)
  const setCorners = useMockupTemplateStore((state) => state.setCorners)
  const setPxPerCm = useMockupTemplateStore((state) => state.setPxPerCm)
  const setChestWidthCm = useMockupTemplateStore((state) => state.setChestWidthCm)
  const setMaxPrintWidthCm = useMockupTemplateStore((state) => state.setMaxPrintWidthCm)
  const setMaxPrintHeightCm = useMockupTemplateStore((state) => state.setMaxPrintHeightCm)
  const setDisplacementStrengthPx = useMockupTemplateStore(
    (state) => state.setDisplacementStrengthPx
  )
  const setShadingStrength = useMockupTemplateStore((state) => state.setShadingStrength)
  const setHighlightStrength = useMockupTemplateStore((state) => state.setHighlightStrength)
  const prepare = useMockupTemplateStore((state) => state.prepare)
  const save = useMockupTemplateStore((state) => state.save)
  const setError = useMockupTemplateStore((state) => state.setError)

  function openInMockups() {
    if (!savedTemplate) return
    useMockupStore.getState().setPreferredTemplateId(savedTemplate.id)
    useNavigationStore.getState().setActiveTab('mockups')
  }

  const [isMeasuring, setIsMeasuring] = useState(false)
  const [measurePoints, setMeasurePoints] = useState<Point[]>([])
  const [activeCorner, setActiveCorner] = useState<CornerIndex | null>(null)
  const cornerKey = useMemo(() => (corners ? JSON.stringify(corners) : ''), [corners])

  useEffect(() => {
    if (!photoPath) return
    const handle = setTimeout(() => void prepare(corners ?? undefined), corners ? 350 : 0)
    return () => clearTimeout(handle)
  }, [photoPath, cornerKey, prepare])

  function pointAt(event: PointerEvent<SVGSVGElement>): Point | null {
    if (!baseSize) return null
    const bounds = event.currentTarget.getBoundingClientRect()
    return [
      Math.max(0, Math.min(baseSize[0], ((event.clientX - bounds.left) / bounds.width) * baseSize[0])),
      Math.max(0, Math.min(baseSize[1], ((event.clientY - bounds.top) / bounds.height) * baseSize[1]))
    ]
  }

  function handlePointerDown(event: PointerEvent<SVGSVGElement>) {
    if (!corners) return
    const corner = (event.target as SVGElement).dataset.corner
    if (corner !== undefined) {
      event.preventDefault()
      event.stopPropagation()
      setActiveCorner(Number(corner) as CornerIndex)
      event.currentTarget.setPointerCapture(event.pointerId)
      return
    }
    if (isMeasuring) {
      const point = pointAt(event)
      if (!point) return
      const next = [...measurePoints, point]
      setMeasurePoints(next.length > 2 ? [point] : next)
      if (next.length >= 2) {
        const [first, second] = next
        const distance = Math.hypot(second[0] - first[0], second[1] - first[1])
        if (distance > 0 && chestWidthCm > 0) setPxPerCm(distance / chestWidthCm)
        setIsMeasuring(false)
        setMeasurePoints([])
      }
    }
  }

  function handlePointerMove(event: PointerEvent<SVGSVGElement>) {
    if (activeCorner === null || !corners) return
    const point = pointAt(event)
    if (!point) return
    const updated: [Point, Point, Point, Point] = corners.map((corner, index) =>
      index === activeCorner ? point : corner
    ) as [Point, Point, Point, Point]
    setCorners(updated)
  }

  function stopDragging() {
    setActiveCorner(null)
  }

  function moveCornerWithKeyboard(index: CornerIndex, dx: number, dy: number) {
    if (!corners || !baseSize) return
    const updated: [Point, Point, Point, Point] = corners.map((point, pointIndex) =>
      pointIndex === index
        ? [
            Math.max(0, Math.min(baseSize[0], point[0] + dx)),
            Math.max(0, Math.min(baseSize[1], point[1] + dy))
          ]
        : point
    ) as [Point, Point, Point, Point]
    setCorners(updated)
  }

  const cornerLabels = ['Superior izquierda', 'Superior derecha', 'Inferior derecha', 'Inferior izquierda']
  const radius = baseSize ? Math.max(7, baseSize[0] / 110) : 8

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      {error ? (
        <p className="error flex-none" role="alert">
          {error}
        </p>
      ) : null}
      <div className="columns columns--scale min-h-0 flex-1">
        <section className="column panel">
          <h2 className="column__title">Fotografía</h2>
          <ImageInputZone
            path={photoPath}
            previewUrl={photoPreview}
            onSource={setPhotoSource}
            onError={setError}
            disabled={isSaving}
            tabId="mockup-templates"
            selectLabel="Seleccionar foto"
            selectIcon={Shirt}
            alt="Foto base de la prenda"
            emptyLabel="Carga una foto frontal de prenda para crear su plantilla"
          />
          {baseSize ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Imagen original · {baseSize[0]} × {baseSize[1]} px
            </p>
          ) : null}
        </section>

        <section className="column panel">
          <h2 className="column__title">
            Área de impresión
            {isPreparing ? (
              <Loader2 className="ml-2 inline size-4 animate-spin align-[-2px]" />
            ) : null}
          </h2>
          {photoPreview && baseSize ? (
            <div className="flex min-h-0 flex-1 flex-col gap-2">
              <p className="text-xs text-muted-foreground">
                Arrastra los cuatro puntos para ajustar el área. La máscara propuesta se muestra sobre la foto.
              </p>
              <div
                className="relative min-h-64 w-full overflow-hidden rounded-md bg-muted"
                style={{ aspectRatio: `${baseSize[0]} / ${baseSize[1]}` }}
              >
                <img
                  src={photoPreview}
                  alt="Prenda con el área de impresión"
                  className="absolute inset-0 size-full object-fill"
                  draggable={false}
                />
                <svg
                  viewBox={`0 0 ${baseSize[0]} ${baseSize[1]}`}
                  preserveAspectRatio="none"
                  className={`absolute inset-0 size-full touch-none ${isMeasuring ? 'cursor-crosshair' : ''}`}
                  aria-label="Ajustar el área de impresión sobre la prenda"
                  onPointerDown={handlePointerDown}
                  onPointerMove={handlePointerMove}
                  onPointerUp={stopDragging}
                  onPointerCancel={stopDragging}
                >
                  {maskDataUrl ? (
                    <image
                      href={maskDataUrl}
                      x="0"
                      y="0"
                      width={baseSize[0]}
                      height={baseSize[1]}
                      opacity="0.28"
                      style={{ mixBlendMode: 'multiply', pointerEvents: 'none' }}
                    />
                  ) : null}
                  {corners ? (
                    <>
                      <polygon
                        points={corners.map((point) => point.join(',')).join(' ')}
                        fill="rgba(250, 204, 21, 0.08)"
                        stroke="#facc15"
                        strokeWidth={Math.max(2, baseSize[0] / 350)}
                        vectorEffect="non-scaling-stroke"
                      />
                      {corners.map(([x, y], index) => (
                        <circle
                          key={cornerLabels[index]}
                          data-corner={index}
                          cx={x}
                          cy={y}
                          r={radius}
                          fill="#facc15"
                          stroke="#18181b"
                          strokeWidth={2}
                          tabIndex={0}
                          role="slider"
                          aria-label={cornerLabels[index]}
                          aria-valuetext={`${Math.round(x)}, ${Math.round(y)} px`}
                          className="cursor-move outline-none focus:fill-amber-300"
                          onKeyDown={(event) => {
                            const step = Math.max(1, Math.round(baseSize[0] / 300))
                            if (event.key === 'ArrowLeft') moveCornerWithKeyboard(index as CornerIndex, -step, 0)
                            if (event.key === 'ArrowRight') moveCornerWithKeyboard(index as CornerIndex, step, 0)
                            if (event.key === 'ArrowUp') moveCornerWithKeyboard(index as CornerIndex, 0, -step)
                            if (event.key === 'ArrowDown') moveCornerWithKeyboard(index as CornerIndex, 0, step)
                          }}
                        />
                      ))}
                    </>
                  ) : null}
                  {measurePoints.map(([x, y], index) => (
                    <circle
                      key={`medida-${index}`}
                      cx={x}
                      cy={y}
                      r={radius * 0.72}
                      fill="#38bdf8"
                      stroke="white"
                      strokeWidth={2}
                      pointerEvents="none"
                    />
                  ))}
                </svg>
              </div>
              {isMeasuring ? (
                <p className="text-xs text-sky-500" role="status">
                  Marca dos puntos a lo ancho del pecho ({measurePoints.length}/2).
                </p>
              ) : null}
            </div>
          ) : (
            <div className="flex min-h-0 flex-1 items-center justify-center rounded-md bg-muted/50 p-6 text-center text-sm text-muted-foreground">
              La máscara y el área editable aparecerán al cargar la foto.
            </div>
          )}
        </section>

        <section className="column panel panel--form overflow-y-auto">
          <h2 className="column__title">Calibración y render</h2>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="mockup-template-name">Nombre</FieldLabel>
                <Input id="mockup-template-name" value={name} onChange={(event) => setName(event.target.value)} />
              </Field>
              <Field>
                <FieldLabel htmlFor="mockup-template-id">ID</FieldLabel>
                <Input id="mockup-template-id" value={id} onChange={(event) => setId(event.target.value)} />
              </Field>
            </div>
            <Field>
              <FieldLabel htmlFor="mockup-template-px-cm">Escala real (px/cm)</FieldLabel>
              <Input
                id="mockup-template-px-cm"
                type="number"
                min="0.1"
                step="0.1"
                value={pxPerCm}
                onChange={(event) => setPxPerCm(Number(event.target.value))}
              />
              <FieldDescription>
                Si conoces una medida real, introduce la escala o mídela en la foto.
              </FieldDescription>
            </Field>
            <div className="grid grid-cols-[1fr_auto] items-end gap-2">
              <Field>
                <FieldLabel htmlFor="mockup-chest-width">Ancho real a medir (cm)</FieldLabel>
                <Input
                  id="mockup-chest-width"
                  type="number"
                  min="1"
                  step="0.5"
                  value={chestWidthCm}
                  onChange={(event) => setChestWidthCm(Number(event.target.value))}
                />
              </Field>
              <AppButton
                type="button"
                variant={isMeasuring ? 'default' : 'outline'}
                icon={Ruler}
                disabled={!corners || !baseSize}
                onClick={() => {
                  setMeasurePoints([])
                  setIsMeasuring((value) => !value)
                }}
              >
                {isMeasuring ? 'Cancelar' : 'Medir'}
              </AppButton>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field>
                <FieldLabel htmlFor="mockup-max-width">Impresión máx. ancho (cm)</FieldLabel>
                <Input
                  id="mockup-max-width"
                  type="number"
                  min="1"
                  step="0.5"
                  value={maxPrintWidthCm}
                  onChange={(event) => setMaxPrintWidthCm(Number(event.target.value))}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="mockup-max-height">Alto (cm)</FieldLabel>
                <Input
                  id="mockup-max-height"
                  type="number"
                  min="1"
                  step="0.5"
                  value={maxPrintHeightCm}
                  onChange={(event) => setMaxPrintHeightCm(Number(event.target.value))}
                />
              </Field>
            </div>
            <Field>
              <div className="flex justify-between gap-2">
                <FieldLabel>Deformación de la tela</FieldLabel>
                <span className="text-xs tabular-nums text-muted-foreground">{displacementStrengthPx.toFixed(1)} px</span>
              </div>
              <Slider
                min={0}
                max={20}
                step={0.5}
                value={[displacementStrengthPx]}
                onValueChange={(value) => setDisplacementStrengthPx(value[0] ?? displacementStrengthPx)}
              />
            </Field>
            <Field>
              <div className="flex justify-between gap-2">
                <FieldLabel>Sombreado</FieldLabel>
                <span className="text-xs tabular-nums text-muted-foreground">{Math.round(shadingStrength * 100)} %</span>
              </div>
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={[shadingStrength]}
                onValueChange={(value) => setShadingStrength(value[0] ?? shadingStrength)}
              />
            </Field>
            <Field>
              <div className="flex justify-between gap-2">
                <FieldLabel>Luces de la tela</FieldLabel>
                <span className="text-xs tabular-nums text-muted-foreground">{Math.round(highlightStrength * 100)} %</span>
              </div>
              <Slider
                min={0}
                max={1}
                step={0.01}
                value={[highlightStrength]}
                onValueChange={(value) => setHighlightStrength(value[0] ?? highlightStrength)}
              />
            </Field>

            {savedTemplate ? (
              <Alert>
                <Check />
                <AlertTitle>Plantilla guardada</AlertTitle>
                <AlertDescription className="flex flex-col items-start gap-2">
                  <span>{savedTemplate.name} · {savedTemplate.id}</span>
                  <span>Los ajustes de tela se aplican en el render de Mockups.</span>
                  <AppButton type="button" variant="outline" icon={Shirt} onClick={openInMockups}>
                    Probar en Mockups
                  </AppButton>
                </AlertDescription>
              </Alert>
            ) : null}
            {error ? (
              <Alert variant="destructive">
                <TriangleAlert />
                <AlertTitle>No se pudo guardar</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
            <AppButton
              type="button"
              icon={isSaving ? Loader2 : Save}
              iconClassName={isSaving ? 'animate-spin' : undefined}
              onClick={() => void save()}
              disabled={!photoPath || !corners || isPreparing || isSaving}
              className="self-end"
            >
              {isSaving ? 'Guardando…' : 'Guardar plantilla'}
            </AppButton>
          </div>
        </section>
      </div>
    </div>
  )
}
