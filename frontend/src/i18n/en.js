/*
 * Everything the app says, in English.
 *
 * Flat keys, dotted by where they are read rather than by grammar. A flat map is
 * what makes the parity check in `catalogues.test.js` a one-line comparison, and
 * it is what stops a key existing in one catalogue as a string and in the other
 * as a branch of nested objects.
 *
 * **A key is a sentence, not a fragment.** Where a sentence is broken up below
 * it is because the markup breaks it — a word inside `<strong>`, a link in the
 * middle of a line — and never to save a duplicate: two views saying the same
 * words keep two keys, because the day one of them is reworded is the day a
 * shared key would reword the other by accident.
 *
 * `{placeholders}` are filled by `t`, which throws for one it has no value for.
 * They are always whole values — a name, a count — never a fragment of the
 * sentence around them, because a translator needs the whole sentence to put the
 * words in the order their language uses.
 */
export const en = {
  /* ---- The app, and its chrome ------------------------------------------ */

  'app.name': 'Campaign Manager',

  'shell.openNav': 'Open navigation',
  'shell.campaignNav': 'Campaign',

  'chrome.switchTheme': 'Switch theme',
  'chrome.campaignSettings': 'Campaign settings',
  'chrome.closeCampaign': 'Close campaign',
  'chrome.signOut': 'Sign out',

  /* The nav sections in `content/sample.js`. Still invented, and translated
     anyway: a sidebar half in French is the thing #87 exists to prevent. */
  'nav.resources': 'Resources',
  'nav.pcs': 'PCs',
  'nav.npcs': 'NPCs',
  'nav.locations': 'Locations',
  'nav.factions': 'Factions',
  'nav.organization': 'Organization',
  'nav.sessions': 'Sessions',
  'nav.agenda': 'Agenda',

  /* ---- Document titles -------------------------------------------------- */

  /* `meta.title` on every route holds the key rather than the words — the tab is
     copy like any other, and it is the one piece of it outside the Vue tree. */
  'route.home': 'Your campaigns',
  'route.sessions': 'Session notes',
  'route.structure': 'Structure',
  'route.act': 'Act',
  'route.sequence': 'Sequence',
  'route.scene': 'Scene',
  'route.campaignSettings': 'Campaign settings',
  'route.login': 'Sign in',
  'route.signup': 'Create an account',
  'route.forgotPassword': 'Reset your password',
  'route.resetPassword': 'Choose a new password',
  'route.verifyEmail': 'Confirm your address',
  'route.ssoCallback': 'Signing you in',
  'route.styleguide': 'Styleguide',
  'route.notFound': 'Not found',

  /* ---- Signing in ------------------------------------------------------- */

  'login.title': 'Sign in',
  'login.username': 'Username',
  'login.password': 'Password',
  'login.submit': 'Sign in',
  /* The sentence the server sent is shown as it arrived — it is English, and
     translating what the backend writes needs the backend to negotiate a
     language (#87 leaves that out on purpose). Only the wait is ours. */
  'login.signedOut.retry': 'Signing in will work again in {wait}.',
  'login.wait.seconds': '{count} seconds',
  'login.wait.minute': 'a minute',
  'login.wait.minutes': '{count} minutes',
  /* Says nothing about which half was wrong, and must not: the API answers a
     wrong password and an unknown account identically. */
  'login.error.credentials': 'That username and password do not match an account.',
  'login.error.generic': 'Something went wrong signing in. Try again.',
  'login.or': 'or',
  'login.discord': 'Continue with Discord',
  'login.google': 'Continue with Google',
  'login.noAccount': 'No account yet?',
  'login.createOne': 'Create one',
  'login.forgotPassword': 'Forgot your password?',

  /* ---- Creating an account ---------------------------------------------- */

  'signup.title': 'Create an account',
  'signup.username': 'Username',
  'signup.email': 'Email',
  'signup.password': 'Password',
  'signup.submit': 'Create account',
  /* Named by the field it lands under rather than in the words — `FormField`
     ties it there with `aria-describedby`, so saying it twice says it twice. */
  'signup.error.notAccepted': 'That was not accepted. Try a different one.',
  'signup.error.email': 'That does not look like an email address we can use. Try another.',
  'signup.error.usernameTaken': 'That username is taken. Try another.',
  'signup.error.something': 'Something in there was not accepted.',
  'signup.error.generic': 'Something went wrong creating the account. Try again.',
  'signup.haveOne': 'Already have one?',
  'signup.signIn': 'Sign in',

  /* ---- Asking for a reset link ------------------------------------------ */

  'forgot.title': 'Reset your password',
  /* Deliberately says "if", and says it whatever happened. */
  'forgot.sent':
    'If that matches an account, a message is on its way. The link works once and expires in an hour.',
  'forgot.backToSignIn': 'Back to sign in',
  'forgot.identifier': 'Email address or username',
  'forgot.submit': 'Send a reset link',
  'forgot.remembered': 'Remembered it?',
  'forgot.signIn': 'Sign in',
  'forgot.error.generic': 'Something went wrong. Try again shortly.',

  /* ---- Choosing a new password ------------------------------------------ */

  'reset.title': 'Choose a new password',
  'reset.done': 'Your password has been changed, and every session has been signed out.',
  'reset.signIn': 'Sign in',
  'reset.missingToken': 'This link is missing its token. Ask for a new one and try again.',
  'reset.requestLink': 'Request a reset link',
  'reset.password': 'New password',
  'reset.submit': 'Change my password',
  'reset.askNewLink': 'Ask for a new link',
  'reset.error.invalidLink':
    'This link is no longer valid. It may have expired, or already been used — ask for a new one.',
  'reset.error.generic': 'Something went wrong. Try again shortly.',

  /* ---- Confirming an address -------------------------------------------- */

  'verify.working': 'Confirming your address…',
  'verify.done.title': 'Address confirmed',
  'verify.done.detail': 'Thank you — this address is now verified.',
  'verify.done.continue': 'Continue',
  'verify.unusable.title': 'This link is no longer valid',
  /* One message for expired, already-used and never-issued: the API answers all
     three the same way, and saying which would confirm that a token existed. */
  'verify.unusable.detail':
    'It may have expired, or already been used. Sign in and ask for a new one from your account.',
  'verify.failed.title': 'Something went wrong',
  'verify.failed.detail':
    'We could not confirm the address just now. The link is still good — try again shortly.',
  'verify.signIn': 'Sign in',

  /* ---- Coming back from a provider -------------------------------------- */

  /*
   * Keyed by the code the API sends, which is why these keys carry its spelling
   * rather than ours. `{provider}` is a provider's name, or `sso.provider` for
   * anything unrecognised — the value arrives in a URL, so it is never the raw
   * text that gets interpolated.
   */
  'sso.working': 'Finishing your sign-in…',
  'sso.backToSignIn': 'Back to sign in',
  'sso.provider': 'the provider',
  'sso.cancelled.title': 'Sign-in cancelled',
  'sso.cancelled.detail':
    'You did not authorise the app at {provider}, so nothing has changed here.',
  'sso.provider-unavailable.title': '{provider} did not answer',
  'sso.provider-unavailable.detail':
    'We could not reach {provider} just now. Nothing is wrong with your account — try again shortly.',
  'sso.no-email.title': 'Your {provider} account has no email address',
  'sso.no-email.detail':
    'An account here needs one, for password resets and confirmations. Add an address to {provider} and try again, or sign in with a password instead.',
  'sso.unverified-email.title': '{provider} has not confirmed your address',
  'sso.unverified-email.detail':
    'We only accept an address the provider has confirmed, so that nobody can reach an account by typing someone else’s address into a profile. Confirm it with {provider}, then come back.',
  'sso.email-in-use.title': 'That address already belongs to an account here',
  'sso.email-in-use.detail':
    'The account has not confirmed the address yet, so we cannot safely link it to {provider}. Sign in with your password, confirm your address, and {provider} will link to it after that.',
  'sso.no-session.title': 'The sign-in did not stick',
  'sso.no-session.detail':
    '{provider} signed you in, but the session did not reach this tab. Try signing in again.',
  'sso.failed.title': 'Something went wrong',
  'sso.failed.detail': 'We could not finish signing you in with {provider}. Try again shortly.',

  /* ---- Choosing a campaign ---------------------------------------------- */

  'home.unreachable.title': 'We could not reach your campaigns',
  'home.unreachable.detail':
    'The app is signed in, so this is the connection rather than your account.',
  'home.retry': 'Try again',
  'home.welcome': 'Welcome, {username}',
  'home.oneThing': 'One thing to do first.',
  'home.empty.title': 'Start your first campaign',
  'home.empty.detail':
    'A campaign holds your session notes, your factions, your locations and the people at your table. Everything else in here hangs off one.',
  'home.empty.action': 'Create a campaign',
  'home.title': 'Which table are you running?',
  'home.lede': 'Everything else lives inside a campaign.',
  'home.waiting': 'Fetching your campaigns…',
  'home.newCampaign': 'New campaign',
  'home.sources.title': 'Your sources',
  'home.sources.note':
    'Sources belong to you, not to a campaign — every campaign you run can see all of them.',
  'home.create.header': 'New campaign',
  'home.create.submit': 'Create campaign',

  /* ---- A campaign's settings -------------------------------------------- */

  'settings.waiting': 'Fetching this campaign…',
  'settings.unreachable.title': 'We could not reach this campaign',
  'settings.unreachable.detail':
    'The app is signed in, so this is the connection rather than your account.',
  'settings.retry': 'Try again',
  'settings.missing.title': 'That campaign is not here',
  'settings.missing.detail':
    'It has been deleted, or it belongs to somebody else. Either way there is nothing to edit.',
  'settings.backHome': 'Back to your campaigns',
  'settings.title': 'Campaign settings',
  'settings.lede': 'Renaming a campaign changes nothing inside it.',
  'settings.submit': 'Save changes',
  'settings.saved': 'Saved',
  'settings.delete.title': 'Delete this campaign',
  'settings.delete.warning':
    'Everything at this table goes with it, including every character sheet. There is no undo.',
  /*
   * Two halves of one sentence, and the only reason is the campaign's name in
   * `<strong>` between them: the renderer takes vnodes and never an HTML string,
   * so there is no `v-html` to put a marked-up sentence through. Both catalogues
   * keep the name in the middle — a language that wanted it elsewhere would need
   * its own arrangement here rather than a reordering of these two.
   */
  'settings.delete.confirmBefore': 'Type',
  'settings.delete.confirmAfter': 'to confirm',
  'settings.delete.submit': 'Delete campaign',
  'settings.delete.error.gone': 'That campaign is already gone.',
  'settings.delete.error.generic': 'Something went wrong deleting the campaign. Try again.',

  /* ---- The campaign's fields, for creating and editing alike ------------ */

  'campaignForm.name': 'Name',
  'campaignForm.description': 'Description',
  'campaignForm.optional': '(optional)',
  'campaignForm.hint':
    'A line introducing the table, for the people you invite to it. It can change at any time.',
  'campaignForm.error.missingName': 'Give the campaign a name.',
  'campaignForm.error.name': 'That name was not accepted. Try a different one.',
  'campaignForm.error.description': 'That description was not accepted. Try a shorter one.',
  'campaignForm.error.something': 'Something in there was not accepted.',
  'campaignForm.error.gone': 'That campaign is no longer there.',
  'campaignForm.error.generic': 'Something went wrong saving the campaign. Try again.',

  /* ---- The pages that stand in for a page ------------------------------- */

  'notFound.title': 'That page isn’t in this volume',
  'notFound.detail':
    'The link may be mistyped, or it may point at something not written yet. Nothing has been lost.',
  'notFound.back': 'Back to session notes',

  'unreachable.title': 'Can’t reach the server',
  'unreachable.detail':
    'This is on our end, not yours — you have not been signed out. It usually means the app is being updated, and it passes in a moment.',
  'unreachable.retry': 'Try again',

  'verification.text':
    'Your email address is not confirmed yet. Confirming it keeps your account yours.',
  'verification.resend': 'Send the link again',
  'verification.dismiss': 'Dismiss',
  'verification.sent': 'Sent. Check your inbox.',
  'verification.failed': 'Could not send it just now. Try again shortly.',

  /* The app's one answer to a refused write, wherever it is said. */
  'write.failed': 'That change could not be saved.',

  /* ---- The three kinds -------------------------------------------------- */

  /*
   * Every sentence that names a kind has one key per kind rather than a
   * `{kind}` to fill in. It reads as duplication in English, where the words
   * either side do not change; it is the whole point in French, where "this
   * act" and "this sequence" do not share a demonstrative.
   */
  'kind.act': 'Act',
  'kind.sequence': 'Sequence',
  'kind.scene': 'Scene',
  'kind.untitled.act': 'Untitled act',
  'kind.untitled.sequence': 'Untitled sequence',
  'kind.untitled.scene': 'Untitled scene',
  'kind.explains.act': 'A major division of the campaign.',
  'kind.explains.sequence': 'A run of scenes that tells a small story of its own.',
  'kind.explains.scene': 'A unit of play: one place, one cast.',

  /* ---- The outline ------------------------------------------------------ */

  'structure.heading': 'Structure',
  'structure.theCampaign': 'the campaign',
  'structure.expandAll': 'Expand all',
  'structure.collapseAll': 'Collapse all',
  'structure.loading': 'Loading',
  'structure.error': 'The structure could not be loaded.',
  'structure.retry': 'Try again',
  /* Three parts because the kind is emphasised inside the sentence — see the
     note on `settings.delete.confirmBefore`. */
  'structure.empty.before': 'Nothing here yet. An',
  'structure.empty.word': 'act',
  'structure.empty.after':
    'is a major division of the campaign — or write a scene straight onto the campaign and add the shape later.',
  'structure.emptyAct.before': 'Nothing in this act yet. A',
  'structure.emptyAct.word': 'sequence',
  'structure.emptyAct.after':
    'is a run of scenes that tells a small story of its own inside it — or write a scene straight onto the act.',

  'outline.expand': 'Expand {name}',
  'outline.collapse': 'Collapse {name}',
  'outline.skipsLevel': 'Attached to the act, skipping the sequence level',
  'outline.nameThis.act': 'Name this act',
  'outline.nameThis.sequence': 'Name this sequence',
  'outline.nameThis.scene': 'Name this scene',

  'add.toParent': 'Add to {parent}',

  'move.menuLabel': 'Move {name}',
  'move.up': 'Move up',
  'move.down': 'Move down',
  'move.into': 'Move into…',
  'move.delete': 'Delete',
  'move.dialog.title': 'Move {name}',
  'move.dialog.explain':
    'It goes to the end of whatever you choose. The campaign is a place in its own right — a scene does not need an act to belong to.',
  'move.dialog.placeholder': 'Choose where it goes',
  'move.cancel': 'Cancel',
  'move.confirm': 'Move',
  'move.parent.campaign': 'The campaign',
  'move.delete.title': 'Delete {name}?',
  'move.delete.confirm': 'Delete',
  /* What deleting actually costs. Nothing inside is lost — the API rehomes
     children — so these explain rather than warn. */
  'move.consequence.act':
    'Its sequences and scenes move to the campaign. Nothing in it is deleted.',
  'move.consequence.sequence': 'Its scenes move to the act above it. Nothing in it is deleted.',
  'move.consequence.scene': 'The scene and everything written in it goes.',

  'campaignNav.looseScene': 'In no act',

  /* ---- A node's own page ------------------------------------------------ */

  'trail.label': 'Breadcrumb',
  'trail.structure': 'Structure',

  'stepper.label': 'Scenes either side of this one',
  'stepper.previous': 'Previous scene',
  'stepper.next': 'Next scene',

  'node.contents.sequence': 'sequence',
  'node.edit': 'Edit',
  'node.save': 'Save',
  'node.cancel': 'Cancel',
  'node.title': 'Title',
  'node.description': 'Description',
  'node.contains': 'Contains',
  'node.missing': 'That is not here.',
  'node.needsTitle': 'Give it a title.',
  'node.teach.before': 'A',
  'node.teach.word': 'sequence',
  'node.teach.after':
    'is a run of scenes that tells a small story of its own inside an act — a beginning and an end, at a smaller scale than the act around it.',
  'node.empty': 'Nothing in it yet.',
  'node.empty.act.before': 'Add a',
  'node.empty.act.word': 'sequence',
  'node.empty.act.after':
    '— a run of scenes that tells a small story of its own — or write a scene straight onto this act.',
  'node.empty.sequence': 'Write a scene in it.',

  'scene.body': 'Body',
  'scene.unwritten': 'Nothing written yet. This is the normal state of most of a campaign.',
  /* Lowercase: the dot's accessible name reads "planned — mark as done", a
     sentence rather than a heading. The capitalised set below is the picker. */
  'scene.status.planned': 'planned',
  'scene.status.done': 'done',
  'scene.status.skipped': 'skipped',
  'scene.status.option.planned': 'Planned',
  'scene.status.option.done': 'Done',
  'scene.status.option.skipped': 'Skipped',
  'scene.status.hint': '{status} — mark as {next}',

  'progress.empty': 'empty',
  'progress.notStarted': 'not started',
  'progress.finished': 'finished',
  'progress.ongoing': 'ongoing',
  'progress.spelled': '{label} — {played} of {total} scenes played',
  'progress.none': 'empty — nothing written in it yet',

  /* ---- What prose renders as -------------------------------------------- */

  'entity.npc': 'NPC',
  'entity.location': 'Location',
  'entity.item': 'Item',
  'entity.monster': 'Monster',
  'entity.faction': 'Faction',
  'entity.session': 'Session',
  'readAloud.label': 'Read aloud',
  'dice.crit': 'crit',
  'dice.fumble': 'fumble',
  'statblock.actions': 'Actions',
}
