/** Entrada de log unificada, compartida entre el proceso `main` y el proceso backend. */
export interface LogEntry {
  timestamp: string
  source: 'backend' | 'main'
  stream: 'stdout' | 'stderr' | 'info' | 'error'
  line: string
}
