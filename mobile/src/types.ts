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
