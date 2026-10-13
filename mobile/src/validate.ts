// Quick checks before calling the server (the server is still the authority).
export function checkEmail(v: string): string | null {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()) ? null : "Enter a valid email address.";
}
export function checkNewPassword(v: string): string | null {
  return v.length >= 10 ? null : "The password must be at least 10 characters.";
}
