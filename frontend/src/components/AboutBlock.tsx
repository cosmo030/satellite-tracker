import { useRef, useState } from 'react';

import type { AboutCategory, AboutImage, SatelliteAbout } from '../api/client';
import { ImageViewer } from './ImageViewer';

const CATEGORY_LABELS: Record<AboutCategory, string> = {
  space_station: 'Space station',
  crewed: 'Crewed',
  telescope: 'Space telescope',
  earth_observation: 'Earth observation',
  weather: 'Weather',
  navigation: 'Navigation',
  communications: 'Communications',
  science: 'Science',
  technology: 'Technology demo',
  amateur: 'Amateur radio',
  military: 'Military',
  cubesat: 'CubeSat',
};
const CC_BY_SA_4 = 'https://creativecommons.org/licenses/by-sa/4.0/';
const IMAGE_SIZES = '(max-width: 759px) calc(100vw - 36px), 460px';

interface AboutBlockProps {
  about: SatelliteAbout;
  satelliteName: string;
}

/**
 * Description, purpose and image from Wikimedia, below "More details". Every part is left out
 * when its data is missing; every piece of content shows its source and license.
 */
export function AboutBlock({ about, satelliteName }: AboutBlockProps) {
  return (
    <section className="about" aria-label={`About ${satelliteName}`}>
      <div className="about-inner">
        {about.image && <AboutMedia image={about.image} satelliteName={satelliteName} />}
        {about.categories.length > 0 && (
          <p className="about-chips">
            {about.categories.map((category) => (
              <span key={category} className="chip">
                {CATEGORY_LABELS[category]}
              </span>
            ))}
          </p>
        )}
        {about.summary && <AboutText about={about} summary={about.summary} />}
        <AboutFacts operators={about.operators} manufacturers={about.manufacturers} />
      </div>
    </section>
  );
}

function AboutMedia({ image, satelliteName }: { image: AboutImage; satelliteName: string }) {
  const [loaded, setLoaded] = useState(false);
  const [viewerOpen, setViewerOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const credit = `${image.artist}, ${image.license_short}`;
  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="about-media"
        aria-label={`View image of ${satelliteName}`}
        onClick={() => {
          setViewerOpen(true);
        }}
      >
        <img
          src={image.url_480}
          srcSet={`${image.url_480} 480w, ${image.url_960} 960w`}
          sizes={IMAGE_SIZES}
          width={image.width_480}
          height={image.height_480}
          alt={image.alt_text || satelliteName}
          loading="lazy"
          decoding="async"
          className={loaded ? 'loaded' : undefined}
          onLoad={() => {
            setLoaded(true);
          }}
        />
      </button>
      <a className="about-credit" href={image.source_url} target="_blank" rel="noopener noreferrer">
        <span className="visually-hidden">Image: </span>
        {credit}
      </a>
      {viewerOpen && (
        <ImageViewer
          image={image}
          satelliteName={satelliteName}
          onClose={() => {
            setViewerOpen(false);
            buttonRef.current?.focus();
          }}
        />
      )}
    </>
  );
}

function AboutText({ about, summary }: { about: SatelliteAbout; summary: string }) {
  // Constellation text describes the constellation, never this particular satellite.
  const heading =
    about.scope === 'constellation' && about.title ? `About the ${about.title}` : 'About';
  return (
    <>
      <h4 className="about-heading">{heading}</h4>
      <p className="about-summary">{summary}</p>
      <SourceLine about={about} />
    </>
  );
}

function SourceLine({ about }: { about: SatelliteAbout }) {
  if (about.summary_source === 'wikidata') {
    return (
      <p className="about-source">
        <SourceLink href={about.summary_url}>From Wikidata</SourceLink>
      </p>
    );
  }
  return (
    <p className="about-source">
      <SourceLink href={about.summary_url}>From Wikipedia</SourceLink>,{' '}
      <a href={CC_BY_SA_4} target="_blank" rel="noopener noreferrer license">
        {about.summary_license ?? 'CC BY-SA 4.0'}
      </a>
    </p>
  );
}

function SourceLink({ href, children }: { href: string | null; children: string }) {
  if (!href) return <>{children}</>;
  return (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}

function AboutFacts({
  operators,
  manufacturers,
}: {
  operators: string[];
  manufacturers: string[];
}) {
  if (operators.length === 0 && manufacturers.length === 0) return null;
  return (
    <dl className="about-facts">
      {operators.length > 0 && (
        <div>
          <dt>{operators.length > 1 ? 'Operators' : 'Operator'}</dt>
          <dd>{operators.join(', ')}</dd>
        </div>
      )}
      {manufacturers.length > 0 && (
        <div>
          <dt>Manufacturer</dt>
          <dd>{manufacturers.join(', ')}</dd>
        </div>
      )}
    </dl>
  );
}
