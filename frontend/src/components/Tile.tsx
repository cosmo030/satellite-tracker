import type { ReactNode } from 'react';

interface TileProps {
  /** Used for the heading id that labels the section. */
  id: string;
  title: string;
  /** Count or context shown on the right of the header. */
  meta?: ReactNode;
  /** Show the title for screen readers only (the tile's content speaks for itself). */
  hideHeader?: boolean;
  className?: string;
  children: ReactNode;
}

/** A workspace tile: a labelled section with a 12 px muted header and its content below. */
export function Tile({ id, title, meta, hideHeader = false, className, children }: TileProps) {
  const headingId = `${id}-heading`;
  return (
    <section className={className ? `tile ${className}` : 'tile'} aria-labelledby={headingId}>
      {hideHeader ? (
        <h2 id={headingId} className="visually-hidden">
          {title}
        </h2>
      ) : (
        <header className="tile-header">
          <h2 id={headingId} className="tile-title">
            {title}
          </h2>
          {meta !== undefined && <div className="tile-meta">{meta}</div>}
        </header>
      )}
      <div className="tile-body">{children}</div>
    </section>
  );
}
