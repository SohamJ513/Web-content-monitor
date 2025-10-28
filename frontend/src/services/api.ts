// frontend/src/services/api.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ✅ Response interceptor for error normalization
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.detail) {
      if (Array.isArray(error.response.data.detail)) {
        error.response.data.detail = error.response.data.detail
          .map((err: any) => err.msg || JSON.stringify(err))
          .join(', ');
      } else if (typeof error.response.data.detail === 'object') {
        error.response.data.detail = JSON.stringify(error.response.data.detail);
      }
    }
    return Promise.reject(error);
  }
);

// ✅ Request interceptor for auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ---------------- Types ----------------
export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface TrackedPage {
  id: string;
  user_id: string;
  url: string;
  display_name: string | null;
  check_interval_minutes: number;
  is_active: boolean;
  created_at: string;
  last_checked: string | null;
  last_change_detected: string | null;
  current_version_id: string | null;
}

export interface PageVersion {
  id: string;
  page_id: string;
  timestamp: string;
  text_content: string;
  metadata: {
    url: string;
    content_length: number;
    word_count: number;
    fetched_at: string; // ✅ Fixed field name to match backend
  };
}

export interface ChangeLog {
  id: string;
  page_id: string;
  user_id: string;
  type: string;
  timestamp: string;
  description: string | null;
  semantic_similarity_score: number | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface CrawlResponse {
  status: string;
  url: string;
  content_length: number;
  content_preview: string | null;
  full_content: string;
}

export interface CrawlPageResponse {
  status: string;
  page_id: string;
  url: string;
  version_id: string;
  change_detected: boolean;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  scheduler_running: boolean;
}

// ---------------- Auth API ----------------
export const authAPI = {
  register: (userData: { email: string; password: string }) =>
    api.post<User>('/auth/register', userData),

  login: (credentials: { username: string; password: string }) => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    return api.post<LoginResponse>('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
};

// ---------------- Pages API ----------------
export const pagesAPI = {
  getAll: () => api.get<TrackedPage[]>('/pages'),
  
  getOne: (id: string) => api.get<TrackedPage>(`/pages/${id}`),
  
  create: (pageData: { 
    url: string; 
    display_name?: string; 
    check_interval_minutes?: number 
  }) => api.post<TrackedPage>('/pages', pageData),
  
  // ✅ Note: Update/Delete endpoints don't exist in your backend main.py
  // Uncomment these when you add them to your FastAPI backend
  // update: (id: string, pageData: Partial<TrackedPage>) =>
  //   api.put<TrackedPage>(`/pages/${id}`, pageData),
  // delete: (id: string) => api.delete(`/pages/${id}`),
  
  getVersions: (pageId: string) => api.get<PageVersion[]>(`/pages/${pageId}/versions`),
};

// ---------------- Change Logs API ----------------
export const changesAPI = {
  getAll: () => api.get<ChangeLog[]>('/changes'),
  // ✅ Added change logs API that matches your backend
};

// ---------------- Crawl API ----------------
export const crawlAPI = {
  // ✅ Manual crawl by URL (query parameter)
  crawlUrl: (url: string) => 
    api.post<CrawlResponse>('/crawl', null, { 
      params: { url } 
    }),
  
  // ✅ Crawl tracked page by ID
  crawlPage: (pageId: string) => 
    api.post<CrawlPageResponse>(`/crawl/${pageId}`),
};

// ---------------- Health API ----------------
export const healthAPI = {
  check: () => api.get<HealthResponse>('/health'),
};

// ---------------- Utility Functions ----------------
export const formatDate = (dateString: string | null): string => {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleString();
};

export const formatTimeAgo = (dateString: string | null): string => {
  if (!dateString) return 'Never';
  
  const now = new Date();
  const date = new Date(dateString);
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
  return `${Math.floor(diffInSeconds / 86400)} days ago`;
};

export const getStatusColor = (page: TrackedPage): string => {
  if (!page.is_active) return 'gray';
  if (page.last_change_detected) return 'green';
  if (page.last_checked) return 'blue';
  return 'yellow';
};

export const getStatusText = (page: TrackedPage): string => {
  if (!page.is_active) return 'Inactive';
  if (page.last_change_detected) return 'Changed';
  if (page.last_checked) return 'Monitored';
  return 'Pending';
};

// ✅ Token management utilities
export const tokenUtils = {
  getToken: (): string | null => localStorage.getItem('token'),
  
  setToken: (token: string): void => {
    localStorage.setItem('token', token);
  },
  
  removeToken: (): void => {
    localStorage.removeItem('token');
  },
  
  isTokenValid: (): boolean => {
    const token = localStorage.getItem('token');
    if (!token) return false;
    
    try {
      // Basic JWT structure check (doesn't verify signature)
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  },
};

export default api;