import { QueryClient } from '@tanstack/react-query'

/** Instancia única de React Query compartida por toda la app. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1
    }
  }
})
