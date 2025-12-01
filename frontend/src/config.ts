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

const sanitizeUrl = (url?: string) => (typeof url === 'string' ? url.trim().replace(/\/+$/, '') : '');

const pickFirstDefined = (...values: string[]) => values.find(Boolean) ?? '';

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

    if (!isDevelopment) {
        console.warn('⚠️ Nenhuma variável VITE_API_* definida. Usando fallback padrão.');
    }

    const prodFallback = [DEFAULT_PROD_API, LEGACY_NGROK_API].find(Boolean) ?? DEFAULT_DEV_API;
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
    return isDevelopment ? 'ws://localhost:8000' : 'wss://orbis-backend.pella.app';
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

    const wsFallbackBase = apiUrl || DEFAULT_PROD_API || LEGACY_NGROK_API;
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
