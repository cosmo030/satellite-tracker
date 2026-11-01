/**
 * Skins change surface materials only (colours, blur, radii); layout and type stay the same.
 * The effective skin is written to `<html data-skin>` and every difference lives in CSS tokens.
 */

export type Skin = 'instrument' | 'frosted';

export const SKINS: readonly Skin[] = ['instrument', 'frosted'];
export const DEFAULT_SKIN: Skin = 'instrument';
export const SKIN_STORAGE_KEY = 'sattrack.ui.skin';

export function parseStoredSkin(raw: string | null): Skin {
  return SKINS.find((skin) => skin === raw) ?? DEFAULT_SKIN;
}

export interface GlassSupport {
  /** The OS asks for less transparency (`prefers-reduced-transparency: reduce`). */
  reducedTransparency: boolean;
  /** The browser supports `backdrop-filter`. */
  backdropFilter: boolean;
}

/** Frosted glass falls back to solid Instrument surfaces when glass cannot or should not render. */
export function effectiveSkin(preference: Skin, support: GlassSupport): Skin {
  if (preference !== 'frosted') return preference;
  return support.backdropFilter && !support.reducedTransparency ? 'frosted' : 'instrument';
}
