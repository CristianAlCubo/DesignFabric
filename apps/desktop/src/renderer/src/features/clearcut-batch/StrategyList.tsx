import type { StrategyInfo } from './store'

interface StrategyListProps {
  strategies: StrategyInfo[]
  selectedId: string | null
  onSelect: (id: string) => void
  disabled?: boolean
  name?: string
  legend?: string
}

export function StrategyList({
  strategies,
  selectedId,
  onSelect,
  disabled = false,
  name = 'strategy',
  legend = 'Estrategia de silueta'
}: StrategyListProps) {
  if (strategies.length === 0) return null

  return (
    <fieldset className="strategy-list" disabled={disabled}>
      <legend className="sr-only">{legend}</legend>
      {strategies.map((strategy) => (
        <label key={strategy.id} className="strategy-option">
          <input
            type="radio"
            name={name}
            value={strategy.id}
            checked={selectedId === strategy.id}
            onChange={() => onSelect(strategy.id)}
          />
          <span className="strategy-option__body">
            <span className="strategy-option__label">{strategy.label}</span>
            <span className="strategy-option__description">{strategy.description}</span>
          </span>
        </label>
      ))}
    </fieldset>
  )
}
