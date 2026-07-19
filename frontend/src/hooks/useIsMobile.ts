import { Grid } from 'antd'

export function useIsMobile() {
  const screens = Grid.useBreakpoint()
  return !screens.md
}
