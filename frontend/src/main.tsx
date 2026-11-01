import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { initialSkin } from './hooks/useSkin';
import './styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('Missing #root element in index.html');

// Set the skin before the first render so the page never flashes the wrong surfaces.
document.documentElement.dataset.skin = initialSkin();

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
