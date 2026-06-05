import * as React from "react"

export interface Toast {
  id: string
  title?: string
  description?: string
  action?: React.ReactNode
  variant?: "default" | "destructive"
}

interface ToastContextType {
  toasts: Toast[]
  toast: (toast: Omit<Toast, "id">) => void
  dismiss: (id: string) => void
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined)

export function useToast() {
  const context = React.useContext(ToastContext)
  if (!context) {
    // Return a mock implementation if no provider
    return {
      toast: (toast: Omit<Toast, "id">) => {
        console.log("Toast:", toast)
      },
      dismiss: (id: string) => {
        console.log("Dismiss toast:", id)
      },
      toasts: [] as Toast[]
    }
  }
  return context
}

export { ToastContext }