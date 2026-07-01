export type CampaignStatus =
  | "pending_approval"
  | "approved"
  | "published"
  | "rejected"
  | "failed";

export type PlanTier = "starter" | "growth" | "agency";

export type Platform = "wordpress" | "webflow" | "x" | "linkedin";

export interface User {
  id: string;
  email: string;
  google_sub: string | null;
  stripe_customer_id: string | null;
  verified: boolean;
  created_at: string;
}

export interface Client {
  id: string;
  user_id: string;
  name: string;
  website_url: string | null;
  brand_voice_profile: BrandVoiceProfile | null;
  created_at: string;
  updated_at: string;
}

export interface ClientResponse {
  id: string;
  name: string;
  website_url: string | null;
  brand_voice_profile: BrandVoiceProfile | null;
  job_id: string | null;
  campaign_count: number;
  created_at: string;
}

export type BrandVoiceProfileStatus = "ready" | "analyzing" | "incomplete";

export interface ClientListItem {
  id: string;
  name: string;
  website_url: string | null;
  brand_voice_profile_status: BrandVoiceProfileStatus;
  campaign_count: number;
}

export interface ClientListResponse {
  clients: ClientListItem[];
  plan_at_limit: boolean;
  plan_tier: string;
  client_limit: number;
}

export interface BrandVoiceProfile {
  tone: string;
  cadence: string;
  banned_jargon: string[];
  sample_phrases: string[];
  voice_summary: string;
}

export interface Campaign {
  id: string;
  client_id: string;
  brain_dump: string;
  blog_html: string | null;
  x_post: string | null;
  linkedin_post: string | null;
  image_url: string | null;
  status: CampaignStatus;
  voice_score: VoiceScore | null;
  rejection_reason: string | null;
  scheduled_at: string | null;
  image_regen_count: number;
  created_at: string;
  updated_at: string;
}

export interface VoiceScore {
  score: number;
  rationale: string;
  flags: string[];
}

export interface Job {
  id: string;
  campaign_id: string | null;
  client_id: string | null;
  job_type: string;
  status: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  attempt_count: number;
  error_details: string | null;
  created_at: string;
}

export interface FileItem {
  filename: string;
  size: number;
}

export interface FileUploadedItem {
  filename: string;
  size: number;
  path: string;
}

export interface FileUploadError {
  filename: string;
  error: string;
}

export interface FileUploadResponse {
  uploaded: FileUploadedItem[];
  errors: FileUploadError[];
}

export interface FileListResponse {
  files: FileItem[];
  count: number;
  limit: number;
}

export interface DashboardStats {
  total_campaigns: number;
  pending_approval: number;
  published_this_month: number;
  total_clients: number;
}

export interface PlanLimits {
  clients: number;
  campaigns: number;
  image_gens: number;
}

export interface SubscriptionResponse {
  plan_tier: PlanTier;
  status: string;
  campaigns_used: number;
  clients_count: number;
  image_gen_used: number;
  billing_cycle_start: string;
  billing_cycle_end: string;
  plan_limits: PlanLimits;
}

export interface Subscription {
  id: string;
  user_id: string;
  stripe_sub_id: string;
  plan_tier: PlanTier;
  status: string;
  campaigns_used: number;
  clients_count: number;
  image_gen_used: number;
  billing_cycle_start: string;
  billing_cycle_end: string;
  created_at: string;
  updated_at: string;
}
