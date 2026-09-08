/* Simple dependency-free test runner for the discount engine. */
var Engine = require('./discount-engine.js');

var passed = 0, failed = 0;
function approx(a, b) { return Math.abs(a - b) < 0.001; }
function test(name, fn) {
  try { fn(); passed++; console.log('  PASS  ' + name); }
  catch (e) { failed++; console.log('  FAIL  ' + name + '\n        ' + e.message); }
}
function eq(actual, expected, msg) {
  if (!approx(actual, expected)) {
    throw new Error((msg || '') + ' expected ' + expected + ' but got ' + actual);
  }
}
function throws(fn, msg) {
  var threw = false;
  try { fn(); } catch (e) { threw = true; }
  if (!threw) throw new Error((msg || 'expected an error') + ' (nothing thrown)');
}

console.log('\n--- Document examples ---');

test('Fixed amount: 350 + 250 - 50 = 550', function () {
  var r = Engine.calculate(
    [{ name: 'T-Shirt', category: 'Clothing', price: 350 },
     { name: 'Hat', category: 'Accessories', price: 250 }],
    [{ type: 'fixed', amount: 50 }]);
  eq(r.finalPrice, 550);
});

test('Percentage discount: 600 - 10% = 540', function () {
  var r = Engine.calculate(
    [{ name: 'T-Shirt', category: 'Clothing', price: 350 },
     { name: 'Hat', category: 'Accessories', price: 250 }],
    [{ type: 'percentage', percentage: 10 }]);
  eq(r.finalPrice, 540);
});

test('Category %: 15% off Clothing -> 2382.5', function () {
  var r = Engine.calculate(
    [{ name: 'T-Shirt', category: 'Clothing', price: 350 },
     { name: 'Hoodie', category: 'Clothing', price: 700 },
     { name: 'Watch', category: 'Electronics', price: 850 },
     { name: 'Bag', category: 'Accessories', price: 640 }],
    [{ type: 'categoryPercentage', category: 'Clothing', percentage: 15 }]);
  eq(r.finalPrice, 2382.5);
});

test('Points: 68 points on 830 -> 762', function () {
  var r = Engine.calculate(
    [{ name: 'T-Shirt', category: 'Clothing', price: 350 },
     { name: 'Hat', category: 'Accessories', price: 250 },
     { name: 'Belt', category: 'Accessories', price: 230 }],
    [{ type: 'points', points: 68 }]);
  eq(r.finalPrice, 762);
});

test('Seasonal: 40 off every 300 on 830 -> 750', function () {
  var r = Engine.calculate(
    [{ name: 'T-Shirt', category: 'Clothing', price: 350 },
     { name: 'Hat', category: 'Accessories', price: 250 },
     { name: 'Belt', category: 'Accessories', price: 230 }],
    [{ type: 'seasonal', every: 300, discount: 40 }]);
  eq(r.finalPrice, 750);
});

console.log('\n--- Rules & ordering ---');

test('Order Coupon > OnTop > Seasonal is enforced regardless of input order', function () {
  var cart = [{ name: 'A', category: 'Clothing', price: 1000 }];
  var campaigns = [
    { type: 'seasonal', every: 100, discount: 10 },
    { type: 'percentage', percentage: 10 } // coupon
  ];
  var r = Engine.calculate(cart, campaigns);
  // Coupon first: 1000 -> 900. Then seasonal: floor(900/100)*10 = 90 -> 810.
  eq(r.steps[0].category === 'Coupon' ? r.steps[0].after : r.steps[1].after, 900,
     'coupon should apply first');
  eq(r.finalPrice, 810);
});

test('Points cap applies to running total after coupon', function () {
  var cart = [{ name: 'A', category: 'Clothing', price: 1000 }];
  // Coupon 50% -> 500. Points 1000 requested but cap = 20% of 500 = 100.
  var r = Engine.calculate(cart, [
    { type: 'percentage', percentage: 50 },
    { type: 'points', points: 1000 }
  ]);
  eq(r.finalPrice, 400);
});

console.log('\n--- Resilience / bad input ---');

test('Rejects two campaigns from same category', function () {
  throws(function () {
    Engine.calculate([{ name: 'A', category: 'Clothing', price: 100 }],
      [{ type: 'fixed', amount: 10 }, { type: 'percentage', percentage: 5 }]);
  });
});

test('Rejects unknown campaign type', function () {
  throws(function () {
    Engine.calculate([{ name: 'A', category: 'Clothing', price: 100 }],
      [{ type: 'bogus' }]);
  });
});

test('Rejects negative price', function () {
  throws(function () {
    Engine.calculate([{ name: 'A', category: 'Clothing', price: -5 }], []);
  });
});

test('Rejects percentage > 100', function () {
  throws(function () {
    Engine.calculate([{ name: 'A', category: 'Clothing', price: 100 }],
      [{ type: 'percentage', percentage: 150 }]);
  });
});

test('Fixed amount never drives price below 0', function () {
  var r = Engine.calculate([{ name: 'A', category: 'Clothing', price: 100 }],
    [{ type: 'fixed', amount: 999 }]);
  eq(r.finalPrice, 0);
});

test('Empty cart + no campaigns -> 0', function () {
  var r = Engine.calculate([], []);
  eq(r.finalPrice, 0);
});

test('No campaigns returns subtotal unchanged', function () {
  var r = Engine.calculate([{ name: 'A', category: 'Clothing', price: 123.45 }], []);
  eq(r.finalPrice, 123.45);
});

console.log('\n============================');
console.log('  ' + passed + ' passed, ' + failed + ' failed');
console.log('============================\n');
process.exit(failed ? 1 : 0);
