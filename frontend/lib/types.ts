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
  ingestion_failed?: boolean;
  ingestion_no_content?: boolean;
  ingestion_error?: string | null;
}

export type BrandVoiceProfileStatus = "ready" | "analyzing" | "incomplete";

export interface ClientListItem {
  id: string;
  name: string;
  website_url: string | null;
  brand_voice_profile_status: BrandVoiceProfileStatus;
  campaign_count: number;
  brand_voice_profile?: BrandVoiceProfile | null;
}

export interface ClientListResponse {
  clients: ClientListItem[];
  plan_at_limit: boolean;
  plan_tier: string;
  client_limit: number;
}

export interface BrandVoiceCadence {
  avg_sentence_length: number;
  variation_pattern: string;
  paragraph_structure: string;
}

export interface BrandVoiceProfile {
  tone: string[];
  cadence: BrandVoiceCadence;
  banned_jargon: string[];
  target_audience?: string | null;
}

export interface QuestionnairePayload {
  tone_sliders: {
    formal_casual: number;
    professional_friendly: number;
    concise_elaborate: number;
  };
  sample_texts: string[];
  reference_urls: string[];
}

export interface PublishJobInfo {
  id: string;
  attempt_count: number;
  error_details: string | null;
  status: string;
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
  github_pr_url: string | null;
  created_at: string;
  updated_at: string;
  publish_job?: PublishJobInfo | null;
}

export interface VoiceScore {
  tone_score: number;
  cadence_score: number;
  jargon_violations: number;
  seo_bluf_present?: boolean;
  seo_h2_count?: number;
  seo_faq_present?: boolean;
  seo_fluff_detected?: boolean;
  tags?: string[];
}

export interface CampaignCreate {
  client_id: string;
  brain_dump: string;
  target_keyword?: string | null;
  target_audience?: string | null;
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

export interface GitHubDetectionResult {
  detected_framework: string;
  publish_path: string;
  confidence: "high" | "medium" | "low";
  signals: string[];
  candidates: Array<{ framework: string; publish_path: string; signals: string[] }>;
}

export interface PlatformConnectionStatus {
  platform: "wordpress" | "webflow" | "x" | "linkedin" | "github_pages";
  connected: boolean;
  account_identifier?: string;
  connected_via?: "wordpress-com";
  github_detection?: GitHubDetectionResult | null;
  direct_commit_default?: boolean;
}

export interface ConnectionCreatePayload {
  platform: string;
  // WordPress
  site_url?: string;
  credential?: string;
  username?: string;
  // Webflow
  token?: string;
  collection_id?: string;
}

export interface CampaignListResponse {
  items: Campaign[];
  total: number;
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

export type SubscriptionInfo = SubscriptionResponse;

export interface DeliveryToken {
  id: string;
  name: string;
  token_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}

export interface DeliveryTokenListResponse {
  items: DeliveryToken[];
}

export interface DeliveryTokenCreateResponse {
  id: string;
  name: string;
  token_prefix: string;
  created_at: string;
  token: string;
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

// ── Article types ────────────────────────────────────────────────────────────

export type ArticleStatus = "published" | "hidden";

export interface ArticleListItem {
  id: string;
  slug: string;
  title: string;
  status: ArticleStatus;
  published_at: string;
  updated_at: string;
}

export interface ArticleListResponse {
  items: ArticleListItem[];
  total: number;
}

export interface Article {
  id: string;
  client_id: string;
  campaign_id: string | null;
  slug: string;
  title: string;
  html: string;
  excerpt: string | null;
  meta_description: string | null;
  featured_image_url: string | null;
  author: string | null;
  tags: string[] | null;
  category: string | null;
  status: ArticleStatus;
  reading_time_minutes: number;
  published_at: string;
  created_at: string;
  updated_at: string;
}

export interface RevisionListItem {
  revision_number: number;
  source: "initial" | "edit" | "restore";
  created_at: string;
}

export interface RevisionListResponse {
  items: RevisionListItem[];
}

export interface RevisionDetail {
  revision_number: number;
  title: string;
  html: string;
  excerpt: string | null;
  meta_description: string | null;
  tags: string[] | null;
  category: string | null;
  author: string | null;
  source: "initial" | "edit" | "restore";
  created_at: string;
}

export interface PublishHeadlessResponse {
  article_id: string;
  slug: string;
  status: string;
}
