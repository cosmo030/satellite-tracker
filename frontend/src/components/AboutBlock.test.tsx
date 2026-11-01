// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { AboutBlock } from './AboutBlock';
import { about } from './aboutFixtures';

afterEach(cleanup);

function parts(container: HTMLElement): string[] {
  const names = ['about-media', 'about-credit', 'about-chips', 'about-heading', 'about-summary'];
  const present = names.filter((name) => container.querySelector(`.${name}`) !== null);
  if (container.querySelector('.about-source')) present.push('about-source');
  if (container.querySelector('.about-facts')) present.push('about-facts');
  return present;
}

describe('AboutBlock fallback rows', () => {
  it('shows everything with a description and an image', () => {
    const { container } = render(<AboutBlock about={about()} satelliteName="TESTSAT 1" />);

    expect(parts(container)).toEqual([
      'about-media',
      'about-credit',
      'about-chips',
      'about-heading',
      'about-summary',
      'about-source',
      'about-facts',
    ]);
    expect(screen.getByText('Test Photographer, CC BY-SA 4.0')).toBeTruthy();
    expect(screen.getByText('Science')).toBeTruthy();
    expect(screen.getByText('CubeSat')).toBeTruthy();
    expect(screen.getByText('Operators').nextElementSibling?.textContent).toBe(
      'Agency One, Agency Two',
    );
    expect(screen.getByRole('link', { name: 'From Wikipedia' }).getAttribute('href')).toBe(
      'https://en.wikipedia.org/wiki/Testsat',
    );
  });

  it('leaves the image out when there is none', () => {
    const { container } = render(
      <AboutBlock about={about({ image: null })} satelliteName="TESTSAT 1" />,
    );

    expect(parts(container)).not.toContain('about-media');
    expect(parts(container)).not.toContain('about-credit');
    expect(parts(container)).toContain('about-summary');
  });

  it('shows image, credit and chips only when there is no description', () => {
    const { container } = render(
      <AboutBlock
        about={about({
          summary: null,
          summary_source: null,
          summary_url: null,
          operators: [],
          manufacturers: [],
        })}
        satelliteName="TESTSAT 1"
      />,
    );

    expect(parts(container)).toEqual(['about-media', 'about-credit', 'about-chips']);
  });

  it('credits Wikidata descriptions without a Wikipedia license', () => {
    render(
      <AboutBlock
        about={about({ summary_source: 'wikidata', summary_license: 'CC0', image: null })}
        satelliteName="TESTSAT 1"
      />,
    );

    expect(screen.getByText('From Wikidata')).toBeTruthy();
    expect(screen.queryByText(/CC BY-SA/)).toBeNull();
  });

  it('labels constellation text as being about the constellation', () => {
    render(
      <AboutBlock
        about={about({ scope: 'constellation', title: 'Testnet constellation', image: null })}
        satelliteName="TESTNET-42"
      />,
    );

    expect(screen.getByRole('heading', { name: 'About the Testnet constellation' })).toBeTruthy();
  });

  it('uses a plain heading for the object itself', () => {
    render(<AboutBlock about={about()} satelliteName="TESTSAT 1" />);

    expect(screen.getByRole('heading', { name: 'About' })).toBeTruthy();
  });
});

describe('ImageViewer', () => {
  it('opens, traps focus and closes on Esc', () => {
    render(<AboutBlock about={about()} satelliteName="TESTSAT 1" />);
    const opener = screen.getByRole('button', { name: 'View image of TESTSAT 1' });

    fireEvent.click(opener);
    const dialog = screen.getByRole('dialog', { name: 'Image of TESTSAT 1' });
    const close = screen.getByRole('button', { name: 'Close image' });
    expect(document.activeElement).toBe(close);

    const links = dialog.querySelectorAll('a');
    const last = links[links.length - 1];
    last?.focus();
    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(document.activeElement).toBe(close);
    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });
    expect(document.activeElement).toBe(last);

    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(opener);
  });

  it('shows the large image with its full credit and closes from the scrim', () => {
    render(<AboutBlock about={about()} satelliteName="TESTSAT 1" />);
    fireEvent.click(screen.getByRole('button', { name: 'View image of TESTSAT 1' }));

    const dialog = screen.getByRole('dialog');
    expect(dialog.querySelector('img')?.getAttribute('src')).toBe(
      '/api/v1/satellites/90001/image?w=960',
    );
    expect(screen.getByRole('link', { name: 'View on Wikimedia Commons' })).toBeTruthy();

    fireEvent.click(dialog);
    expect(screen.queryByRole('dialog')).not.toBeNull();
    const scrim = dialog.parentElement;
    if (scrim) fireEvent.click(scrim);
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
