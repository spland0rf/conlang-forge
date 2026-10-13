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
