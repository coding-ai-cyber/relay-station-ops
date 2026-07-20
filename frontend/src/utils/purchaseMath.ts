export function calculatePurchaseTotal(
  quantity: number | string | null | undefined,
  unitPrice: number | string | null | undefined
) {
  const numericQuantity = Number(quantity ?? 0);
  const numericUnitPrice = Number(unitPrice ?? 0);

  if (!Number.isFinite(numericQuantity) || !Number.isFinite(numericUnitPrice)) {
    return 0;
  }

  return Math.round((numericQuantity * numericUnitPrice + 1e-8) * 100) / 100;
}
