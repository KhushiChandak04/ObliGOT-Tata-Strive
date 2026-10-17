/** The next lifecycle stage in the backend's order, or null at the end. */
export function nextStage(order: string[], stage: string): string | null {
  const index = order.indexOf(stage);
  return index >= 0 && index < order.length - 1 ? order[index + 1] : null;
}
