export async function settleDataLoads(loads) {
  const results = await Promise.all(loads.map(async ({ label, load, apply, fallback }) => {
    try {
      apply(await load());
      return null;
    } catch {
      apply(fallback);
      return label;
    }
  }));
  return results.filter(Boolean);
}
