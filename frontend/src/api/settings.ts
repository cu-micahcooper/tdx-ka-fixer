// frontend/src/api/settings.ts
import client from './client'

export interface AppSettings {
  internal_directive: string
  public_directive: string
}

export const getSettings = (): Promise<AppSettings> =>
  client.get<AppSettings>('/settings').then(r => r.data)

export const patchSettings = (patch: Partial<AppSettings>): Promise<AppSettings> =>
  client.patch<AppSettings>('/settings', patch).then(r => r.data)
