import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

import { getRecommendPreview } from '../src/home-dashboard.js';

test('getRecommendPreview maps recommendation payload into home card text', () => {
  const preview = getRecommendPreview({
    id: 12,
    recommended_topic: 'quadratic-function',
    question_payload: {
      question: 'Find the vertex of y=x^2-4x+3.',
    },
    status: 'pending',
  });

  assert.deepEqual(preview, {
    title: 'Find the vertex of y=x^2-4x+3.',
    meta: 'quadratic-function',
  });
});

test('getRecommendPreview falls back to topic when question text is missing', () => {
  const preview = getRecommendPreview({
    id: 13,
    recommended_topic: 'pythagorean-theorem',
    question_payload: {},
    status: 'pending',
  });

  assert.deepEqual(preview, {
    title: 'pythagorean-theorem',
    meta: '',
  });
});

test('home recommendation list keeps long titles from squeezing action buttons', () => {
  const cssPath = fileURLToPath(
    new URL('../src/pages/HomePage/HomePage.module.css', import.meta.url)
  );
  const css = readFileSync(cssPath, 'utf8');

  assert.match(css, /\.listItem[\s\S]*gap:/);
  assert.match(css, /\.itemInfo[\s\S]*min-width:\s*0/);
  assert.match(css, /\.itemTitle[\s\S]*overflow-wrap:/);
  assert.match(css, /\.listItem\s+\.primaryBtn[\s\S]*white-space:\s*nowrap/);
});
