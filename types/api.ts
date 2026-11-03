export interface OptionalMetadata {
  age?: string;
  bodyLocation?: string;
  duration?: string;
  symptoms?: string;
}

export interface ImageQualityReport {
  status: 'good' | 'warning' | 'unsuitable';
  suitable: boolean;
  warnings: string[];
  reasons: string[];
  metrics: Record<string, number>;
}

export interface Prediction {
  visual_category: string;
  confidence: number;
}

export interface ClassProbability {
  category: string;
  probability: number;
}

export interface EducationalRecommendation {
  title: string;
  information: string;
  general_guidance: string[];
  care_notice: string;
  limitation: string;
}

export interface AnalysisResponse {
  analysis_id: number;
  created_at: string;
  image_retained: boolean;
  quality: ImageQualityReport;
  model_status: 'available' | 'unavailable';
  model_message: string | null;
  uncertainty_status: 'confident' | 'low_confidence' | 'model_unavailable' | 'image_unsuitable';
  prediction: Prediction | null;
  probabilities: ClassProbability[];
  gradcam_data_url: string | null;
  gradcam_available: boolean;
  gradcam_message: string | null;
  recommendation: EducationalRecommendation;
  disclaimer: string;
}

export interface HealthResponse {
  status: 'ok';
  model_available: boolean;
  image_retention_allowed: boolean;
  model_version: string | null;
  model_message: string;
}

export interface HistoryItem {
  id: number;
  created_at: string;
  predicted_category: string | null;
  confidence: number | null;
  quality_status: string;
  model_version: string | null;
  image_retained: boolean;
}
