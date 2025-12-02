import { WS_BASE_URL } from '../config';

const ensureLeadingSlash = (value: string): string =>
  value.startsWith('/') ? value : `/${value}`;

const toWebSocketScheme = (value: string): string => {
  if (!value) {
    return value;
  }
  if (/^wss?:\/\//i.test(value)) {
    return value;
  }
  if (/^https?:\/\//i.test(value)) {
    return value.replace(/^http(s)?:\/\//i, (match) => (match.toLowerCase() === 'https://' ? 'wss://' : 'ws://'));
  }
  return value;
};

const runtimeOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:8000';
const runtimeWebSocketOrigin = toWebSocketScheme(runtimeOrigin);

export const buildBackendWebSocketUrl = (
  endpointPath: string,
  queryParams: Record<string, string | undefined> = {}
): string => {
  const baseCandidate = WS_BASE_URL && WS_BASE_URL.trim().length > 0
    ? WS_BASE_URL.trim()
    : runtimeWebSocketOrigin;
  const baseUrl = toWebSocketScheme(baseCandidate) || runtimeWebSocketOrigin;
  const path = ensureLeadingSlash(endpointPath);

  const searchParams = new URLSearchParams();
  Object.entries(queryParams).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, value);
    }
  });
  const queryString = searchParams.toString();

  try {
    const url = new URL(baseUrl);
    url.pathname = path;
    url.search = '';
    url.hash = '';
    if (queryString) {
      url.search = queryString;
    }
    return url.toString();
  } catch {
    const sanitizedBase = baseUrl.replace(/\/+$/, '');
    return `${sanitizedBase}${path}${queryString ? `?${queryString}` : ''}`;
  }
};
