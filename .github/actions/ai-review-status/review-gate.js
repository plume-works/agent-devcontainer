// This module holds the decisions of the AI review gate. The github-script steps of
// ai-responder.yml and of this action read GitHub and call these functions.

const REVIEWER_LOGIN = 'plume-works-quill[bot]';
const ACCEPTED_REVIEW_STATES = new Set(['approved', 'changes_requested', 'commented']);
const PUSH_ACTIVITIES = ['branch_creation', 'push', 'force_push'];

const parseTrustedBots = (list) =>
  (list ?? '')
    .split(',')
    .map((login) => login.trim())
    .filter(Boolean);

const isTrustedBot = (login, trustedBots) => parseTrustedBots(trustedBots).includes(login);

/** Return `{ found, reason }` for a pull request author and its reviews. */
function reviewAcceptance(author, reviews, trustedBots) {
  if (author?.type === 'Bot' && isTrustedBot(author.login, trustedBots)) {
    return {
      found: true,
      reason: `Pull request authored by ${author.login} (bot); AI review is not required.`,
    };
  }
  // The rule makes sure that the pull request has a review, not that the AI reviewer
  // reviewed its current head. Do not compare review.commit_id against the head SHA.
  const accepted = [...reviews]
    .reverse()
    .find(
      (review) =>
        review?.user?.login === REVIEWER_LOGIN &&
        ACCEPTED_REVIEW_STATES.has(review?.state?.toLowerCase()),
    );
  if (accepted) {
    return {
      found: true,
      reason: `Found accepted AI review by ${accepted.user.login} for ${accepted.commit_id} with state ${accepted.state}.`,
    };
  }
  return { found: false, reason: `No AI review found. Expected a review from ${REVIEWER_LOGIN}.` };
}

const isFork = (pullRequest, repository) =>
  Boolean(pullRequest?.head?.repo?.full_name && pullRequest.head.repo.full_name !== repository);

const canTrigger = (permission) => ['admin', 'maintain', 'write'].includes(permission);

/** Decide if this pull_request run starts an AI review. */
function wantsReview({ eventName, action, label, isDraft, blockAiReviews, requestLabel, reviewExists }) {
  if (eventName !== 'pull_request' || isDraft) {
    return false;
  }
  // A run in the pr-<n> group starts the review that a label requests, if no label blocks
  // the reviews. A run in a label-<run id> group never starts it. For the sequence of the
  // labels, see ADR-0059.
  const labelEvent = ['labeled', 'unlabeled'].includes(action);
  const inPrGroup =
    !labelEvent ||
    (action === 'labeled' && label === 'request-ai-review') ||
    (action === 'unlabeled' && label === 'block-ai-reviews');
  if (!inPrGroup || blockAiReviews) {
    return false;
  }
  if (requestLabel) {
    return true;
  }
  if (labelEvent) {
    return false;
  }
  if (['opened', 'ready_for_review', 'reopened'].includes(action)) {
    return true;
  }
  return action === 'synchronize' && !reviewExists;
}

function commitFailure(commit, login) {
  if (commit.author?.login !== login) {
    return `author is ${commit.author?.login ?? 'not a GitHub account'}`;
  }
  const committer = commit.committer?.login;
  if (committer !== login && committer !== 'web-flow') {
    return `committer is ${committer ?? 'not a GitHub account'}`;
  }
  if (commit.commit?.verification?.verified !== true) {
    return `signature is not verified (${commit.commit?.verification?.reason ?? 'unknown'})`;
  }
  return '';
}

/**
 * Return why the trusted bot `login` gets no approval, or '' to approve.
 * The list `activities` starts with the newest activity. An approval covers only the commits
 * of the bot. See ADR-0069.
 */
function botApprovalFailure(login, activities, commits) {
  // For a branch name that GitHub used before, the check uses only the activities since the
  // latest creation of the branch.
  const created = activities.findIndex((activity) => activity.activity_type === 'branch_creation');
  const current = created === -1 ? activities : activities.slice(0, created + 1);
  const foreignPush = current.find(
    (activity) =>
      PUSH_ACTIVITIES.includes(activity.activity_type) && activity.actor?.login !== login,
  );
  if (foreignPush) {
    return `${foreignPush.activity_type} to ${foreignPush.after} by ${foreignPush.actor?.login ?? 'an unknown actor'}`;
  }
  for (const commit of commits) {
    const reason = commitFailure(commit, login);
    if (reason) {
      return `commit ${commit.sha}: ${reason}`;
    }
  }
  return '';
}

module.exports = {
  REVIEWER_LOGIN,
  reviewAcceptance,
  isFork,
  canTrigger,
  wantsReview,
  isTrustedBot,
  botApprovalFailure,
};
