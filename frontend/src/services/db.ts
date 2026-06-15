import Dexie, { Table } from 'dexie';

export interface Lead {
  id?: number;
  owner: number;
  owner_name?: string;
  created_by: number;
  created_by_name?: string;
  category?: number;
  category_name?: string;
  category_other?: string;
  source?: number;
  source_name?: string;
  source_other?: string;
  client_name: string;
  contact_number?: string;
  email?: string;
  requirement?: string;
  status: string;
  follow_up_date?: string;
  notes?: string;
  assigned_to?: number;
  assigned_to_name?: string;
  lead_score?: number;
  budget?: number;
  timeline?: string;
  decision_maker?: boolean;
  converted_to_customer?: boolean;
  custom_fields?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  deleted_at?: string;
  deleted_by?: number;
  assignment_date?: string;
  syncStatus?: 'synced' | 'pending' | 'syncing' | 'error';
  syncError?: string;
}

export interface Category {
  id?: number;
  name: string;
  created_at?: string;
}

export interface Source {
  id?: number;
  name: string;
  created_at?: string;
}

export interface SyncQueue {
  id?: number;
  action: 'CREATE' | 'UPDATE' | 'DELETE';
  entity: 'lead' | 'category' | 'source' | 'owner_category' | 'owner_source';
  entityId?: number;
  data: Record<string, any>;
  timestamp: number;
  status: 'pending' | 'syncing' | 'synced' | 'error';
  error?: string;
  retryCount?: number;
}

export class LeadSyncDB extends Dexie {
  leads!: Table<Lead>;
  categories!: Table<Category>;
  sources!: Table<Source>;
  syncQueue!: Table<SyncQueue>;

  constructor() {
    super('LeadSyncCRM');
    this.version(1).stores({
      leads: '++id, owner, status, created_at, syncStatus',
      categories: '++id, name',
      sources: '++id, name',
      syncQueue: '++id, status, timestamp, entity, entityId',
    });
  }

  // Leads
  async getLeads(filters?: any) {
    let query = this.leads.where('deleted_at').equals(undefined);

    if (filters?.status) {
      query = this.leads.where('status').equals(filters.status);
    }

    if (filters?.category) {
      query = this.leads.where('category').equals(filters.category);
    }

    return query.reverse().sortBy('created_at');
  }

  async getLead(id: number) {
    return this.leads.get(id);
  }

  async addLead(lead: Lead) {
    const id = await this.leads.add(lead);
    
    // Add to sync queue
    await this.syncQueue.add({
      action: 'CREATE',
      entity: 'lead',
      data: lead,
      timestamp: Date.now(),
      status: 'pending',
    });

    return id;
  }

  async updateLead(id: number, updates: Partial<Lead>) {
    await this.leads.update(id, { ...updates, syncStatus: 'pending' });

    // Add to sync queue
    await this.syncQueue.add({
      action: 'UPDATE',
      entity: 'lead',
      entityId: id,
      data: updates,
      timestamp: Date.now(),
      status: 'pending',
    });
  }

  async deleteLead(id: number) {
    const lead = await this.leads.get(id);
    if (lead) {
      await this.leads.update(id, { deleted_at: new Date().toISOString() });

      // Add to sync queue
      await this.syncQueue.add({
        action: 'DELETE',
        entity: 'lead',
        entityId: id,
        data: { id },
        timestamp: Date.now(),
        status: 'pending',
      });
    }
  }

  // Categories
  async getCategories() {
    return this.categories.toArray();
  }

  async addCategory(category: Category) {
    const id = await this.categories.add(category);

    await this.syncQueue.add({
      action: 'CREATE',
      entity: 'category',
      data: category,
      timestamp: Date.now(),
      status: 'pending',
    });

    return id;
  }

  async updateCategory(id: number, updates: Partial<Category>) {
    await this.categories.update(id, updates);

    await this.syncQueue.add({
      action: 'UPDATE',
      entity: 'category',
      entityId: id,
      data: updates,
      timestamp: Date.now(),
      status: 'pending',
    });
  }

  async deleteCategory(id: number) {
    await this.categories.delete(id);

    await this.syncQueue.add({
      action: 'DELETE',
      entity: 'category',
      entityId: id,
      data: { id },
      timestamp: Date.now(),
      status: 'pending',
    });
  }

  // Sources
  async getSources() {
    return this.sources.toArray();
  }

  async addSource(source: Source) {
    const id = await this.sources.add(source);

    await this.syncQueue.add({
      action: 'CREATE',
      entity: 'source',
      data: source,
      timestamp: Date.now(),
      status: 'pending',
    });

    return id;
  }

  async updateSource(id: number, updates: Partial<Source>) {
    await this.sources.update(id, updates);

    await this.syncQueue.add({
      action: 'UPDATE',
      entity: 'source',
      entityId: id,
      data: updates,
      timestamp: Date.now(),
      status: 'pending',
    });
  }

  async deleteSource(id: number) {
    await this.sources.delete(id);

    await this.syncQueue.add({
      action: 'DELETE',
      entity: 'source',
      entityId: id,
      data: { id },
      timestamp: Date.now(),
      status: 'pending',
    });
  }

  // Sync Queue
  async getPendingSyncItems() {
    return this.syncQueue.where('status').equals('pending').toArray();
  }

  async markSyncItemAsProcessing(id: number) {
    await this.syncQueue.update(id, { status: 'syncing' });
  }

  async markSyncItemAsSynced(id: number) {
    await this.syncQueue.update(id, { status: 'synced' });
    await this.syncQueue.delete(id);
  }

  async markSyncItemAsError(id: number, error: string) {
    const item = await this.syncQueue.get(id);
    if (item) {
      const retryCount = (item.retryCount || 0) + 1;
      await this.syncQueue.update(id, {
        status: 'error',
        error,
        retryCount,
        timestamp: Date.now(),
      });
    }
  }

  async clearSyncQueue() {
    await this.syncQueue.clear();
  }

  async syncLeads(leads: Lead[]) {
    await this.leads.bulkPut(leads);
  }

  async syncCategories(categories: Category[]) {
    await this.categories.clear();
    await this.categories.bulkPut(categories);
  }

  async syncSources(sources: Source[]) {
    await this.sources.clear();
    await this.sources.bulkPut(sources);
  }
}

export const db = new LeadSyncDB();
