import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  fullName: string
  companyName?: string
  role: 'USER' | 'ADMIN' | 'SUPER_ADMIN'
  plan: 'FREE' | 'STARTER' | 'PROFESSIONAL' | 'ENTERPRISE'
  creditsRemaining: number
  creditsTotal: number
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (token: string, user: User) => void
  logout: () => void
  updateCredits: (credits: number) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (token, user) => set({ token, user, isAuthenticated: true }),
      logout: () => set({ token: null, user: null, isAuthenticated: false }),
      updateCredits: (credits) => set((state) => ({
        user: state.user ? { ...state.user, creditsRemaining: credits } : null
      }))
    }),
    {
      name: 'auth-storage'
    }
  )
)