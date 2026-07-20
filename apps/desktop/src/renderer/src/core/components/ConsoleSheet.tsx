import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle
} from '@/components/ui/sheet'

import { LogConsole } from './LogConsole'

interface ConsoleSheetProps {
  open: boolean
  onClose: () => void
}

export function ConsoleSheet({ open, onClose }: ConsoleSheetProps) {
  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent
        id="console-sheet"
        side="right"
        className="flex w-1/2! max-w-none! flex-col gap-0 p-0 data-[side=right]:w-1/2 data-[side=right]:max-w-none sm:max-w-none"
      >
        <SheetHeader className="border-b border-border px-4 py-3">
          <SheetTitle>Registro</SheetTitle>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col p-3">
          <LogConsole />
        </div>
      </SheetContent>
    </Sheet>
  )
}
