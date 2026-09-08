/**
 * discount-engine.js
 * Pure discount calculation module for Playtorium assignment.
 *
 * No DOM / no framework dependency so it can run in the browser AND under Node
 * for testing. Exposes a single `DiscountEngine` object.
 *
 * ---- Domain model ----
 * CartItem: { name: string, category: 'Dessert'|'Main_course'|'Beverage', price: number }
 * Campaign: { type: <campaign type>, ...params }
 *
 * Campaign categories & the mutual-exclusion / ordering rules:
 *   Coupon   -> 'fixed' | 'percentage'                (max 1)
 *   OnTop    -> 'categoryPercentage' | 'points'       (max 1)
 *   Seasonal -> 'seasonal'                            (max 1)
 * Application order is always: Coupon > On Top > Seasonal.
 */
(function (root) {
  'use strict';

  var VALID_CATEGORIES = ['Dessert', 'Main_course', 'Beverage'];

  var CAMPAIGN_CATEGORY = {
    fixed: 'Coupon',
    percentage: 'Coupon',
    categoryPercentage: 'OnTop',
    points: 'OnTop',
    seasonal: 'Seasonal'
  };

  // Fixed business rule: points discount is capped at this share of the running total.
  var POINTS_CAP_RATIO = 0.20;

  function isFiniteNumber(n) {
    return typeof n === 'number' && isFinite(n);
  }

  function round2(n) {
    // Avoid binary float artefacts like 762.0000000001.
    return Math.round((n + Number.EPSILON) * 100) / 100;
  }

  // ---------------------------------------------------------------------------
  // Validation
  // ---------------------------------------------------------------------------

  function validateCart(cart) {
    if (!Array.isArray(cart)) {
      throw new TypeError('Cart must be an array of items.');
    }
    cart.forEach(function (item, i) {
      if (!item || typeof item !== 'object') {
        throw new TypeError('Cart item #' + (i + 1) + ' is not an object.');
      }
      if (!isFiniteNumber(item.price) || item.price < 0) {
        throw new RangeError(
          'Cart item "' + (item.name || i + 1) + '" has an invalid price.'
        );
      }
      if (item.category && VALID_CATEGORIES.indexOf(item.category) === -1) {
        throw new RangeError(
          'Cart item "' + (item.name || i + 1) + '" has unknown category "' +
          item.category + '".'
        );
      }
    });
  }

  function validateCampaigns(campaigns) {
    if (!Array.isArray(campaigns)) {
      throw new TypeError('Campaigns must be an array.');
    }
    var seen = {};
    campaigns.forEach(function (c, i) {
      if (!c || typeof c !== 'object') {
        throw new TypeError('Campaign #' + (i + 1) + ' is not an object.');
      }
      var cat = CAMPAIGN_CATEGORY[c.type];
      if (!cat) {
        throw new RangeError('Unknown campaign type "' + c.type + '".');
      }
      // Mutual exclusion: only one campaign per category.
      if (seen[cat]) {
        throw new RangeError(
          'Only one ' + cat + ' campaign is allowed (got "' + seen[cat] +
          '" and "' + c.type + '").'
        );
      }
      seen[cat] = c.type;
    });
  }

  // ---------------------------------------------------------------------------
  // Individual campaign appliers. Each returns the discount amount (>= 0)
  // to subtract from the running total.
  // ---------------------------------------------------------------------------

  function applyFixed(total, cart, params) {
    var amount = params.amount;
    if (!isFiniteNumber(amount) || amount < 0) {
      throw new RangeError('Fixed amount must be a non-negative number.');
    }
    return Math.min(amount, total); // never go below zero
  }

  function applyPercentage(total, cart, params) {
    var pct = params.percentage;
    if (!isFiniteNumber(pct) || pct < 0 || pct > 100) {
      throw new RangeError('Percentage must be between 0 and 100.');
    }
    return total * (pct / 100);
  }

  function applyCategoryPercentage(total, cart, params) {
    var pct = params.percentage;
    var category = params.category;
    if (VALID_CATEGORIES.indexOf(category) === -1) {
      throw new RangeError('Unknown category "' + category + '".');
    }
    if (!isFiniteNumber(pct) || pct < 0 || pct > 100) {
      throw new RangeError('Percentage must be between 0 and 100.');
    }
    var categorySum = cart.reduce(function (sum, item) {
      return item.category === category ? sum + item.price : sum;
    }, 0);
    return categorySum * (pct / 100);
  }

  function applyPoints(total, cart, params) {
    var points = params.points;
    if (!isFiniteNumber(points) || points < 0) {
      throw new RangeError('Points must be a non-negative number.');
    }
    var cap = total * POINTS_CAP_RATIO; // 1 point = 1 THB, capped at 20%
    return Math.min(points, cap);
  }

  function applySeasonal(total, cart, params) {
    var every = params.every;
    var discount = params.discount;
    if (!isFiniteNumber(every) || every <= 0) {
      throw new RangeError('Seasonal "every X THB" must be a positive number.');
    }
    if (!isFiniteNumber(discount) || discount < 0) {
      throw new RangeError('Seasonal "discount Y THB" must be non-negative.');
    }
    var blocks = Math.floor(total / every);
    return Math.min(blocks * discount, total);
  }

  var APPLIERS = {
    fixed: applyFixed,
    percentage: applyPercentage,
    categoryPercentage: applyCategoryPercentage,
    points: applyPoints,
    seasonal: applySeasonal
  };

  // Deterministic application order regardless of input ordering.
  var ORDER = ['Coupon', 'OnTop', 'Seasonal'];

  // ---------------------------------------------------------------------------
  // Public entry point
  // ---------------------------------------------------------------------------

  /**
   * calculate(cart, campaigns) -> {
   *   subtotal, finalPrice, totalDiscount, steps: [{type, category, before, discount, after}]
   * }
   */
  function calculate(cart, campaigns) {
    cart = cart || [];
    campaigns = campaigns || [];
    validateCart(cart);
    validateCampaigns(campaigns);

    var subtotal = cart.reduce(function (s, item) { return s + item.price; }, 0);

    // Bucket campaigns by their category so we can apply in fixed order.
    var byCategory = {};
    campaigns.forEach(function (c) {
      byCategory[CAMPAIGN_CATEGORY[c.type]] = c;
    });

    var running = subtotal;
    var steps = [];

    ORDER.forEach(function (cat) {
      var c = byCategory[cat];
      if (!c) return;
      var before = running;
      var discount = APPLIERS[c.type](running, cart, c);
      discount = Math.max(0, Math.min(discount, running)); // clamp
      running = round2(running - discount);
      steps.push({
        type: c.type,
        category: cat,
        before: round2(before),
        discount: round2(discount),
        after: running
      });
    });

    return {
      subtotal: round2(subtotal),
      totalDiscount: round2(subtotal - running),
      finalPrice: round2(running),
      steps: steps
    };
  }

  var DiscountEngine = {
    calculate: calculate,
    VALID_CATEGORIES: VALID_CATEGORIES,
    CAMPAIGN_CATEGORY: CAMPAIGN_CATEGORY,
    POINTS_CAP_RATIO: POINTS_CAP_RATIO,
    _round2: round2
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = DiscountEngine;
  } else {
    root.DiscountEngine = DiscountEngine;
  }
})(typeof self !== 'undefined' ? self : this);
