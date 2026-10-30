# Email account setup

Email/password login uses required email verification. Custom Gmail SMTP and confirmation/recovery templates are configured for Clariqo. Real inbox delivery still needs a user sign-up check after deployment. Google sign-in is intentionally disabled.

## Configure your own Supabase project

1. Create a project on your chosen plan. This implementation uses no paid feature and does not enable billing.
2. Apply `supabase/migrations/20261030190130_clariqo_accounts.sql` to a new database once. The Clariqo development project already has this schema; do not run it twice there.
3. Enable email/password Auth. Keep email confirmation enabled and password minimum length at 8. Disable anonymous sign-in.
4. Set the Auth Site URL to your website. Allow the site's `/auth/confirm` and `/auth/callback` URLs, plus localhost equivalents only for development.
5. Configure custom SMTP under Authentication → Email → SMTP settings. Supabase's default sender restricts delivery to organization members and is not suitable for public registration. Save SMTP credentials only in Supabase, never in this repository or Vercel frontend variables.
6. Set the confirmation email link to `{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email` and the recovery email link to `{{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=recovery`.
7. Add the project URL and publishable key from `web/.env.example` to local/Vercel settings. These two values are browser-safe. **Never add a Supabase service-role/secret key to this app.** Keep Groq credentials server-only.
8. Redeploy after configuring build-time public variables. Register using your own email, open the verification link, sign in, sign out, and test password reset before opening registration to visitors.

## Data and access

- The server checks the current Supabase user and confirmed email before serving the study page or accepting AI requests.
- PDFs upload directly from the browser to a private bucket. Database and file policies restrict access to the signed-in owner.
- One account supports five PDFs / 50 MB metadata total; each file has a 20 MB storage limit. Private bucket quotas still apply, including abandoned files from interrupted uploads.
- Scores, chats and plans use a revision check so an old tab cannot silently overwrite newer progress. Reload on a save conflict.
- Clearing study data removes that account's PDFs and study records across devices, while retaining its login account. File removal and database removal are separate operations; a failed operation may need a retry.
- Legacy browser-only data remains on that device and is not silently imported into an account.
- Sign out on shared devices. The application does not yet offer account deletion or Google sign-in.

## Verification

Run `npm test`, `npm run typecheck` and `npm run build` from `web/`. The optional `web/tests/manual/cloud-isolation.ts` needs two disposable confirmed users supplied over stdin by a secure local harness; it does not run during unit tests or send verification email. Never save user tokens or admin keys to a test fixture.

Local checks: 55 automated tests pass; type checking passes; live two-account learning/file isolation, stale-write rejection, safe failed replacement and owner-only clearing pass. Supabase database security advisors found no issues. Real email delivery and browser click-through are not verified yet.
