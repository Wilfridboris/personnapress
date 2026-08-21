/** Angle code to display label map -- mirrors backend/app/services/angles.py */
export const ANGLE_LABELS: Record<string, string> = {
  personal_story: "Personal story",
  lesson_learned: "Lesson learned",
  how_to: "How-to",
  data_proof: "Data proof",
  contrarian: "Contrarian take",
  myth_bust: "Myth-buster",
  prediction: "Prediction",
  engagement_q: "Question",
  quick_tip: "Quick tip",
  hot_take: "Hot take",
};

export function getAngleLabel(code: string | null | undefined): string | null {
  if (!code) return null;
  return ANGLE_LABELS[code] ?? null;
}
