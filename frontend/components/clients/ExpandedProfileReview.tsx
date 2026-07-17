"use client";

import { useState, KeyboardEvent } from "react";
import { Lock, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { TagChip } from "@/components/ui/TagChip";
import { clientsApi } from "@/lib/api";
import type { ExpandedBrandVoiceProfile } from "@/lib/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function isExpandedBVP(bvp: ExpandedBrandVoiceProfile): boolean {
  return bvp.voice_brief != null || bvp.pronoun_preference != null || bvp.formality_scale != null;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] uppercase tracking-[0.06em] text-[#555555] mb-1">{children}</p>
  );
}

interface FieldGroupProps {
  label: string;
  children: React.ReactNode;
}

function FieldGroup({ label, children }: FieldGroupProps) {
  return (
    <div className="border border-[#E5E5E5] bg-white p-6 mb-6">
      <p className="text-xs uppercase tracking-[0.06em] text-[#111111] mb-4">{label}</p>
      {children}
    </div>
  );
}

interface ChipSelectProps<T extends string> {
  options: { value: T; label: string }[];
  value: T | undefined;
  onChange?: (v: T) => void;
  readOnly: boolean;
}

function ChipSelect<T extends string>({ options, value, onChange, readOnly }: ChipSelectProps<T>) {
  if (readOnly) {
    const found = options.find((o) => o.value === value);
    return found ? (
      <span className="inline-flex items-center border border-[#E5E5E5] bg-white px-3 py-2 text-sm text-[#555555] rounded-none">
        {found.label}
      </span>
    ) : null;
  }

  return (
    <div className="flex flex-wrap gap-2" role="group">
      {options.map((o) => {
        const active = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange?.(o.value)}
            className={[
              "min-h-[44px] px-3 text-sm border rounded-none",
              "transition-colors duration-150",
              "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1",
              active
                ? "bg-[#FFF1B8] border-[#111111] text-[#111111]"
                : "bg-white border-[#E5E5E5] text-[#555555] hover:border-[#111111]",
            ].join(" ")}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

interface FormalityScaleProps {
  value: number | undefined;
  onChange?: (v: number) => void;
  readOnly: boolean;
}

function FormalityScale({ value, onChange, readOnly }: FormalityScaleProps) {
  if (readOnly) {
    return value != null ? (
      <span className="inline-flex items-center border border-[#E5E5E5] bg-white px-3 py-2 text-sm text-[#555555] rounded-none">
        {value} / 5
      </span>
    ) : null;
  }

  return (
    <div>
      <div className="flex justify-between text-[11px] text-[#555555] mb-1 uppercase tracking-[0.06em]">
        <span>Casual</span>
        <span>Formal</span>
      </div>
      <div
        className="inline-flex border border-[#E5E5E5] rounded-none"
        role="group"
        aria-label="Formality scale 1 to 5"
      >
        {[1, 2, 3, 4, 5].map((n) => {
          const active = value === n;
          return (
            <button
              key={n}
              type="button"
              aria-label={`Formality ${n} of 5`}
              aria-pressed={active}
              onClick={() => onChange?.(n)}
              className={[
                "min-h-[44px] w-12 text-sm border-r border-[#E5E5E5] last:border-r-0",
                "transition-colors duration-150",
                "focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1",
                active
                  ? "bg-[#FFF1B8] text-[#111111]"
                  : "bg-white text-[#555555] hover:bg-[#F9F9F6]",
              ].join(" ")}
            >
              {n}
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface ComputedMetricsRowProps {
  bvp: ExpandedBrandVoiceProfile;
}

const COMPUTED_LABELS: { key: keyof ExpandedBrandVoiceProfile; label: string }[] = [
  { key: "sentence_length_avg", label: "Avg sentence length" },
  { key: "sentence_rhythm", label: "Sentence rhythm" },
  { key: "paragraph_density", label: "Paragraph density" },
  { key: "contraction_frequency", label: "Contractions" },
  { key: "list_preference", label: "List use" },
];

function ComputedMetricsRow({ bvp }: ComputedMetricsRowProps) {
  const chips = COMPUTED_LABELS.filter(({ key }) => bvp[key] != null);
  if (chips.length === 0) return null;

  return (
    <FieldGroup label="Writing Metrics">
      <div className="flex items-center gap-1.5 mb-3">
        <Lock size={12} className="text-[#555555]" aria-hidden="true" />
        <span className="text-[11px] uppercase tracking-[0.06em] text-[#555555]">
          Computed from your writing -- not editable
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {chips.map(({ key, label }) => (
          <span
            key={key}
            className="inline-flex items-center gap-2 border border-[#E5E5E5] bg-[#F9F9F6] px-3 py-2 rounded-none"
          >
            <span className="text-[10px] uppercase tracking-[0.06em] text-[#555555]">{label}</span>
            <span className="text-sm text-[#111111]">{String(bvp[key])}</span>
          </span>
        ))}
      </div>
    </FieldGroup>
  );
}

interface VoiceBriefPanelProps {
  voiceBrief: string;
}

function VoiceBriefPanel({ voiceBrief }: VoiceBriefPanelProps) {
  return (
    <div className="border border-[#111111] bg-[#FFF1B8] p-6 mb-6">
      <p className="font-serif text-base font-semibold text-[#111111] mb-3">
        How PersonnaPress understands your writing
      </p>
      <p className="text-sm leading-[1.7] text-[#111111]">{voiceBrief}</p>
      <p className="mt-4 text-[11px] uppercase tracking-[0.06em] text-[#555555]">
        Regenerated automatically when you refresh your profile
      </p>
    </div>
  );
}

interface LegacyUpgradeNudgeProps {
  onRefresh?: () => void;
  refreshDisabled?: boolean;
}

function LegacyUpgradeNudge({ onRefresh, refreshDisabled }: LegacyUpgradeNudgeProps) {
  return (
    <div className="border border-[#E5E5E5] bg-white p-6 mb-6">
      <p className="text-sm text-[#555555] mb-4">
        Refresh your voice profile to unlock 17 additional dimensions including Voice Brief
        synthesis, writing patterns, and anchor phrases. Your current profile stays intact during
        the refresh.
      </p>
      {onRefresh && (
        <Button
          variant="secondary"
          type="button"
          onClick={onRefresh}
          disabled={refreshDisabled}
        >
          <RefreshCw size={16} aria-hidden="true" />
          Refresh profile
        </Button>
      )}
    </div>
  );
}

interface EditableTagListProps {
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder: string;
  label: string;
  readOnly: boolean;
}

function EditableTagList({ tags, onChange, placeholder, label, readOnly }: EditableTagListProps) {
  const [input, setInput] = useState("");

  const add = () => {
    const trimmed = input.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setInput("");
  };

  return (
    <div>
      <div className="flex flex-wrap mb-2">
        {tags.map((tag) => (
          <TagChip
            key={tag}
            label={tag}
            readOnly={readOnly}
            onRemove={() => onChange(tags.filter((t) => t !== tag))}
          />
        ))}
        {tags.length === 0 && readOnly && (
          <span className="text-sm text-[#555555]">None specified.</span>
        )}
      </div>
      {!readOnly && (
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder}
          aria-label={label}
        />
      )}
    </div>
  );
}

interface VoiceAnchorListProps {
  sentences: string[];
  onChange: (sentences: string[]) => void;
  readOnly: boolean;
}

function VoiceAnchorList({ sentences, onChange, readOnly }: VoiceAnchorListProps) {
  const [input, setInput] = useState("");
  const MAX = 5;

  const add = () => {
    const trimmed = input.trim();
    if (trimmed && sentences.length < MAX) {
      onChange([...sentences, trimmed]);
    }
    setInput("");
  };

  return (
    <div>
      <ol className="space-y-2 mb-3">
        {sentences.map((s, i) => (
          <li
            key={i}
            className="flex items-start gap-2 border border-[#E5E5E5] bg-[#F9F9F6] px-3 py-2"
          >
            <span className="font-['JetBrains_Mono'] text-xs text-[#555555] mt-0.5 shrink-0">
              {i + 1}.
            </span>
            <span className="font-['JetBrains_Mono'] text-xs text-[#111111] flex-1">{s}</span>
            {!readOnly && (
              <button
                type="button"
                aria-label={`Remove sentence ${i + 1}`}
                onClick={() => onChange(sentences.filter((_, idx) => idx !== i))}
                className="min-h-[44px] min-w-[44px] flex items-center justify-center text-[#555555] hover:text-[#111111] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1 shrink-0"
              >
                <X size={14} aria-hidden="true" />
              </button>
            )}
          </li>
        ))}
      </ol>
      {!readOnly && sentences.length < MAX && (
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder="Add a sentence and press Enter"
          aria-label="New voice anchor sentence"
        />
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface ExpandedProfileReviewProps {
  bvp: ExpandedBrandVoiceProfile;
  clientId: string;
  onRefresh?: () => void;
  refreshDisabled?: boolean;
  refreshBtnRef?: React.RefObject<HTMLButtonElement | null>;
}

const PRONOUN_OPTIONS = [
  { value: "first_person" as const, label: "First person (I / we)" },
  { value: "second_person" as const, label: "Second person (you)" },
  { value: "mixed" as const, label: "Mixed" },
];

const HUMOR_OPTIONS = [
  { value: "none" as const, label: "None" },
  { value: "dry" as const, label: "Dry" },
  { value: "playful" as const, label: "Playful" },
  { value: "self_deprecating" as const, label: "Self-deprecating" },
];

const VOCAB_OPTIONS = [
  { value: "plain" as const, label: "Plain" },
  { value: "mixed" as const, label: "Mixed" },
  { value: "technical" as const, label: "Technical" },
];

const EXAMPLE_STYLE_OPTIONS = [
  { value: "analogy" as const, label: "Analogy" },
  { value: "data" as const, label: "Data" },
  { value: "story" as const, label: "Story" },
  { value: "direct" as const, label: "Direct" },
];

const SPECIFICITY_OPTIONS = [
  { value: "concrete_numbers" as const, label: "Concrete numbers" },
  { value: "vague_quantifiers" as const, label: "Vague quantifiers" },
  { value: "mixed" as const, label: "Mixed" },
];

const OPENING_OPTIONS = [
  { value: "question" as const, label: "Question" },
  { value: "bold_claim" as const, label: "Bold claim" },
  { value: "anecdote" as const, label: "Anecdote" },
  { value: "stat" as const, label: "Statistic" },
  { value: "problem" as const, label: "Problem" },
];

const CLOSING_OPTIONS = [
  { value: "cta" as const, label: "CTA" },
  { value: "question" as const, label: "Question" },
  { value: "summary" as const, label: "Summary" },
  { value: "one_liner" as const, label: "One-liner" },
  { value: "none" as const, label: "None" },
];

const HEADER_OPTIONS = [
  { value: "question" as const, label: "Question" },
  { value: "command" as const, label: "Command" },
  { value: "statement" as const, label: "Statement" },
  { value: "mixed" as const, label: "Mixed" },
];

export function ExpandedProfileReview({
  bvp,
  clientId,
  onRefresh,
  refreshDisabled,
  refreshBtnRef,
}: ExpandedProfileReviewProps) {
  const expanded = isExpandedBVP(bvp);
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Editable field state -- initialized from bvp
  const [pronounPreference, setPronounPreference] = useState(bvp.pronoun_preference);
  const [formalityScale, setFormalityScale] = useState(bvp.formality_scale);
  const [humorStyle, setHumorStyle] = useState(bvp.humor_style);
  const [vocabularyComplexity, setVocabularyComplexity] = useState(bvp.vocabulary_complexity);
  const [exampleStyle, setExampleStyle] = useState(bvp.example_style);
  const [specificityPreference, setSpecificityPreference] = useState(bvp.specificity_preference);
  const [openingPattern, setOpeningPattern] = useState(bvp.opening_pattern);
  const [closingPattern, setClosingPattern] = useState(bvp.closing_pattern);
  const [headerStyle, setHeaderStyle] = useState(bvp.header_style);
  const [postStructureTemplate, setPostStructureTemplate] = useState(
    bvp.post_structure_template ?? ""
  );
  const [signaturePhrases, setSignaturePhrases] = useState<string[]>(bvp.signature_phrases ?? []);
  const [bannedJargon, setBannedJargon] = useState<string[]>(bvp.banned_jargon ?? []);
  const [voiceAnchorSentences, setVoiceAnchorSentences] = useState<string[]>(
    bvp.voice_anchor_sentences ?? []
  );
  const [antiPatternExample, setAntiPatternExample] = useState(bvp.anti_pattern_example ?? "");
  // Legacy fields
  const [tone, setTone] = useState<string[]>(bvp.tone ?? []);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      // Build patch body, excluding computed fields and voice_brief.
      // Always include user-editable array/string fields even when empty so
      // deliberate clearing (e.g. removing all banned_jargon chips) is persisted.
      const patch: Record<string, unknown> = {
        tone,
        banned_jargon: bannedJargon,
        signature_phrases: signaturePhrases,
        voice_anchor_sentences: voiceAnchorSentences,
        post_structure_template: postStructureTemplate || null,
        anti_pattern_example: antiPatternExample || null,
      };
      // Pass-through read-only fields (cadence/target_audience are not editable in this UI)
      if (bvp.cadence !== undefined) patch.cadence = bvp.cadence;
      if (bvp.target_audience !== undefined) patch.target_audience = bvp.target_audience;
      // Nullable enum fields: only set if the user has selected a value
      if (pronounPreference != null) patch.pronoun_preference = pronounPreference;
      if (formalityScale != null) patch.formality_scale = formalityScale;
      if (humorStyle != null) patch.humor_style = humorStyle;
      if (vocabularyComplexity != null) patch.vocabulary_complexity = vocabularyComplexity;
      if (exampleStyle != null) patch.example_style = exampleStyle;
      if (specificityPreference != null) patch.specificity_preference = specificityPreference;
      if (openingPattern != null) patch.opening_pattern = openingPattern;
      if (closingPattern != null) patch.closing_pattern = closingPattern;
      if (headerStyle != null) patch.header_style = headerStyle;

      await clientsApi.patch(clientId, { brand_voice_profile: patch });
      setSaveSuccess(true);
      setEditMode(false);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    // Reset to original bvp values
    setPronounPreference(bvp.pronoun_preference);
    setFormalityScale(bvp.formality_scale);
    setHumorStyle(bvp.humor_style);
    setVocabularyComplexity(bvp.vocabulary_complexity);
    setExampleStyle(bvp.example_style);
    setSpecificityPreference(bvp.specificity_preference);
    setOpeningPattern(bvp.opening_pattern);
    setClosingPattern(bvp.closing_pattern);
    setHeaderStyle(bvp.header_style);
    setPostStructureTemplate(bvp.post_structure_template ?? "");
    setSignaturePhrases(bvp.signature_phrases ?? []);
    setBannedJargon(bvp.banned_jargon ?? []);
    setVoiceAnchorSentences(bvp.voice_anchor_sentences ?? []);
    setAntiPatternExample(bvp.anti_pattern_example ?? "");
    setTone(bvp.tone ?? []);
    setSaveError(null);
    setSaveSuccess(false);
    setEditMode(false);
  };

  return (
    <div className="max-w-xl">
      {/* Action bar */}
      <div className="flex items-center gap-3 mb-6">
        {editMode ? (
          <>
            <Button onClick={handleSave} disabled={saving} aria-busy={saving} type="button">
              {saving ? "Saving..." : "Save profile"}
            </Button>
            <Button variant="secondary" onClick={handleCancel} disabled={saving} type="button">
              Cancel
            </Button>
          </>
        ) : (
          <>
            <Button
              ref={refreshBtnRef}
              variant="secondary"
              onClick={onRefresh}
              disabled={refreshDisabled}
              type="button"
            >
              <RefreshCw size={16} aria-hidden="true" />
              Refresh profile
            </Button>
            <Button variant="secondary" onClick={() => setEditMode(true)} type="button">
              Edit profile
            </Button>
          </>
        )}
      </div>

      {saveSuccess && !editMode && (
        <p role="status" className="text-sm text-[#2E4F2E] mb-4">Voice profile saved.</p>
      )}
      {saveError && (
        <p role="alert" className="text-sm text-[#8B0000] mb-4">
          {saveError}
        </p>
      )}

      {/* Voice Brief or Legacy Nudge */}
      {expanded && bvp.voice_brief ? (
        <VoiceBriefPanel voiceBrief={bvp.voice_brief} />
      ) : !expanded ? (
        <LegacyUpgradeNudge onRefresh={onRefresh} refreshDisabled={refreshDisabled} />
      ) : null}

      {/* Computed metrics (always read-only) */}
      <ComputedMetricsRow bvp={bvp} />

      {/* Identity group */}
      {expanded && (
        <FieldGroup label="Identity">
          <div className="space-y-5">
            <div>
              <FieldLabel>Pronoun preference</FieldLabel>
              <ChipSelect
                options={PRONOUN_OPTIONS}
                value={pronounPreference}
                onChange={setPronounPreference}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Formality scale</FieldLabel>
              <FormalityScale
                value={formalityScale}
                onChange={setFormalityScale}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Humor style</FieldLabel>
              <ChipSelect
                options={HUMOR_OPTIONS}
                value={humorStyle}
                onChange={setHumorStyle}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Vocabulary complexity</FieldLabel>
              <ChipSelect
                options={VOCAB_OPTIONS}
                value={vocabularyComplexity}
                onChange={setVocabularyComplexity}
                readOnly={!editMode}
              />
            </div>
          </div>
        </FieldGroup>
      )}

      {/* Patterns group */}
      {expanded && (
        <FieldGroup label="Patterns">
          <div className="space-y-5">
            <div>
              <FieldLabel>Example style</FieldLabel>
              <ChipSelect
                options={EXAMPLE_STYLE_OPTIONS}
                value={exampleStyle}
                onChange={setExampleStyle}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Specificity preference</FieldLabel>
              <ChipSelect
                options={SPECIFICITY_OPTIONS}
                value={specificityPreference}
                onChange={setSpecificityPreference}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Opening pattern</FieldLabel>
              <ChipSelect
                options={OPENING_OPTIONS}
                value={openingPattern}
                onChange={setOpeningPattern}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Closing pattern</FieldLabel>
              <ChipSelect
                options={CLOSING_OPTIONS}
                value={closingPattern}
                onChange={setClosingPattern}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Header style</FieldLabel>
              <ChipSelect
                options={HEADER_OPTIONS}
                value={headerStyle}
                onChange={setHeaderStyle}
                readOnly={!editMode}
              />
            </div>
            <div>
              <FieldLabel>Post structure template</FieldLabel>
              {editMode ? (
                <Input
                  value={postStructureTemplate}
                  onChange={(e) => setPostStructureTemplate(e.target.value)}
                  placeholder="hook -> pain -> insight -> example -> CTA"
                  aria-label="Post structure template"
                />
              ) : (
                <p className="text-sm text-[#111111]">
                  {postStructureTemplate || <span className="text-[#555555]">None specified.</span>}
                </p>
              )}
            </div>
          </div>
        </FieldGroup>
      )}

      {/* Anchors group */}
      <FieldGroup label="Anchors">
        <div className="space-y-5">
          {expanded && (
            <div>
              <FieldLabel>Signature phrases</FieldLabel>
              <EditableTagList
                tags={signaturePhrases}
                onChange={setSignaturePhrases}
                placeholder="Add a phrase and press Enter"
                label="New signature phrase"
                readOnly={!editMode}
              />
            </div>
          )}
          <div>
            <FieldLabel>Banned jargon</FieldLabel>
            <EditableTagList
              tags={bannedJargon}
              onChange={setBannedJargon}
              placeholder="Add a word or phrase and press Enter"
              label="New banned jargon term"
              readOnly={!editMode}
            />
          </div>
          {expanded && (
            <>
              <div>
                <FieldLabel>Voice anchor sentences</FieldLabel>
                <VoiceAnchorList
                  sentences={voiceAnchorSentences}
                  onChange={setVoiceAnchorSentences}
                  readOnly={!editMode}
                />
              </div>
              <div>
                <FieldLabel>Anti-pattern example</FieldLabel>
                {editMode ? (
                  <textarea
                    rows={2}
                    value={antiPatternExample}
                    onChange={(e) => setAntiPatternExample(e.target.value)}
                    placeholder="e.g. Synergizing our core competencies to leverage actionable insights..."
                    aria-label="Anti-pattern example"
                    className="w-full bg-transparent border-0 border-b border-[#111111] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-1 text-sm text-[#111111] py-2 resize-none"
                  />
                ) : (
                  <p className="font-['JetBrains_Mono'] text-xs text-[#555555]">
                    {antiPatternExample || "None specified."}
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </FieldGroup>

      {/* Legacy tone field */}
      {!expanded && (
        <FieldGroup label="Tone">
          <EditableTagList
            tags={tone}
            onChange={setTone}
            placeholder="Add descriptor and press Enter"
            label="New tone descriptor"
            readOnly={!editMode}
          />
        </FieldGroup>
      )}
    </div>
  );
}
