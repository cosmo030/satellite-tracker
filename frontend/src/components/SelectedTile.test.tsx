// @vitest-environment jsdom
import { cleanup, render } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { about, detail } from './aboutFixtures';
import { SelectedTile } from './SelectedTile';

const NOW = new Date('2026-11-01T12:00:00Z');
const noop = () => undefined;

afterEach(cleanup);

function renderTile(props: Partial<Parameters<typeof SelectedTile>[0]> = {}) {
  return render(
    <SelectedTile
      selectedId={90001}
      detail={detail}
      state={null}
      now={NOW}
      error={null}
      onClose={noop}
      {...props}
    />,
  ).container;
}

describe('SelectedTile', () => {
  it('renders the layout without a description unchanged', () => {
    const withoutProp = renderTile().innerHTML;
    cleanup();
    const withNull = renderTile({ about: null }).innerHTML;

    expect(withNull).toBe(withoutProp);
    expect(withNull).not.toContain('about');
    expect(withNull).toMatchSnapshot();
  });

  it('adds the About block after "More details" when a description is available', () => {
    const container = renderTile({ about: about() });

    const more = container.querySelector('details.more');
    expect(more?.nextElementSibling?.matches('section.about')).toBe(true);
  });

  it('ignores a description that belongs to another object', () => {
    const container = renderTile({ about: about({ norad_id: 25544 }) });

    expect(container.querySelector('.about')).toBeNull();
  });
});
