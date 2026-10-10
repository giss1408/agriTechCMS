// Mirrors apps/backend/app/schemas.py. Decimals arrive as strings.

export type Role = "super_admin" | "admin" | "collector";

export type Me = {
  id: string;
  name: string;
  phone: string;
  role: Role;
  cooperative_id: string;
  cooperative: { id: string; name: string; code: string };
  permissions: string[];
};

export type User = { id: string; name: string; phone: string; role: Role; is_active: boolean; last_seen_at: string | null };

export type Geometry = { type: "Point"; coordinates: [number, number] } | { type: "Polygon"; coordinates: [number, number][][] };

export type Parcel = {
  id: string;
  producer_id: string;
  name: string | null;
  crop: string;
  area_hectares: string | null;
  measured_area_hectares: string | null;
  geometry: Geometry | null;
  planted_year: number | null;
  deforestation_status: "unchecked" | "clear" | "flagged";
  eudr_issues: string[];
};

export type Producer = {
  id: string;
  code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  cin_number: string | null;
  gender: string | null;
  birth_year: number | null;
  zone_id: string | null;
  zone_name: string | null;
  membership_date: string | null;
  status: "active" | "inactive";
  momo_operator: string | null;
  momo_account: string | null;
  notes: string | null;
  qr_payload: string;
  parcels: Parcel[];
};

export type Balance = {
  campaign: string;
  total_delivered_kg: string;
  total_earned: number;
  total_paid: number;
  balance_due: number;
  outstanding_advances: number;
  net_payable: number;
  pending_validation_amount: number;
  last_delivery: string | null;
};

export type Advance = { id: string; amount: number; remaining: number; reason: string | null; given_at: string };

export type CollectionStatus = "pending_validation" | "validated" | "rejected" | "paid" | "cancelled";

export type Collection = {
  id: string;
  reference: string;
  producer_id: string;
  producer_name: string;
  producer_code: string;
  collector_id: string;
  collector_name: string;
  product: string;
  quality: string;
  weight_kg: string;
  moisture_percent: string | null;
  unit_price: number;
  amount: number;
  status: CollectionStatus;
  collected_at: string;
  clock_offset_seconds: number;
  gps_lat: number | null;
  gps_lng: number | null;
  notes: string | null;
  sync_source: string;
  rejection_reason: string | null;
  lot_id: string | null;
  payment_id: string | null;
};

export type Totals = { count: number; weight_kg: string; amount: number };

export type Lot = {
  id: string;
  reference: string;
  product: string;
  quality: string | null;
  status: "open" | "sealed" | "shipped";
  total_weight_kg: string;
  collections_count: number;
  bags_count: number | null;
  buyer_name: string | null;
  destination: string | null;
  notes: string | null;
  sealed_at: string | null;
  shipped_at: string | null;
  trace_url: string | null;
  created_at: string;
};

export type Payable = {
  producer_id: string;
  producer_name: string;
  producer_code: string;
  momo_operator: string | null;
  momo_account: string | null;
  collections_count: number;
  gross_amount: number;
  outstanding_advances: number;
  net_amount: number;
  oldest_collection_at: string;
};

export type Payment = {
  id: string;
  batch_id: string;
  producer_id: string;
  producer_name: string;
  gross_amount: number;
  advance_deduction: number;
  amount: number;
  operator: string | null;
  account: string | null;
  status: "initiated" | "processing" | "success" | "failed" | "cancelled";
  failure_reason: string | null;
  attempts: number;
  paid_at: string | null;
  created_at: string;
};

export type Price = { id: string; product: string; quality: string; price_per_kg: number; effective_from: string; effective_to: string | null };
export type Zone = { id: string; name: string };
export type Device = {
  id: string;
  user_name: string;
  app_version: string | null;
  last_push_at: string | null;
  last_pull_at: string | null;
  last_clock_offset_seconds: number;
  pending_on_device: number;
};

export type IssueStatus = "open" | "in_progress" | "resolved";
export type Issue = {
  id: string;
  reference: string;
  source: "web" | "mobile" | "ussd" | "public";
  category: "app_bug" | "sync" | "data_error" | "payment" | "account" | "other";
  message: string;
  status: IssueStatus;
  reporter_name: string | null;
  reporter_phone: string | null;
  collection_id: string | null;
  collection_reference: string | null;
  producer_id: string | null;
  producer_name: string | null;
  lot_id: string | null;
  lot_reference: string | null;
  context: Record<string, unknown>;
  resolution_note: string | null;
  resolved_at: string | null;
  created_at: string;
};

export type Alert = { level: "info" | "warning" | "danger"; code: string; count: number; message: string; link: string };

export type Dashboard = {
  campaign: string;
  today: { count: number; weight_kg: number; amount: number };
  campaign_totals: { count: number; weight_kg: number; amount: number };
  amount_to_pay: number;
  pending_validation: number;
  open_lots: number;
  producers: { active: number; geolocated: number };
  series_7d: { date: string; count: number; weight_kg: number }[];
  top_collectors: { id: string; name: string; count: number; weight_kg: number }[];
  alerts: Alert[];
};

export type TraceProducer = {
  code: string;
  name: string;
  weight_kg: string;
  collections: number;
  eudr_ready: boolean;
  parcels: { id: string; area_hectares: number | null; geometry_type: string | null; deforestation_status: string; eudr_issues: string[] }[];
};

export type Trace = {
  lot: Lot;
  cooperative: { name: string; region: string | null; code: string };
  summary: {
    producers: number;
    parcels: number;
    parcels_eudr_ready: number;
    producers_without_parcel: number;
    eudr_ready: boolean;
    first_collection_at: string | null;
    last_collection_at: string | null;
  };
  producers: TraceProducer[];
  geojson: { type: "FeatureCollection"; features: { type: "Feature"; geometry: Geometry; properties: Record<string, unknown> }[] };
};
