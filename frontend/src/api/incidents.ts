import client from "./client";
import type {
  AnalyticsSummary,
  Incident,
  IncidentCategory,
  IncidentComment,
  IncidentMediaItem,
  Paginated,
  TimelineEvent,
  Ward,
} from "@/types";

export interface IncidentFilters {
  status?: string[];
  severity?: string;
  category?: string;
  department?: string;
  ward?: string;
  q?: string;
  overdue?: string;
  sla_state?: string;
  emergency?: string;
  created_after?: string;
  created_before?: string;
  page?: number;
  page_size?: number;
  ordering?: string;
}

export function toQuery(filters: IncidentFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === "") return;
    if (Array.isArray(value)) value.forEach((v) => params.append("status", v));
    else params.set(key, String(value));
  });
  return params.toString();
}

export const exportCsv = async (): Promise<void> => {
  const { data } = await client.get("/analytics/export.csv/", {
    responseType: "blob",
  });
  const url = URL.createObjectURL(data as unknown as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "safecity-analytics.csv";
  link.click();
  URL.revokeObjectURL(url);
};

export const exportIncidentPdf = async (id: string): Promise<void> => {
  const { data } = await client.get(`/incidents/${id}/export/pdf/`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(data as unknown as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `safecity-incident-${id}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
};

export const exportIncidentCsv = async (filters: IncidentFilters = {}): Promise<void> => {
  const { data } = await client.get(`/incidents/export/csv/?${toQuery(filters)}`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(data as unknown as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "safecity-incidents.csv";
  link.click();
  URL.revokeObjectURL(url);
};

export const incidentsApi = {
  list: async (filters: IncidentFilters = {}): Promise<Paginated<Incident>> => {
    const { data } = await client.get(`/incidents/?${toQuery(filters)}`);
    return data;
  },
  get: async (id: string): Promise<Incident> => {
    const { data } = await client.get(`/incidents/${id}/`);
    return data;
  },
  create: async (payload: Record<string, unknown>): Promise<Incident> => {
    const { data } = await client.post("/incidents/", payload);
    return data;
  },
  changeStatus: async (
    id: string,
    status: string,
    note = "",
    resolutionSummary = "",
  ): Promise<Incident> => {
    const { data } = await client.post(`/incidents/${id}/status/`, {
      status,
      note,
      resolution_summary: resolutionSummary,
    });
    return data;
  },
  assign: async (id: string, payload: { assignee_id?: string; auto?: boolean; note?: string }) => {
    const { data } = await client.post(`/incidents/${id}/assign/`, payload);
    return data;
  },
  escalate: async (id: string, level: string, reason: string) => {
    const { data } = await client.post(`/incidents/${id}/escalate/`, { level, reason });
    return data;
  },
  merge: async (id: string, parentId: string) => {
    const { data } = await client.post(`/incidents/${id}/merge/`, { parent_id: parentId });
    return data;
  },
  reopen: async (id: string, reason: string) => {
    const { data } = await client.post(`/incidents/${id}/reopen/`, { reason });
    return data;
  },
  confirm: async (id: string, payload: { rating?: number; comment?: string }) => {
    const { data } = await client.post(`/incidents/${id}/confirm/`, payload);
    return data;
  },
  timeline: async (id: string): Promise<TimelineEvent[]> => {
    const { data } = await client.get(`/incidents/${id}/timeline/`);
    return data;
  },
  comments: async (id: string): Promise<IncidentComment[]> => {
    const { data } = await client.get(`/incidents/${id}/comments/`);
    return data;
  },
  addComment: async (id: string, body: string, isInternal = false, mediaId?: string) => {
    const { data } = await client.post(`/incidents/${id}/comments/`, {
      body,
      is_internal: isInternal,
      media_id: mediaId,
    });
    return data;
  },
  media: async (id: string): Promise<IncidentMediaItem[]> => {
    const { data } = await client.get(`/incidents/media/?incident=${id}`);
    return Array.isArray(data) ? data : data.results;
  },
  uploadMedia: async (id: string, file: File): Promise<IncidentMediaItem> => {
    const payload = new FormData();
    payload.append("incident", id);
    payload.append("file", file);
    const { data } = await client.post("/incidents/media/", payload, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
  similar: async (id: string) => {
    const { data } = await client.get(`/incidents/${id}/similar/`);
    return data as Array<{
      id: string;
      reference_number: string;
      title: string;
      distance_m: number;
      created_at: string;
    }>;
  },
  duplicatesCheck: async (payload: {
    latitude: number;
    longitude: number;
    category_id: string;
  }) => {
    const { data } = await client.post("/incidents/duplicates/check/", payload);
    return data as {
      has_duplicates: boolean;
      matches: Array<{
        id: string;
        reference_number: string;
        title: string;
        distance_m: number;
        status: string;
      }>;
    };
  },
  track: async (reference: string): Promise<Incident> => {
    const { data } = await client.get(`/incidents/track/${reference}/`);
    return data;
  },
exportCsv,
   exportIncidentPdf,
   exportIncidentCsv,
};

export const referenceDataApi = {
  categories: async (): Promise<IncidentCategory[]> => {
    const { data } = await client.get("/categories/");
    return Array.isArray(data) ? data : data.results;
  },
  wards: async (): Promise<Ward[]> => {
    const { data } = await client.get("/wards/");
    return Array.isArray(data) ? data : data.results;
  },
};

export const analyticsApi = {
  summary: async (days = 30): Promise<AnalyticsSummary> => {
    const { data } = await client.get(`/analytics/summary/?days=${days}`);
    return data;
  },
  trends: async (days = 30) => {
    const { data } = await client.get(`/analytics/trends/?days=${days}`);
    return data as Array<{ date: string; total: number; resolved: number }>;
  },
  byDimension: async (dimension: string, days = 30) => {
    const { data } = await client.get(`/analytics/by-${dimension}/?days=${days}`);
    return data as Array<{ name: string; total: number; resolved: number; sla_breached: number }>;
  },
};

export interface GeocodeResult {
  place_id: number;
  lat: number;
  lon: number;
  display_name: string;
  type: string;
  class: string;
  address: Record<string, string>;
}

export interface ReverseGeocodeResult {
  lat: number;
  lon: number;
  display_name: string;
  address: Record<string, string>;
}

export const geocodeApi = {
  search: async (query: string, limit = 5): Promise<GeocodeResult[]> => {
    if (!query.trim()) return [];
    const params = new URLSearchParams({ q: query, limit: String(limit), countrycodes: "in" });
    const { data } = await client.get(`/geocode/search/?${params.toString()}`);
    return data.results || [];
  },
  reverse: async (lat: number, lon: number): Promise<ReverseGeocodeResult> => {
    const params = new URLSearchParams({ lat: String(lat), lon: String(lon), zoom: "18" });
    const { data } = await client.get(`/geocode/reverse/?${params.toString()}`);
    return data;
  },
};
