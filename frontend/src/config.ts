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

const isDevelopment = import.meta.env.MODE === 'development';

// ⚠️ ATENÇÃO: Após fazer deploy do backend no Pella, 
// cole a URL aqui substituindo 'SEU_BACKEND_URL'
const PRODUCTION_BACKEND_URL = 'SEU_BACKEND_URL'; // Ex: https://orbis-backend.pella.app

export const API_BASE_URL = isDevelopment
    ? 'http://localhost:8000'
    : PRODUCTION_BACKEND_URL;

export const WS_BASE_URL = isDevelopment
    ? 'ws://localhost:8000'
    : PRODUCTION_BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

export const config = {
    apiUrl: API_BASE_URL,
    wsUrl: WS_BASE_URL,
    environment: isDevelopment ? 'development' : 'production',
    isDevelopment,
};

// Log para debug (apenas em desenvolvimento)
if (isDevelopment) {
    console.log('🔧 Config:', config);
}

export default config;
