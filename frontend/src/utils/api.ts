/**
 * API Utilities - Centralized fetch wrapper with automatic token expiration handling
 */

/**
 * Custom fetch wrapper that automatically handles token expiration
 * When receiving a 401 Unauthorized, it logs the user out and redirects to login
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const response = await fetch(url, options);

  // Check if token expired (401 Unauthorized)
  if (response.status === 401) {
    console.warn('🔒 Token expired or invalid - Logging out...');
    
    // Clear authentication data
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    localStorage.removeItem('username');
    
    // Show notification to user
    const event = new CustomEvent('auth:expired', {
      detail: { message: 'Your session has expired. Please login again.' }
    });
    window.dispatchEvent(event);
    
    // Redirect to login after a short delay
    setTimeout(() => {
      window.location.href = '/login';
    }, 1500);
    
    // Throw error to prevent further processing
    throw new Error('Token expired - User logged out');
  }

  return response;
}

/**
 * Helper function to make authenticated API calls
 * Automatically adds Authorization header with token from localStorage
 */
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = localStorage.getItem('auth_token');
  
  if (!token) {
    console.warn('⚠️ No auth token found - Redirecting to login...');
    window.location.href = '/login';
    throw new Error('No authentication token');
  }

  const headers = new Headers(options.headers);
  headers.set('Authorization', `Bearer ${token}`);

  return apiFetch(url, {
    ...options,
    headers
  });
}

/**
 * Helper for GET requests
 */
export async function apiGet(url: string): Promise<Response> {
  return authenticatedFetch(url, { method: 'GET' });
}

/**
 * Helper for POST requests
 */
export async function apiPost(url: string, data: any): Promise<Response> {
  return authenticatedFetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
}

/**
 * Helper for PUT requests
 */
export async function apiPut(url: string, data: any): Promise<Response> {
  return authenticatedFetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
}

/**
 * Helper for DELETE requests
 */
export async function apiDelete(url: string): Promise<Response> {
  return authenticatedFetch(url, { method: 'DELETE' });
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!localStorage.getItem('auth_token');
}

/**
 * Get current user token
 */
export function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

/**
 * Logout user manually
 */
export function logout(): void {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_id');
  localStorage.removeItem('user_email');
  localStorage.removeItem('username');
  window.location.href = '/login';
}
