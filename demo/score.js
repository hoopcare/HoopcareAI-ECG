(function (root) {
  'use strict';
  // Order follows the study source's HP configuration.
  const componentIds = Object.freeze([
    'lvef_lte_50', 'ph_rvsp40', 'rv_dysfunction', 'as_severe', 'hcm'
  ]);
  const componentLabels = Object.freeze([
    'LVEF ≤50%', 'Estimated RVSP ≥40 mmHg', 'RV systolic dysfunction',
    'Severe aortic stenosis', 'LV hypertrophy proxy'
  ]);
  const thresholds = Object.freeze({ diagnostic: 0.453, originalSurgicalHigh5: 0.635 });

  function evaluate(scores) {
    if (!Array.isArray(scores) || scores.length !== 5) {
      throw new TypeError('Supply exactly five component scores.');
    }
    const components = Array.from(scores);
    if (components.some(value => typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1)) {
      throw new RangeError('Every component must be a finite number between 0 and 1.');
    }
    // Equivalent to 1 - product(1 - p); preserves a single nonzero input exactly.
    const score = components.reduce((accumulator, value) => accumulator + value * (1 - accumulator), 0);
    return Object.freeze({
      score,
      components: Object.freeze(components),
      flags: Object.freeze({
        diagnostic: score >= thresholds.diagnostic,
        originalSurgicalHigh5: score >= thresholds.originalSurgicalHigh5
      })
    });
  }

  const api = Object.freeze({ evaluate, componentIds, componentLabels, thresholds });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.HoopcareScore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
