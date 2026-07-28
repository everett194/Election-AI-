import { createContext, useContext } from 'react'
import type { PageName } from '../types'

interface NavContextType {
  page: PageName
  navigate: (page: PageName, params?: Record<string, string>) => void
  params: Record<string, string>
}

export const NavContext = createContext<NavContextType>({
  page: 'home',
  navigate: () => {},
  params: {},
})

export const useNav = () => useContext(NavContext)
