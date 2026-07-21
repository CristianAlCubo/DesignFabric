import { Info } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverDescription,
  PopoverHeader,
  PopoverTitle,
  PopoverTrigger
} from '@/components/ui/popover'

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
          </span>
          {strategy.description ? (
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  className="strategy-option__info"
                  disabled={disabled}
                  aria-label={`Más información sobre ${strategy.label}`}
                  onClick={(event) => event.stopPropagation()}
                >
                  <Info />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end">
                <PopoverHeader>
                  <PopoverTitle>{strategy.label}</PopoverTitle>
                </PopoverHeader>
                <PopoverDescription>{strategy.description}</PopoverDescription>
              </PopoverContent>
            </Popover>
          ) : null}
        </label>
      ))}
    </fieldset>
  )
}
