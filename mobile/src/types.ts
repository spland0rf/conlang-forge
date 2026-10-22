// Shapes returned by the Conlang Forge API (only the fields the app uses).
export type Session = { access_token: string; refresh_token: string };

export type Me = {
  id: string; email: string; display_name?: string; role?: string;
  email_verified?: boolean; debug?: boolean;
  [k: string]: unknown;
};

export type Config = {
  app: string; google_client_id: string | null; registration_open: boolean;
  model_available: boolean; email_enabled: boolean; verification_required: boolean;
  verified_email_required: boolean;
  google_app_enabled?: boolean;
  dials?: Record<string, (string | number)[] | null>;
};

export type LanguageSummary = {
  id: string; name: string; seed: number; created_at: number | string; updated_at: number | string;
  typology?: string | null; word_order?: string | null;
};

export type Issue = { level?: string; code?: string; message: string };
export type Usage = { input?: number; output?: number; cache_write?: number; cache_read?: number } | null;

export type ToSentence = { text: string; forms: string[]; glosses: string[] };
export type ToResult = {
  mode: "english" | "restricted"; input: string; reduced: string | null; re_text: string; text: string;
  sentences: ToSentence[]; issues: Issue[]; usage: Usage;
};

export type InterToken = { text: string; gloss: string; alts?: string[]; known?: boolean };
export type FromResult = {
  input: string; literal: string[]; re_text: string; interlinear: InterToken[][];
  issues: Issue[]; natural: string[] | null; usage: Usage;
};

export type RegisterResult = Session | { verification_required: true; email: string };

export type Sounds = { consonants: string[]; vowels: string[]; syllables: string[]; stress: string; spelling: string };
export type Grammar = {
  type: string; word_order: string; adjectives: string; adposition: string; affixes: string; number: string[]; cases: string[];
  genders: string[]; definiteness: string; tenses: string[]; aspects: string[]; moods: string[]; agreement: string; negation: string;
  questions: string; numeral_base: number | string; alignment: string; pro_drop: boolean;
};
export type Profile = {
  name: string; seed: number; words: number; one_syllable_share: number; sounds: Sounds; grammar: Grammar;
  quick_words: { en: string; form: string; ipa: string }[]; vocab_version: string;
};
export type Language = LanguageSummary & { profile: Profile };

export type DictEntry = {
  en: string; form: string; ipa: string; pos: string; gender?: string | null; plural?: string | null; dual?: string | null;
  tenses?: Record<string, string>; agreement?: Record<string, string>; built?: string | null; related: { en: string; form: string }[];
};
export type Script = "plain" | "special";

// ---- writing systems
export type ScriptDial = {
  key: string; label: string; group: string; description: string;
  type: "number" | "choice"; min?: number; max?: number; step?: number; values?: string[];
};
export type ScriptPreset = { id: string; label: string; note: string; pins: Record<string, string | number> };
export type ScriptCatalog = { groups: string[]; dials: ScriptDial[]; presets?: ScriptPreset[] };
export type ScriptRecord = {
  id: string; name: string; seed: number; pins: Record<string, string | number>;
  conlang_id: string | null; conlang_name?: string | null; primary: boolean; updated_at?: number | string;
};
export type ScriptSentence = { english: string; text: string; svg: string };
export type ScriptDetail = {
  script_record: ScriptRecord; spec: Record<string, any>; metrics?: { letters?: number; sound_coherence?: { nearest_same_manner?: number | null } } | null;
  specimen: string; sample: string; sentences?: ScriptSentence[]; language?: { id: string; name: string; exact?: boolean };
};
export type ScriptPreview = Omit<ScriptDetail, "script_record"> & { seed: number };
export type ScriptListItem = ScriptRecord;
export type LanguageScripts = { primary_id: string | null; scripts: ScriptRecord[] };
export type RenderResult = {
  script_id: string; script_name: string; primary: boolean; language: string; designed_for_this: boolean;
  sentences: { svg: string }[]; svg: string; approximations: unknown[];
  coverage: { total: number; exact: number; approximate: { sound: string; written_as: string[]; how: string }[] };
};
export type Proposal = { key: string; value: string | number; evidence?: string; source?: string };
export type Proposals = { proposals: Proposal[]; notes: string[]; usage: Usage };

// ---- checkpoints (versions)
export type VersionRow = { id: string; n: number; label: string; created_at: number; stored_bytes: number; raw_bytes: number };
export type VersionList = {
  working: number; has_checkpoints: boolean; max_per_item: number; versions: VersionRow[];
  branched_from: { kind: string; id: string; name: string; n: number } | null;
};
export type VersionChange = { label: string; then: string | number; now: string | number };
export type VersionDetail = {
  n: number; label: string; created_at: number; read_only: true; kind: "conlang" | "script"; name: string; seed: number;
  changes_since: VersionChange[];
  // a language
  words?: number; vocab_version?: string; consonants?: string[]; vowels?: string[]; typology?: string | null; word_order?: string | null;
  // a writing system
  sample?: string; specimen?: string; sentences?: ScriptSentence[];
};
export type BranchResult = { kind: "conlang" | "script"; item: any; exact?: boolean };
