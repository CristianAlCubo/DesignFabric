import type { ComponentProps, ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type AppButtonProps = ComponentProps<typeof Button> & {
  icon?: LucideIcon
  iconPosition?: 'start' | 'end'
  iconClassName?: string
}

function hasVisibleLabel(children: ReactNode): boolean {
  if (children == null || children === false || children === true) return false
  if (typeof children === 'string') return children.trim().length > 0
  return true
}

/** Button de producto: shadcn Button + icono Lucide opcional. */
export function AppButton({
  icon: Icon,
  iconPosition = 'start',
  iconClassName,
  children,
  ...props
}: AppButtonProps) {
  const labeled = hasVisibleLabel(children)
  const iconNode = Icon ? (
    <Icon
      data-icon={
        labeled ? (iconPosition === 'start' ? 'inline-start' : 'inline-end') : undefined
      }
      aria-hidden
      className={cn(iconClassName)}
    />
  ) : null

  return (
    <Button {...props}>
      {iconPosition === 'start' ? iconNode : null}
      {children}
      {iconPosition === 'end' ? iconNode : null}
    </Button>
  )
}
