import { calculatePurchaseTotal } from "../src/utils/purchaseMath";

function assertEqual(actual: number, expected: number, label: string) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

assertEqual(calculatePurchaseTotal(2, 9.99), 19.98, "multiplies quantity and unit price");
assertEqual(calculatePurchaseTotal(undefined, 9.99), 0, "treats missing quantity as zero");
assertEqual(calculatePurchaseTotal(3, undefined), 0, "treats missing unit price as zero");
assertEqual(calculatePurchaseTotal(3, 1.005), 3.02, "rounds to two decimal places");
