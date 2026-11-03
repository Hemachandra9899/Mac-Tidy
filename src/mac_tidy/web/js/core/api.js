// HTTP client for the local server. Mutations carry a session token, which is
// renewed once automatically if the server restarted.

export function createClient(fetcher = (...args) => fetch(...args)) {
  let token = '';

  async function renew() {
    const response = await fetcher('/api/session', { cache: 'no-store' });
    if (!response.ok) throw new Error('Cannot connect to the local session. Reload this page.');
    token = (await response.json()).token;
  }

  async function get(path) {
    const response = await fetcher(path, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return response.json();
  }

  async function post(path, body) {
    if (!token) await renew();
    for (let attempt = 0; attempt < 2; attempt++) {
      const response = await fetcher(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': token },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (response.ok) return data;
      if (response.status === 403 && data.code === 'session_expired' && attempt === 0) {
        await renew();
        continue;
      }
      throw new Error(data.error || 'Action failed');
    }
  }

  return { get, post };
}

export const api = createClient();
