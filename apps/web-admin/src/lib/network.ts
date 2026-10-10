// Connection awareness. On 2G/3G or with "data saver" on, poll less and defer heavy content (map tiles).
// navigator.connection exists in Chrome/Android (most cooperative offices); elsewhere we assume a normal link.

type NetInfo = { effectiveType?: string; saveData?: boolean; addEventListener?: (t: string, f: () => void) => void };
const conn = (navigator as Navigator & { connection?: NetInfo }).connection;

export function isSlowConnection(): boolean {
  if (!conn) return false;
  return Boolean(conn.saveData) || ["slow-2g", "2g", "3g"].includes(conn.effectiveType ?? "");
}

/** Polling interval adapted to the link: x4 on slow connections. Pages poll only while visible
 *  (TanStack Query pauses intervals in background tabs). */
export function pollEvery(ms: number): number {
  return isSlowConnection() ? ms * 4 : ms;
}
