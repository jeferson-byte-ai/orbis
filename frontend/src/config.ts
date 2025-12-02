/**
 * Configuração de URLs para desenvolvimento e produção
 * 
 * Em desenvolvimento (npm run dev):
 *   - API: http://localhost:8000
 *   - WebSocket: ws://localhost:8000
 * 
 * Em produção (deploy):
 *   - API: https://orbis-backend.pella.app (ou sua URL do backend)
 *   - WebSocket: wss://orbis-backend.pella.app
 */

const env = (import.meta as any).env || {};
const isDevelopment = env.MODE === 'development';

const DEFAULT_DEV_API = 'http://localhost:8000';
const DEFAULT_PROD_API = 'https://orbis-backend.pella.app';
const LEGACY_NGROK_API = 'https://convolutionary-staminal-caren.ngrok-free.dev';
const DEFAULT_DEV_BACKEND_PORT = '8000';

const sanitizeUrl = (url?: string) => (typeof url === 'string' ? url.trim().replace(/\/+$/, '') : '');

const pickFirstDefined = (...values: (string | undefined)[]) => values.find(value => typeof value === 'string' && value.trim().length > 0)?.trim() ?? '';

const sanitizePort = (value?: string) => {
    if (!value) {
        return '';
    }

    const parsed = parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? String(parsed) : '';
};

const isLocalLikeHost = (hostname: string) => {
    if (!hostname) {
        return false;
    }

    const normalized = hostname.toLowerCase();
    if (normalized === 'localhost' || normalized === '127.0.0.1' || normalized === '::1') {
        return true;
    }

    if (normalized.endsWith('.local')) {
        return true;
    }

    return /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(normalized);
};

const detectRuntimeLocalNetworkApiUrl = () => {
    if (typeof window === 'undefined') {
        return '';
    }

    const hostname = window.location?.hostname;
    if (!hostname || !isLocalLikeHost(hostname)) {
        return '';
    }

    const preferredPort = sanitizePort(
        pickFirstDefined(
            env.VITE_DEV_BACKEND_PORT,
            env.VITE_BACKEND_PORT,
            env.VITE_API_PORT
        ) || DEFAULT_DEV_BACKEND_PORT
    );

    const portSuffix = preferredPort ? `:${preferredPort}` : '';
    return `http://${hostname}${portSuffix}`;
};

const resolveApiBaseUrl = () => {
    const envUrl = pickFirstDefined(
        sanitizeUrl(env.VITE_API_BASE_URL),
        sanitizeUrl(env.VITE_API_URL),
        sanitizeUrl(env.VITE_BACKEND_URL),
        sanitizeUrl(env.VITE_BACKEND_API_URL),
        sanitizeUrl(env.VITE_API)
    );

    if (envUrl) {
        return envUrl;
    }

    if (isDevelopment) {
        const runtimeLocalUrl = detectRuntimeLocalNetworkApiUrl();
        if (runtimeLocalUrl) {
            console.log('🔁 Utilizando backend local detectado via hostname:', runtimeLocalUrl);
            return runtimeLocalUrl;
        }
    } else {
        console.warn('⚠️ Nenhuma variável VITE_API_* definida. Usando fallback padrão.');
    }

    const prodFallback = [LEGACY_NGROK_API, DEFAULT_PROD_API].find(Boolean) ?? DEFAULT_DEV_API;
    return isDevelopment ? DEFAULT_DEV_API : prodFallback;
};

const ensureWebSocketScheme = (url: string) => {
    if (url.startsWith('wss://') || url.startsWith('ws://')) {
        return url;
    }
    if (url.startsWith('https://')) {
        return url.replace('https://', 'wss://');
    }
    if (url.startsWith('http://')) {
        return url.replace('http://', 'ws://');
    }
    return isDevelopment ? 'ws://localhost:8000' : `wss://${LEGACY_NGROK_API.replace('https://', '')}`;
};

const resolveWsBaseUrl = (apiUrl: string) => {
    const envWs = pickFirstDefined(
        sanitizeUrl(env.VITE_WS_BASE_URL),
        sanitizeUrl(env.VITE_WS_URL),
        sanitizeUrl(env.VITE_BACKEND_WS_URL)
    );

    if (envWs) {
        return envWs;
    }

    if (!isDevelopment) {
        console.warn('⚠️ Nenhuma variável VITE_WS_* definida. Derivando URL do WebSocket a partir da API.');
    }

    const wsFallbackBase = apiUrl || LEGACY_NGROK_API || DEFAULT_PROD_API;
    return ensureWebSocketScheme(wsFallbackBase);
};

export const API_BASE_URL = resolveApiBaseUrl();
export const WS_BASE_URL = resolveWsBaseUrl(API_BASE_URL);

export const config = {
    apiUrl: API_BASE_URL,
    wsUrl: WS_BASE_URL,
    environment: isDevelopment ? 'development' : 'production',
    isDevelopment,
};

console.log('🔧 Orbis Config:', {
    apiUrl: API_BASE_URL,
    wsUrl: WS_BASE_URL,
    environment: isDevelopment ? 'development' : 'production',
    mode: env.MODE,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A'
});

export default config;
