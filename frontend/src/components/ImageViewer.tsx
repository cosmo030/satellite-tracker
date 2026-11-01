import { useEffect, useRef, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';

import type { AboutImage } from '../api/client';
import { CloseIcon } from './icons';

interface ImageViewerProps {
  image: AboutImage;
  satelliteName: string;
  /** Called on Esc, the close button or a click on the scrim; the caller restores focus. */
  onClose: () => void;
}

const FOCUSABLE = 'a[href], button:not([disabled])';

/**
 * The large image with its full credit, in a modal dialog over a dark scrim. Rendered into
 * <body>, so a tile's clipping and blur never apply to it. Focus stays inside while open.
 */
export function ImageViewer({ image, satelliteName, onClose }: ImageViewerProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key === 'Tab' && dialogRef.current) trapFocus(event, dialogRef.current);
  };

  return createPortal(
    <div className="viewer-scrim" onClick={onClose}>
      <div
        ref={dialogRef}
        className="popover viewer"
        role="dialog"
        aria-modal="true"
        aria-label={`Image of ${satelliteName}`}
        onKeyDown={onKeyDown}
        onClick={(event) => {
          event.stopPropagation();
        }}
      >
        <button
          ref={closeRef}
          type="button"
          className="icon-button viewer-close"
          aria-label="Close image"
          onClick={onClose}
        >
          <CloseIcon />
        </button>
        <img className="viewer-image" src={image.url_960} alt={image.alt_text || satelliteName} />
        <p className="viewer-credit">
          {image.artist}, {image.license_short}
        </p>
        <p className="viewer-links">
          {image.license_url && (
            <a href={image.license_url} target="_blank" rel="noopener noreferrer license">
              License: {image.license_short}
            </a>
          )}
          <a href={image.source_url} target="_blank" rel="noopener noreferrer">
            View on Wikimedia Commons
          </a>
        </p>
      </div>
    </div>,
    document.body,
  );
}

/** Keep Tab and Shift+Tab cycling through the dialog's links and buttons. */
function trapFocus(event: KeyboardEvent<HTMLDivElement>, dialog: HTMLElement): void {
  const focusable = [...dialog.querySelectorAll<HTMLElement>(FOCUSABLE)];
  const first = focusable[0];
  const last = focusable.at(-1);
  if (!first || !last) return;
  const active = document.activeElement;
  if (event.shiftKey && (active === first || !dialog.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}
