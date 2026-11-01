import { useEffect, useRef, type RefObject } from 'react';

import { SKINS, type Skin } from '../ui/skin';

const SKIN_LABELS: Record<Skin, string> = {
  instrument: 'Instrument',
  frosted: 'Frosted glass',
};

interface SettingsPopoverProps {
  /** The skin chosen by the user (not the fallback that may be shown). */
  skin: Skin;
  /** Why Frosted glass shows solid surfaces; null when it renders as glass. */
  glassNote: string | null;
  onSkinChange: (skin: Skin) => void;
  onResetLayout: () => void;
  onClose: () => void;
  /** The dock button that opened the popover; focus returns to it on close. */
  anchorRef: RefObject<HTMLButtonElement | null>;
  /** On small screens Settings is a modal with a scrim. */
  modal: boolean;
}

/** Appearance (skin) and layout settings, anchored to the dock. */
export function SettingsPopover({
  skin,
  glassNote,
  onSkinChange,
  onResetLayout,
  onClose,
  anchorRef,
  modal,
}: SettingsPopoverProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  useDismiss(panelRef, anchorRef, onClose);

  useEffect(() => {
    panelRef.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus();
    const anchor = anchorRef.current;
    return () => {
      anchor?.focus();
    };
  }, [anchorRef]);

  return (
    <>
      {modal && <div className="scrim" aria-hidden="true" />}
      <div
        ref={panelRef}
        className="popover settings"
        role="dialog"
        aria-modal={modal}
        aria-labelledby="settings-heading"
      >
        <h2 id="settings-heading">Settings</h2>
        <section aria-labelledby="appearance-heading">
          <h3 id="appearance-heading">Appearance</h3>
          <p className="setting-label" id="theme-label">
            Theme
          </p>
          <div className="segmented" role="radiogroup" aria-labelledby="theme-label">
            {SKINS.map((option) => (
              <button
                key={option}
                type="button"
                role="radio"
                aria-checked={option === skin}
                onClick={() => {
                  onSkinChange(option);
                }}
              >
                {SKIN_LABELS[option]}
              </button>
            ))}
          </div>
          {glassNote && <p className="note">{glassNote}</p>}
        </section>
        <section aria-labelledby="layout-heading">
          <h3 id="layout-heading">Layout</h3>
          <button type="button" className="button" onClick={onResetLayout}>
            Reset layout
          </button>
        </section>
        <p className="about">
          Orbital data from <a href="https://celestrak.org">CelesTrak</a>. Globe by{' '}
          <a href="https://cesium.com/platform/cesiumjs/">CesiumJS</a>.
        </p>
      </div>
    </>
  );
}

/** Close on Escape, or on a pointer press outside the popover and its dock button. */
function useDismiss(
  panelRef: RefObject<HTMLDivElement | null>,
  anchorRef: RefObject<HTMLButtonElement | null>,
  onClose: () => void,
): void {
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCloseRef.current();
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (panelRef.current?.contains(target) || anchorRef.current?.contains(target)) return;
      onCloseRef.current();
    };
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('pointerdown', onPointerDown);
    };
  }, [panelRef, anchorRef]);
}
