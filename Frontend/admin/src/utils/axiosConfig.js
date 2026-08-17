// src/utils/axiosConfig.js
import axios from "axios";

// Admin API Base URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json",
  },
  timeout: 30000,
});

// ============================================================================
// TOKEN REFRESH HANDLING
// ============================================================================

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error) => {
  failedQueue.forEach(prom => error ? prom.reject(error) : prom.resolve());
  failedQueue = [];
};

// ============================================================================
// REFRESH CALLBACKS
// ============================================================================

let refreshDashboardFn = null;
let refreshInventoryFn = null;
let refreshRecommendationsFn = null;
let refreshForecastFn = null;
let refreshScenariosFn = null;
let refreshUsersFn = null;

export const setRefreshDashboard = (fn) => { refreshDashboardFn = fn; };
export const setRefreshInventory = (fn) => { refreshInventoryFn = fn; };
export const setRefreshRecommendations = (fn) => { refreshRecommendationsFn = fn; };
export const setRefreshForecast = (fn) => { refreshForecastFn = fn; };
export const setRefreshScenarios = (fn) => { refreshScenariosFn = fn; };
export const setRefreshUsers = (fn) => { refreshUsersFn = fn; };

// ============================================================================
// TRIGGER REFRESH
// ============================================================================

const triggerRefresh = (url) => {
  setTimeout(() => {
    if (url.includes('/inventory/') && refreshInventoryFn) {
      refreshInventoryFn();
    } else if (url.includes('/recommendations/') && refreshRecommendationsFn) {
      refreshRecommendationsFn();
    } else if (url.includes('/forecast/') && refreshForecastFn) {
      refreshForecastFn();
    } else if (url.includes('/scenarios/') && refreshScenariosFn) {
      refreshScenariosFn();
    } else if (url.includes('/users/') && refreshUsersFn) {
      refreshUsersFn();
    } else if (refreshDashboardFn) {
      refreshDashboardFn();
    }
  }, 300);
};

// ============================================================================
// REQUEST INTERCEPTOR - Add this first
// ============================================================================

api.interceptors.request.use(
  (config) => {
    // Don't add token for auth endpoints
    const isAuthEndpoint = 
      config.url?.includes('/auth/') ||
      config.url?.includes('/login') ||
      config.url?.includes('/logout') ||
      config.url?.includes('/refresh') ||
      config.url?.includes('/verify') ||
      config.url?.includes('/forgot-password') ||
      config.url?.includes('/resend-otp') ||
      config.url?.includes('/verify-otp') ||
      config.url?.includes('/reset-password');

    if (!isAuthEndpoint) {
      const token = localStorage.getItem('admin_access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// ============================================================================
// RESPONSE INTERCEPTOR
// ============================================================================

api.interceptors.response.use(
  (response) => {
    const method = response.config.method?.toLowerCase();
    const url = response.config.url || '';

    const skipRefresh =
      url.includes('/admin/') ||
      url.includes('/auth/') ||
      url.includes('/login') ||
      url.includes('/logout') ||
      url.includes('/refresh') ||
      url.includes('/verify') ||
      url.includes('/forgot-password') ||
      url.includes('/resend-otp') ||
      url.includes('/verify-otp') ||
      url.includes('/reset-password');

    if (['post', 'put', 'patch', 'delete'].includes(method) && !skipRefresh) {
      triggerRefresh(url);
    }

    return response;
  },

  async (error) => {
    const originalRequest = error.config;

    // Don't attempt refresh for auth endpoints
    const isAuthEndpoint =
      originalRequest.url?.includes('/admin/') ||
      originalRequest.url?.includes('/auth/') ||
      originalRequest.url?.includes('/login') ||
      originalRequest.url?.includes('/logout') ||
      originalRequest.url?.includes('/refresh') ||
      originalRequest.url?.includes('/verify') ||
      originalRequest.url?.includes('/forgot-password') ||
      originalRequest.url?.includes('/resend-otp') ||
      originalRequest.url?.includes('/verify-otp') ||
      originalRequest.url?.includes('/reset-password');

    if (isAuthEndpoint) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => api(originalRequest)).catch(err => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await api.post("/admin/refresh");
        processQueue(null);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        localStorage.removeItem('admin_access_token');
        window.location.href = "/admin/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (error.response?.status === 403) {
      if (error.response?.data?.detail?.includes("permission")) {
        console.error("Permission denied:", error.response.data.detail);
      } else {
        localStorage.removeItem('admin_access_token');
        window.location.href = "/admin/login";
      }
    }

    return Promise.reject(error);
  }
);

// ============================================================================
// AUTH HELPERS
// ============================================================================

export const clearRefreshCallbacks = () => {
  refreshDashboardFn = null;
  refreshInventoryFn = null;
  refreshRecommendationsFn = null;
  refreshForecastFn = null;
  refreshScenariosFn = null;
  refreshUsersFn = null;
};

export const isAuthenticated = async () => {
  try {
    const response = await api.get("/admin/verify");
    return response.status === 200;
  } catch {
    return false;
  }
};

export const logout = async () => {
  try {
    await api.post("/admin/logout");
    localStorage.removeItem('admin_access_token');
  } catch (error) {
    console.error("Logout error:", error);
  } finally {
    clearRefreshCallbacks();
    window.location.href = "/admin/login";
  }
};

export const loginUser = async (email, password) => {
  try {
    const response = await api.post("/auth/login", {
      email,
      password
    });
    
    if (response.data && response.data.access_token) {
      localStorage.setItem('admin_access_token', response.data.access_token);
      return response.data;
    }
    
    throw new Error("Invalid response from server");
  } catch (error) {
    throw error;
  }
};

export default api;