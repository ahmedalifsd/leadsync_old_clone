import axios, { AxiosInstance, AxiosError } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      withCredentials: true, // Send cookies with requests
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add response interceptor to handle errors
    this.client.interceptors.response.use(
      response => response,
      error => {
        if (error.response?.status === 401) {
          // Unauthorized - user should login
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async register(username: string, email: string, password: string, passwordConfirm: string) {
    return this.client.post('/auth/register/', {
      username,
      email,
      password,
      password_confirm: passwordConfirm,
    });
  }

  async login(username: string, password: string) {
    return this.client.post('/auth/login/', { username, password });
  }

  async logout() {
    return this.client.post('/auth/logout/');
  }

  async getCurrentUser() {
    return this.client.get('/auth/user/');
  }

  async checkUsername(username: string) {
    return this.client.get('/auth/check-username/', { params: { username } });
  }

  async checkEmail(email: string) {
    return this.client.get('/auth/check-email/', { params: { email } });
  }

  async updateProfile(data: any) {
    return this.client.put('/auth/profile/', data);
  }

  async changePassword(oldPassword: string, newPassword: string, newPasswordConfirm: string) {
    return this.client.post('/auth/password/change/', {
      old_password: oldPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    });
  }

  // Leads
  async getLeads(page = 1, filters: any = {}) {
    return this.client.get('/leads/', {
      params: { page, ...filters },
    });
  }

  async getLead(id: number) {
    return this.client.get(`/leads/${id}/`);
  }

  async createLead(data: any) {
    return this.client.post('/leads/', data);
  }

  async updateLead(id: number, data: any) {
    return this.client.put(`/leads/${id}/`, data);
  }

  async partialUpdateLead(id: number, data: any) {
    return this.client.patch(`/leads/${id}/`, data);
  }

  async deleteLead(id: number) {
    return this.client.delete(`/leads/${id}/`);
  }

  async changeLeadStatus(id: number, status: string) {
    return this.client.post(`/leads/${id}/change_status/`, { status });
  }

  async assignLead(id: number, assignedToId: number) {
    return this.client.post(`/leads/${id}/assign/`, { assigned_to_id: assignedToId });
  }

  async getDeletedLeads(page = 1) {
    return this.client.get('/leads/deleted_leads/', { params: { page } });
  }

  async restoreLead(id: number) {
    return this.client.post(`/leads/${id}/restore/`);
  }

  // Categories
  async getCategories() {
    return this.client.get('/categories/');
  }

  async createCategory(name: string) {
    return this.client.post('/categories/', { name });
  }

  async updateCategory(id: number, name: string) {
    return this.client.put(`/categories/${id}/`, { name });
  }

  async deleteCategory(id: number) {
    return this.client.delete(`/categories/${id}/`);
  }

  // Sources
  async getSources() {
    return this.client.get('/sources/');
  }

  async createSource(name: string) {
    return this.client.post('/sources/', { name });
  }

  async updateSource(id: number, name: string) {
    return this.client.put(`/sources/${id}/`, { name });
  }

  async deleteSource(id: number) {
    return this.client.delete(`/sources/${id}/`);
  }

  // Owner Categories
  async getOwnerCategories() {
    return this.client.get('/owner-categories/');
  }

  async createOwnerCategory(name: string) {
    return this.client.post('/owner-categories/', { name });
  }

  async updateOwnerCategory(id: number, name: string) {
    return this.client.put(`/owner-categories/${id}/`, { name });
  }

  async deleteOwnerCategory(id: number) {
    return this.client.delete(`/owner-categories/${id}/`);
  }

  // Owner Sources
  async getOwnerSources() {
    return this.client.get('/owner-sources/');
  }

  async createOwnerSource(name: string) {
    return this.client.post('/owner-sources/', { name });
  }

  async updateOwnerSource(id: number, name: string) {
    return this.client.put(`/owner-sources/${id}/`, { name });
  }

  async deleteOwnerSource(id: number) {
    return this.client.delete(`/owner-sources/${id}/`);
  }

  // Dashboard
  async getDashboardStats() {
    return this.client.get('/dashboard/stats/');
  }

  async getLeadStatusDistribution() {
    return this.client.get('/leads/status-distribution/');
  }

  // Activity Logs
  async getActivityLogs(page = 1) {
    return this.client.get('/activity-logs/', { params: { page } });
  }

  // Users
  async getUsers() {
    return this.client.get('/auth/users/');
  }
}

export const api = new ApiClient();
