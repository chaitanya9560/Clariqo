import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EmailSchema, NewPasswordSchema, recoveryDestination, authMessage } from '../lib/email-auth';
import { savedLearning, materialFromRow } from '../lib/saved-data';
import { EMPTY_LEARNING } from '../lib/types';

test('email input trims spaces and rejects invalid addresses', () => {
  assert.equal(EmailSchema.parse(' student@example.com '), 'student@example.com');
  for (const email of ['', 'not-an-email', 'x'.repeat(255) + '@example.com']) assert.equal(EmailSchema.safeParse(email).success, false);
});
test('new passwords respect the configured length limits without changing characters', () => {
  for (const password of ['short', 'x'.repeat(129)]) assert.equal(NewPasswordSchema.safeParse(password).success, false);
  assert.equal(NewPasswordSchema.parse(' safe password '), ' safe password ');
});
test('confirmation destinations cannot redirect to an external address', () => {
  assert.equal(recoveryDestination('recovery'), '/account/password');
  for (const type of [null, 'email', 'https://evil.example', '//evil.example']) assert.equal(recoveryDestination(type), '/');
});
test('auth errors explain verification and throttle without leaking provider details', () => {
  assert.match(authMessage('email_not_confirmed'), /Verify your email/);
  assert.match(authMessage('over_email_send_rate_limit'), /Wait/);
  assert.doesNotMatch(authMessage('private-provider-error'), /private-provider-error/);
});
test('saved learning rejects invalid quiz scores and unsafe source links', () => {
  assert.deepEqual(savedLearning(EMPTY_LEARNING), EMPTY_LEARNING);
  assert.throws(() => savedLearning({ ...EMPTY_LEARNING, results: [{ id: 'r', topic: 'x', total: 1, correct: 2, date: '2026-10-31', concepts: [] }] }));
  assert.throws(() => savedLearning({ ...EMPTY_LEARNING, messages: [{ id: 'm', role: 'assistant', content: 'x', webSources: [{ title: 'x', url: 'javascript:alert(1)' }] }] }));
});
test('material records must match both the account and private storage path', () => {
  const owner = '11111111-1111-4111-8111-111111111111', id = '22222222-2222-4222-8222-222222222222';
  const row = { id, user_id: owner, name: 'notes.pdf', size: 100, page_count: 1, chunks: [{ page: 1, text: 'Notes' }], storage_path: `${owner}/${id}/version.pdf`, created_at: '2026-10-31' };
  assert.equal(materialFromRow(row, owner).file, undefined);
  assert.throws(() => materialFromRow(row, '33333333-3333-4333-8333-333333333333'));
  assert.throws(() => materialFromRow({ ...row, storage_path: 'other-account/file.pdf' }, owner));
});
