import { useCallback, useLayoutEffect, useState } from 'react';

import {
  effectiveSkin,
  parseStoredSkin,
  SKIN_STORAGE_KEY,
  type GlassSupport,
  type Skin,
} from '../ui/skin';
import { readStorage, writeStorage } from '../ui/storage';
import { useMediaQuery } from './useMediaQuery';

const REDUCED_TRANSPARENCY = '(prefers-reduced-transparency: reduce)';
const BACKDROP_FILTER =
  CSS.supports('backdrop-filter', 'blur(1px)') ||
  CSS.supports('-webkit-backdrop-filter', 'blur(1px)');

export interface SkinState {
  /** The skin chosen in Settings. */
  preference: Skin;
  /** The skin actually shown (Frosted glass may fall back to Instrument surfaces). */
  skin: Skin;
  /** Why Frosted glass is not shown, for the note in Settings; null when it is. */
  glassNote: string | null;
  choose: (skin: Skin) => void;
}

/** The effective skin before React renders, so the first paint already uses it. */
export function initialSkin(): Skin {
  const support: GlassSupport = {
    reducedTransparency: window.matchMedia(REDUCED_TRANSPARENCY).matches,
    backdropFilter: BACKDROP_FILTER,
  };
  return effectiveSkin(parseStoredSkin(readStorage(SKIN_STORAGE_KEY)), support);
}

/** The user's skin preference (saved), the effective skin, and `<html data-skin>` kept in sync. */
export function useSkin(): SkinState {
  const [preference, setPreference] = useState<Skin>(() =>
    parseStoredSkin(readStorage(SKIN_STORAGE_KEY)),
  );
  const reducedTransparency = useMediaQuery(REDUCED_TRANSPARENCY);
  const skin = effectiveSkin(preference, { reducedTransparency, backdropFilter: BACKDROP_FILTER });

  // A layout effect, so the attribute (and the CSS accent) changes before other effects read it.
  useLayoutEffect(() => {
    document.documentElement.dataset.skin = skin;
  }, [skin]);

  const choose = useCallback((next: Skin) => {
    setPreference(next);
    writeStorage(SKIN_STORAGE_KEY, next);
  }, []);

  return { preference, skin, glassNote: glassNote(preference, skin, reducedTransparency), choose };
}

function glassNote(preference: Skin, skin: Skin, reducedTransparency: boolean): string | null {
  if (preference !== 'frosted' || skin === 'frosted') return null;
  return reducedTransparency
    ? 'Transparency is reduced by your system, so surfaces stay solid.'
    : 'This browser cannot blur surfaces, so they stay solid.';
}
