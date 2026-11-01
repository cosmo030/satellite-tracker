import { useCallback, useSyncExternalStore } from 'react';

/** Whether a CSS media query matches, updated when it changes. */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = window.matchMedia(query);
      list.addEventListener('change', onChange);
      return () => {
        list.removeEventListener('change', onChange);
      };
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches);
}

export type LayoutMode = 'wide' | 'medium' | 'narrow';

/** Spec breakpoints: under 1100 px the right column becomes a sheet; under 760 px, bottom sheets. */
export function useLayoutMode(): LayoutMode {
  const narrow = useMediaQuery('(max-width: 759.98px)');
  const medium = useMediaQuery('(max-width: 1099.98px)');
  if (narrow) return 'narrow';
  return medium ? 'medium' : 'wide';
}
