const { describe, expect, test } = require('bun:test');
const {
  REVIEWER_LOGIN,
  reviewAcceptance,
  isFork,
  canTrigger,
  wantsReview,
  isTrustedBot,
  botApprovalFailure,
} = require('./review-gate.js');

const BOT = 'acme-bot[bot]';
const SHA = 'a'.repeat(40);

describe('PRs are blocked until an AI review exists', () => {
  const review = (login, state) => ({ user: { login }, state, commit_id: 'c'.repeat(40) });
  const user = { login: 'dev', type: 'User' };

  test.each(['APPROVED', 'CHANGES_REQUESTED', 'COMMENTED'])(
    'a %s review by the reviewer is accepted on any head',
    (state) => {
      expect(reviewAcceptance(user, [review(REVIEWER_LOGIN, state)], '').found).toBe(true);
    },
  );

  test.each([
    ['none', []],
    ['other reviewer', [review('someone', 'APPROVED')]],
    ['dismissed', [review(REVIEWER_LOGIN, 'DISMISSED')]],
  ])('%s is not an accepted review', (_, reviews) => {
    expect(reviewAcceptance(user, reviews, '').found).toBe(false);
  });

  test('a trusted bot needs no review', () => {
    expect(reviewAcceptance({ login: BOT, type: 'Bot' }, [], `x, ${BOT}`).found).toBe(true);
  });

  test('a user with a trusted login still needs a review', () => {
    expect(reviewAcceptance({ login: BOT, type: 'User' }, [], BOT).found).toBe(false);
  });
});

describe('the responder only acts for authorized same-repository requests', () => {
  test.each([
    ['acme/repo', false],
    ['other/repo', true],
    [undefined, false],
  ])('head repository %s is a fork: %p', (fullName, expected) => {
    expect(isFork({ head: { repo: { full_name: fullName } } }, 'acme/repo')).toBe(expected);
  });

  test.each([
    ['admin', true],
    ['maintain', true],
    ['write', true],
    ['triage', false],
    ['read', false],
    [undefined, false],
  ])('permission %s can trigger: %p', (permission, expected) => {
    expect(canTrigger(permission)).toBe(expected);
  });
});

describe('a review runs on first push and on explicit request', () => {
  const pr = (action, facts = {}) => ({ eventName: 'pull_request', action, ...facts });

  test.each([
    ['opened', pr('opened'), true],
    ['reopened', pr('reopened'), true],
    ['ready for review', pr('ready_for_review'), true],
    ['first push without review', pr('synchronize'), true],
    ['push after review', pr('synchronize', { reviewExists: true }), false],
    ['push with request label', pr('synchronize', { reviewExists: true, requestLabel: true }), true],
    ['request label added', pr('labeled', { label: 'request-ai-review', requestLabel: true }), true],
    [
      'block label removed with request',
      pr('unlabeled', { label: 'block-ai-reviews', requestLabel: true }),
      true,
    ],
    ['block label removed without request', pr('unlabeled', { label: 'block-ai-reviews' }), false],
    ['other label event', pr('labeled', { label: 'other', requestLabel: true }), false],
    ['draft', pr('opened', { isDraft: true }), false],
    ['blocked', pr('opened', { blockAiReviews: true }), false],
    ['blocked with request', pr('opened', { blockAiReviews: true, requestLabel: true }), false],
    ['review event', { eventName: 'pull_request_review', action: 'submitted' }, false],
  ])('%s', (_, facts, expected) => {
    expect(wantsReview(facts)).toBe(expected);
  });
});

describe('trusted-bot pull requests are approved without an AI review', () => {
  const commit = (sha, { author = BOT, committer = BOT, verified = true, reason } = {}) => ({
    sha,
    author: author && { login: author },
    committer: committer && { login: committer },
    commit: { verification: { verified, reason } },
  });
  const activity = (type, actor = BOT) => ({ activity_type: type, actor: { login: actor }, after: SHA });
  const created = [activity('branch_creation')];

  test.each([
    [BOT, true],
    ['dev', false],
  ])('%s is a trusted bot: %p', (login, expected) => {
    expect(isTrustedBot(login, `renovate[bot], ${BOT}`)).toBe(expected);
  });

  test.each([
    ['own commits', [commit('1'), commit('2', { committer: 'web-flow' })], ''],
    ['foreign author', [commit('1', { author: 'dev' })], 'commit 1: author is dev'],
    ['no author', [commit('1', { author: null })], 'commit 1: author is not a GitHub account'],
    ['foreign committer', [commit('1', { committer: 'dev' })], 'commit 1: committer is dev'],
    [
      'unsigned',
      [commit('1', { verified: false, reason: 'unsigned' })],
      'commit 1: signature is not verified (unsigned)',
    ],
  ])('approval covers only the own commits: %s', (_, commits, expected) => {
    expect(botApprovalFailure(BOT, created, commits)).toBe(expected);
  });

  test.each(['push', 'force_push', 'branch_creation'])('a foreign %s refuses the approval', (type) => {
    const activities = [activity('push'), activity(type, 'dev')];
    if (type !== 'branch_creation') {
      activities.push(activity('branch_creation'));
    }
    expect(botApprovalFailure(BOT, activities, [commit('1')])).toBe(`${type} to ${SHA} by dev`);
  });

  test('a reused branch starts clean at its latest creation', () => {
    const activities = [activity('push'), activity('branch_creation'), activity('push', 'dev')];
    expect(botApprovalFailure(BOT, activities, [commit('1')])).toBe('');
  });
});
