import { api } from './api';
import { db } from './db';
import type { Lead, Category, Source, SyncQueue } from './db';

let isSyncing = false;
const syncListeners: ((status: 'online' | 'offline' | 'syncing' | 'synced') => void)[] = [];

export const syncService = {
  // Listen for sync status changes
  onSyncStatusChange(listener: (status: 'online' | 'offline' | 'syncing' | 'synced') => void) {
    syncListeners.push(listener);
    return () => {
      const index = syncListeners.indexOf(listener);
      if (index > -1) syncListeners.splice(index, 1);
    };
  },

  notifySyncStatus(status: 'online' | 'offline' | 'syncing' | 'synced') {
    syncListeners.forEach(listener => listener(status));
  },

  // Initialize sync service
  async initialize() {
    // Check initial online status
    window.addEventListener('online', () => this.notifySyncStatus('online'));
    window.addEventListener('offline', () => this.notifySyncStatus('offline'));

    // Fetch initial data from API
    await this.fetchInitialData();

    // Setup sync interval (every 30 seconds if online)
    setInterval(() => {
      if (navigator.onLine && !isSyncing) {
        this.syncPendingChanges();
      }
    }, 30000);
  },

  // Fetch all data from API and cache locally
  async fetchInitialData() {
    try {
      const [leadsRes, categoriesRes, sourcesRes] = await Promise.all([
        api.getLeads(1, { page_size: 1000 }),
        api.getCategories(),
        api.getSources(),
      ]);

      // Cache data
      await db.syncLeads(leadsRes.data.results || leadsRes.data);
      await db.syncCategories(categoriesRes.data.results || categoriesRes.data);
      await db.syncSources(sourcesRes.data.results || sourcesRes.data);

      this.notifySyncStatus('synced');
    } catch (error) {
      console.error('[v0] Failed to fetch initial data:', error);
      this.notifySyncStatus('offline');
    }
  },

  // Sync pending changes with server
  async syncPendingChanges() {
    if (isSyncing || !navigator.onLine) return;

    isSyncing = true;
    this.notifySyncStatus('syncing');

    try {
      const pendingItems = await db.getPendingSyncItems();

      for (const item of pendingItems) {
        await this.processSyncItem(item);
      }

      this.notifySyncStatus('synced');
    } catch (error) {
      console.error('[v0] Sync error:', error);
      this.notifySyncStatus('offline');
    } finally {
      isSyncing = false;
    }
  },

  // Process individual sync queue item
  async processSyncItem(item: SyncQueue) {
    if (!item.id) return;

    try {
      await db.markSyncItemAsProcessing(item.id);

      switch (item.entity) {
        case 'lead':
          await this.syncLead(item);
          break;
        case 'category':
          await this.syncCategory(item);
          break;
        case 'source':
          await this.syncSource(item);
          break;
        default:
          break;
      }

      await db.markSyncItemAsSynced(item.id);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error';
      await db.markSyncItemAsError(item.id, errorMessage);
    }
  },

  // Sync lead changes
  async syncLead(item: SyncQueue) {
    switch (item.action) {
      case 'CREATE':
        const createRes = await api.createLead(item.data);
        if (item.data.id) {
          await db.leads.delete(item.data.id);
        }
        await db.leads.add(createRes.data);
        break;

      case 'UPDATE':
        if (item.entityId) {
          await api.updateLead(item.entityId, item.data);
          const updated = await api.getLead(item.entityId);
          await db.leads.put(updated.data);
        }
        break;

      case 'DELETE':
        if (item.entityId) {
          await api.deleteLead(item.entityId);
          await db.leads.delete(item.entityId);
        }
        break;
    }
  },

  // Sync category changes
  async syncCategory(item: SyncQueue) {
    switch (item.action) {
      case 'CREATE':
        const createRes = await api.createCategory(item.data.name);
        if (item.data.id) {
          await db.categories.delete(item.data.id);
        }
        await db.categories.add(createRes.data);
        break;

      case 'UPDATE':
        if (item.entityId) {
          await api.updateCategory(item.entityId, item.data.name);
          await db.updateCategory(item.entityId, item.data);
        }
        break;

      case 'DELETE':
        if (item.entityId) {
          await api.deleteCategory(item.entityId);
          await db.categories.delete(item.entityId);
        }
        break;
    }
  },

  // Sync source changes
  async syncSource(item: SyncQueue) {
    switch (item.action) {
      case 'CREATE':
        const createRes = await api.createSource(item.data.name);
        if (item.data.id) {
          await db.sources.delete(item.data.id);
        }
        await db.sources.add(createRes.data);
        break;

      case 'UPDATE':
        if (item.entityId) {
          await api.updateSource(item.entityId, item.data.name);
          await db.updateSource(item.entityId, item.data);
        }
        break;

      case 'DELETE':
        if (item.entityId) {
          await api.deleteSource(item.entityId);
          await db.sources.delete(item.entityId);
        }
        break;
    }
  },

  // Get sync status
  isSyncing() {
    return isSyncing;
  },

  isOnline() {
    return navigator.onLine;
  },
};
