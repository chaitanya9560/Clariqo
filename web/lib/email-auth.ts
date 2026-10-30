import { z } from 'zod';
export const EmailSchema = z.string().trim().email('Enter a valid email address.').max(254);
export const NewPasswordSchema = z.string().min(8, 'Use at least 8 characters for your password.').max(128, 'Use a password with at most 128 characters.');
export function recoveryDestination(type: string | null) { return type === 'recovery' ? '/account/password' : '/'; }
export function authMessage(code?: string) {
  if (code === 'email_not_confirmed') return 'Verify your email first. Check your inbox, or use Resend verification below.';
  if (code === 'over_email_send_rate_limit' || code === 'over_request_rate_limit') return 'Too many requests. Wait a little before trying again.';
  if (code === 'weak_password') return 'Choose a stronger password with at least 8 characters.';
  return 'The request could not be completed. Check your details and try again.';
}
