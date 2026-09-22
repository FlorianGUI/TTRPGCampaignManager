# Frontend

Vue 3 + Vite single-page app for the TTRPG Campaign Manager.

## Commands

```bash
npm install       # install dependencies
npm run dev       # start the dev server on http://localhost:5173
npm run build     # production build into dist/
npm run preview   # serve the production build on http://localhost:4173
npm test          # run the unit tests once (Vitest)
npm run test:watch  # run the tests in watch mode
npm run lint      # check with ESLint (eslint-plugin-vue)
npm run lint:fix  # auto-fix ESLint issues
npm run format    # format all files with Prettier
npm run format:check  # verify formatting without writing
```

## Linting & formatting

ESLint (flat config, `eslint.config.js`) uses `eslint-plugin-vue`'s recommended
rules for `.vue` and JS files. Prettier owns formatting; `@vue/eslint-config-prettier`
disables any ESLint rules that would conflict with it. Prettier settings live in
`.prettierrc.json`.

The dev (5173) and preview (4173) ports match the origins allowed by the API's
CORS configuration (`CORS_ORIGINS`, see `app/common/security/cors.py`) — the API
is a separate origin, so that list is what lets the session cookie work at all.

## Structure

```
frontend/
  index.html                       # Vite entry point
  vite.config.js                   # Vite + Vitest config
  vitest.setup.js                  # the DOM measurements jsdom does not implement
  scripts/
    vendor-fonts.mjs               # re-download the self-hosted webfonts
    check-contrast.mjs             # WCAG AA check over the theme's colour pairs
  src/
    main.js                        # app bootstrap + PrimeVue plugin + router
    App.vue                        # the persistent shell around <RouterView>
    router/
      index.js                     # router instance, scroll behaviour, title
      routes.js                    # the route table
    views/
      HomeView.vue                 # / — the campaign chooser, and the create dialog
      CampaignSettingsView.vue     # /campaigns/:id/settings — editing and deleting one
      SpikeView.vue                # SPIKE: design-direction judgement surface
      StyleguideView.vue           # /styleguide — every token and component
      NotFoundView.vue             # catch-all
    assets/
      base.css                     # element defaults, prose, ornament
      fonts.css                    # @font-face for the self-hosted families
      fonts/                       # woff2, latin + latin-ext subsets
    api/
      http.js                      # the transport: one request, no auth state
      client.js                    # what features call: token + refresh-on-401
      sso.js                       # where "Continue with Discord" goes, and back
    stores/
      auth.js                      # current user, in-memory access token
      theme.js                     # theme state, persisted
      campaigns.js                 # the campaigns you own, and the three writes
      sources.js                   # the sources you own, read-only
      currentCampaign.js           # the remembered campaign — storage, not a store
    composables/
      useWriteFailure.js           # what the app says when a write is refused
    directives/
      dragToPlace.js               # dragging a row of the outline, over the ⋮ menu
    design-system/
      preset.js                    # composes the three layers into the preset
      tokens/
        primitives.js              # raw ramps and scales, no meaning, no imports
        semantic.js                # roles, the two schemes, app tokens
        components.js              # per-component overrides
    components/
      AppShell.vue                 # top bar + context sidebar + content area
      AppNav.vue                   # the nav list, shared by sidebar and drawer
      CampaignTitle.vue            # the campaign name at the head of its own nav
      CampaignForm.vue             # the campaign fields, for both creating and editing
      BareLayout.vue               # chrome for the pages above any campaign
      ChromeActions.vue            # who you are, and the account menu, in both bars
      domain/                      # stat block, read-aloud, dice, entity tags
    markdown/
      CampaignMarkdown.vue         # the one renderer every prose field uses
      parse.js                     # text ⟶ mdast, and nothing further
      directives.js                # the dialect: directive name ⟶ component
      render.js                    # mdast ⟶ vnodes, block and inline
      toPlainText.js               # mdast ⟶ a string, for cells and titles
      nodes.js                     # the tree facts both renderers share
      MarkdownField.vue            # the writing side: the toolbar, and the editor
      toolbar.js                   # what a button writes, and where the caret lands
      livePreview.js               # mdast ⟶ what the field draws over the source
      editor.js                    # those descriptors ⟶ CodeMirror decorations
      continuation.js              # what Enter writes on a line carrying a marker
    content/
      sample.js                    # the nav's sections, and sample copy for the spike
    i18n/
      en.js                        # every string the app says, in English
      fr.js                        # the same keys, in French
      locale.js                    # what the browser asked for ⟶ a locale we speak
      primevue.js                  # PrimeVue's own strings
      index.js                     # t(), the current locale, and dates
```

## Design system

The visual direction is settled (issue #23). Two surfaces exercise it:

- **`/styleguide`** — the living reference: every token in both schemes, and
  every component we own or override. Start here. **Dev only** — see below.
- **`/campaigns/:campaignId/sessions` (`SpikeView.vue`)** — one realistic page
  of prep notes, for judging type, palette and ornament _in context_ rather than
  in a grid. It stands in for session notes until that context exists; its
  counts come from `content/sample.js` and are invented.

### Token layers

`design-system/preset.js` composes three layers under `tokens/`, and each layer
may only reach downwards:

| layer      | file                   | holds                                                 |
| ---------- | ---------------------- | ----------------------------------------------------- |
| primitives | `tokens/primitives.js` | raw ramps and scales, no meaning, no imports          |
| semantic   | `tokens/semantic.js`   | roles, the two schemes, app-owned `grimoire.*` tokens |
| components | `tokens/components.js` | per-component overrides, referencing semantic tokens  |

Two rules that are load-bearing:

- **Never reference a primitive from a component override.** Go through the
  semantic layer, so a ramp change never has to be chased into component files.
- **Never collapse `LIGHT_ROLES` / `DARK_ROLES` into shared numeric indices.**
  The schemes walk the ramp in _opposite_ directions — parchment top-down,
  candlelight bottom-up. Collapsing them is what produced the light-on-light
  dark theme bug during the spike.

`tokens/primitives.js` is deliberately import-free so plain Node tooling can
read it; `scripts/check-contrast.mjs` imports it directly.

### The prose palette

`design-system/proseColors.js` is the seven hues and three tiers that
`:color[…]{hue=… tier=…}` resolves to (#147). It sits beside the token layers
rather than inside `markdown/`, because four unrelated modules ask it the same
question — the dialect (is this a colour?), the picker (what can be chosen?),
`tokens/semantic.js` (what does it resolve to?) and the contrast checker (what
has to be gated?) — and none of them should hold an opinion of its own.

- **Every hue ramp carries 200–800.** Three legible tiers need ends the original
  300–700 ramps did not have: measured on the page, `torch` cleared 4.5:1 at
  exactly one step. Light walks **800/700/600** down, dark walks **200/300/400**
  up, and the two step maps in `tokens/semantic.js` are kept apart for the same
  reason `LIGHT_ROLES` / `DARK_ROLES` are.
- **Not 900 in light**, though it passes AA comfortably. At 900 the hues
  converge on near-black and a red, a blue and a violet become three blacks in
  running prose. A palette whose strongest tier cannot be told apart by hue is
  not a palette.
- **`gold` is not a prose hue.** It is reserved for affordances, and prose that
  can borrow the accent makes every link and button on the page ambiguous.
- **Four surfaces are checked, not two.** A colour sits on a card, on the page,
  or on either of those seen through a `:::read-aloud` box's wash — which is a
  third, composited surface, and the one `torch` `subtle` was found failing on.
  `READ_ALOUD_WASH` is stated as numbers so the checker can flatten it.
- **Adding an eighth hue** is a row in `PROSE_HUES`, a ramp in `primitives.js`
  and three rules in `base.css` — nothing in `render.js`, the picker or the
  checker. The CSS is the one table written out by hand, because CSS cannot
  build a custom-property name from a class, and `proseColors.test.js` fails if
  it drifts from the table.

### Elevation

**There is no elevation scale, and that is a decision rather than an omission.**
A printed page has no z-axis: depth here comes from rules (`.rule-double`,
`.rule-fleuron`), borders (`--p-content-border-color`) and the chrome/content
split — dark leather against parchment. Every in-page `shadow` in the preset is
explicitly `none`, overriding Aura's defaults on `card`, `formField` and both
focus rings.

**There is no density scale either, since #79.** Comfortable is the only
spacing, so `--space-*` has one definition rather than two. The 44px touch
floors dotted around the components look like they were density workarounds and
are not: they are a touch guideline, set in absolute pixels precisely so no
change to the spacing scale can quietly lower them.

Shadows survive only where something genuinely floats above the page — drawer,
popover, menu — and those are the `overlay.*` tokens in `tokens/semantic.js`.
**They are tinted warm, and that is not decoration.** Aura ships them as pure
black at 10%; this palette never reaches pure black, so a neutral shadow reads
grey-blue against parchment — a hole in the page rather than a raised edge.
`OVERLAY_SHADOW` and `MODAL_SHADOW` warm them to the ink at the bottom of the
ramp. #79's account menu was the first overlay in the app and is what put the
question on screen; anything floating that is added later should read those
tokens rather than inventing a shadow.

Some things worth knowing before touching any of it:

- **PrimeVue is pinned to v4** (`4.5.5`, MIT). v5 relicensed to a commercial
  model and renders a license banner without a key. Don't bump the major
  without deciding that question.
- **Everything colour-bearing reads a `--p-*` token.** No component hardcodes a
  hex. A theme switch is a token swap.
- **`app` wins over `primevue` in the cascade**, which is what lets `base.css`
  override component styles without specificity games — and is also a trap.
  `<Button as="router-link">` renders an `<a>`, so the anchor rule claims it and
  paints a primary button's label in the same accent as its background: a solid
  block with invisible text. `a.p-button` reverts colour and decoration to the
  primevue layer. jsdom does not do layered cascade, so no unit test can catch
  this class of bug — it is found by looking.
- **Two themes**: `candlelight` (dark, the default) and `parchment` (light),
  driven by a `.theme-candlelight` class on `<html>`. The default is
  deliberately _not_ tied to `prefers-color-scheme`.
- **Contrast is checked, not eyeballed**: `node scripts/check-contrast.mjs`
  verifies every foreground/background pair against WCAG AA in both themes and
  exits non-zero on failure. Run it after any palette change.
- **Fonts are self-hosted**, no CDN — Cinzel (display), Alegreya (body),
  IBM Plex Mono (dice and stat lines), latin + latin-ext only, all OFL.
  Regenerate with `node scripts/vendor-fonts.mjs`.
- **Ornament is token-gated**: a `.no-ornament` class on any ancestor turns off
  textures and rules.

### Routing

`vue-router` in history mode. Conventions, set in `router/routes.js`:

- every route is **named**; link and navigate by name, never by a hand-built path
- the landing route is eagerly imported, everything else is **lazy**, so the
  initial bundle carries only what the first paint needs
- **`/styleguide` is dev only.** Its route is behind an `import.meta.env.DEV`
  literal, which the bundler substitutes at build time, so the branch and its
  dynamic import are dropped entirely: the view is not shipped, no chunk is
  emitted, and `/styleguide` falls through to the catch-all in a production
  build. Keep that condition a bare literal — putting it behind a variable or a
  function parameter defeats the elimination and the chunk comes back.
- every route sets `meta.title`, which `router/index.js` turns into the document
  title
- `meta.layout` names the chrome `App.vue` wraps the view in: `auth` for the
  signed-out column, `bare` for the pages above any campaign. Saying nothing
  gets the campaign shell, which is what all but a handful want
- the catch-all stays **last**

`App.vue` holds the shell and renders `<RouterView>` inside it, so the top bar
and sidebar are not torn down on navigation.

### Where a signed-in visitor lands

`/` is a **chooser**, not a page inside the campaign frame (#59). `AppNav`'s
Campaign section is meaningless before a campaign is picked, so home sits
outside `AppShell` in `BareLayout` — `meta.layout: 'bare'`, the third value
beside `auth` and saying nothing.

The campaign id lives **in the path** (`/campaigns/:campaignId/...`).
`localStorage` holds only the campaign to open by default, under
`grimoire.campaign`. That is a knowing contradiction of #14, which put
`active_campaign_id` on `users` — a column cut from #44 and still unbuilt. It
moves server-side the day multi-device continuity matters.

The rule for `/` is one line, in `enterRememberedCampaign`:

> a remembered id? go there. otherwise, show the chooser.

The two exceptions — just signed in, just left a campaign — are **not** special
cases in that guard. They work because the id is cleared at those moments, in
four places, and between them they are every point a session starts or stops
being one person's:

| where             | why it is not covered by the others                                   |
| ----------------- | --------------------------------------------------------------------- |
| `auth.clear()`    | logout, and a refresh the server _answered_ — a session ending        |
| `auth.logIn()`    | an expired session never calls logout; that person meets a login form |
| `SsoCallbackView` | a provider sign-in arrives through `boot()`, which must _not_ forget  |
| the campaign chip | leaving would otherwise bounce straight back in                       |

Two consequences worth keeping:

- **Do not "fix" this with a flag.** A `skipAutoEnter` boolean is the obvious
  shape and it desynchronises on the first page reload. The clearing rule cannot.
- **`boot()` must never forget.** A cold open with a live refresh cookie is the
  case the whole feature exists for. The SSO callback is the one sign-in that
  also arrives through `boot()`, which is why it clears explicitly.

### The top bar: where you are on the left, who you are on the right

#79 collapsed a bar that had accumulated one control per decision — six of them,
none of which said who was signed in. What is left is a label and a menu.

**Where you are is a label; what you can do is a menu.** That split is the whole
shape of it, and it is why the campaign's name and the campaign's actions live
in different places rather than together.

- **`ChromeActions.vue` is the one menu** — everything you can do: switch theme,
  and inside a campaign its settings and closing it, then sign out. Shared by
  `AppShell` and `BareLayout` so the two bars cannot drift apart; the campaign
  arrives as a prop rather than by forking the component. The username is the
  trigger itself rather than a name beside one: one control, carrying
  `aria-haspopup`, `aria-expanded` and a focus ring because it is pressable.
- **The campaign items are added, not dimmed.** They exist only when there is a
  campaign. A disabled item reads as broken rather than as not-yet-available —
  the argument #59 made for the sidebar.
- **`CampaignTitle.vue` is a label and nothing else.** No border, no chevron,
  nothing to press, `cursor: default`. It sits at the head of the nav it names,
  in the sidebar and in the drawer — below 900px the drawer is the only place
  the campaign is named at all. The tag it replaced looked pressable and mostly
  was not, which is the worst of both.
- **Its tooltip carries the rest of the name, and only when there is a rest.** A
  15rem column is narrower than a lot of campaign names, so the name ellipsises
  and the popup finishes it. A name that fits gets no popup at all — an empty
  value is how PrimeVue's directive is told to unbind one — because a popup that
  repeats a line you are already reading teaches you it is not worth waiting for.
  The ellipsis is visual only: CSS truncation does not shorten the accessible
  name, so nothing is hidden from a screen reader by a hover-only affordance. The
  `tooltip` directive is registered in `main.js`; `tokens/components.js` already
  had tokens for it.
- **Whether it is ellipsised is measured, not guessed.** `scrollWidth >
clientWidth`, retaken on a `ResizeObserver`, on a rename, and once
  `document.fonts.ready` resolves — the display face is `font-display: swap`, so
  the first paint measures the fallback. A character count would be wrong twice:
  the face is proportional, and the column is one width in the sidebar and
  another in the drawer.
- **The description is not in the chrome at all**, and not on the chooser's cards
  either. It is being held for #31: there it introduces a table to someone
  deciding whether to join it, which is a different reader at a different moment
  from a game master hovering the name of a campaign they are already inside. It
  is still stored, and still edited on the settings page.
- **The theme item reads "Switch theme"**, not the name of the theme it would
  switch to. Naming the destination needs no state indicator, which is the
  argument for it, but it reads as a place among a list of verbs. The icon
  carries the direction — a sun in candlelight, a moon in parchment.
- **`aria-expanded` is flipped on click, not from the menu's `show` event.**
  PrimeVue emits that from the overlay's transition hooks, so it arrives after
  the animation — and the attribute describes what the button just did, not what
  an animation has finished doing. Focus returns to the trigger on close.

Two recorded decisions changed here, and both were rewritten rather than deleted:

- **#25 said sign out must hold its place at every width.** That was written when
  the alternative was folding it away as the bar narrowed. It is in the menu now:
  one tap further, but present on every route and at every width, and no longer a
  44px icon beside another 44px icon — which is how a thumb aiming at the theme
  toggle ends a session. The reasoning lives in `ChromeActions.vue`.
- **Search is gone entirely** — field, toggle and collapsed row. Nothing was ever
  behind it, a placeholder since the spike, and a control that does nothing is a
  promise the app does not keep.

Below 640px the ladder is one rung long — the wordmark goes, and the username
caps at 8rem in `ChromeActions`. The campaign is not on this row to compete for
it any more.

### Creating is a dialog; editing is a page

The two are shaped differently on purpose, and the difference is not
inconsistency:

- **Creating stays the `Dialog` on the chooser** (#59). It is short, it is never
  resumed, and nobody reloads half way through — and an empty state whose
  primary action navigates away is a worse answer than one that resolves where
  you are.
- **Editing is `/campaigns/:campaignId/settings`** (#49). An edit _is_
  interrupted, reloaded, bookmarked and opened in a second tab, and a modal
  survives none of those.

Both render `CampaignForm.vue`, so the two cannot drift apart.

The settings page is reached from the **cog on the campaign chip** in
`AppShell`'s top bar, beside the name it changes — by the time you want to
rename a campaign you are inside it, so the chooser carries no entry point of its
own and stays a screen for choosing a table. If that bar ends up carrying more
controls than it can, #79 owns the crowding.

Three things that go with all this:

- **`CampaignForm.vue` owns the form and nothing else.** The caller makes the
  call and hands back whatever it threw, through `error`. That is what lets
  creating navigate into the new campaign and editing stay put, without the
  shared component knowing that either happens.
- **Every write sends both fields.** `PUT /campaigns/{id}` is a full
  replacement, not a patch: a description left out of the body is cleared. A
  form that emitted only what changed would wipe the description of every
  campaign anyone renamed.
- **The empty-name check is not duplication of the API's 422.** `CampaignCreate.name`
  is a bare `str`, so the backend answers 422 for a name that is _missing_ and
  accepts one that is blank — the client check is the only thing between someone
  and a nameless campaign. A 422 is placed against the field named in its `loc`;
  pydantic's own wording is not shown, because it is written for whoever wrote
  the request.
- **The length caps are the same rule twice, on purpose.** `maxlength` holds the
  name to 200 and the description to 1000 — the API's own limits, `name` being a
  `String(200)` column and the description capped in the campaign schema. The API
  is still the one that decides; the fields say it earlier, so nobody writes a
  description for a minute and learns from a 422 that the minute was wasted. The
  chooser's cards break the name anywhere for the same reason — 200 characters
  need not contain a space, and one without would run out over the card beside
  it.

Deleting lives on that same settings page, behind the campaign's name typed out.
It is not on the chooser, which is the screen people land on straight after
signing in, and it is not a dialog: `CampaignService.delete` takes every
character at the table with it and the API offers no undo, so the confirmation
has to be one that muscle memory cannot satisfy.

`currentCampaign.js` is deliberately import-free and is not a Pinia store:
`stores/auth.js` has to clear it, and it cannot import a store that imports
`api/client.js`, which imports the auth store.

## Language: French or English, from the browser

Every user-facing string the frontend owns lives in a catalogue, and the app
speaks whichever of the two languages the browser asked for. `src/i18n/` is the
whole of it:

```
src/i18n/
  en.js          # the English catalogue
  fr.js          # the French one, same keys, same order
  locale.js      # what the browser asked for ⟶ a locale we speak
  primevue.js    # PrimeVue's own strings, for the components we use
  index.js       # t(), the current locale, and dates
```

**Copy goes in the catalogue, not in the template.** A new string is a key in
`en.js` and a key in `fr.js`, read back with `t('its.key')`. That is the rule
this section exists to state — a literal typed into a `.vue` file is a sentence
one of the two languages will never see, and nothing catches it but a reader.

```vue
<script setup>
import { t } from '../i18n/index.js'
</script>

<template>
  <h1>{{ t('home.title') }}</h1>
  <Button :label="t('home.retry')" @click="reload" />
</template>
```

`t` is a plain function rather than a `$t` global from a plugin: it is imported
where it is used, so ESLint sees a typo'd import, a test renders real copy with
no plugin installed, and the store and the router — neither of which has a
component around it — reach copy the same way a template does.

**The locale is resolved once, before the app mounts.** `main.js` asks
`resolveLocale()` what the browser wants, matched on the primary subtag so
`fr-CA` and `fr-BE` are French, with English as the fallback for everything
else. `setLocale` writes the answer onto `<html lang>` — `index.html` ships
`lang="en"` for the moment before the module runs, and the app makes it true.
There is no language switcher and no reactivity behind `t`: a chosen language is
a preference, and a preference needs somewhere to live per account, which is a
separate conversation.

That timing is the one trap. Modules are evaluated before `main.js` runs, so
anything built at the top level of a module is built in English and stays that
way — `content/sample.js` exports a function for exactly this reason, and
`SceneView`'s status options are a computed. Call `t` when something renders,
not when a module loads.

**Placeholders are whole values, never fragments**: `t('home.welcome', {
username })`, so a translator can put the words in the order their language
uses. `t` throws for a key nobody wrote and for a placeholder with no value —
loudly, because a missing key rendering its own name across a button reads as
broken to everyone except the person who could fix it. Where a
sentence _is_ split across two or three keys it is because the markup splits it
— a `<strong>` around a word in the middle — and never to save a duplicate. The
renderer takes vnodes and never an HTML string, so there is no `v-html` to put a
marked-up sentence through.

**Sentences that name one of the three kinds get one key per kind** —
`outline.nameThis.act`, `.sequence`, `.scene` — rather than a `{kind}` filled
into one sentence. It reads as duplication in English, where the words either
side do not change; in French, "this act" and "this sequence" do not share a
demonstrative, and one sentence with a hole in it cannot say both.

**PrimeVue has its own copy**, configured in the same breath (`app.use(PrimeVue,
{ locale })`). It merges over the library's English defaults, so `primevue.js`
carries only what the components this app actually uses can say — a date
picker's month names are not translated for a date picker nobody has written.

**Dates go through `formatDate`**, which is `Intl.DateTimeFormat` with the
resolved locale. Nothing renders one yet (#78 gave records their times and no
screen shows them); it is there so the first screen that does is already
speaking the app's language rather than the operating system's.

**What is deliberately not translated**: anything the backend writes — the
rate-limit sentences a 429 carries arrive as finished English prose, and
translating them would mean the API negotiating a language — and user content,
which is never translated by anyone.

The tests assert English copy, under the locale the catalogue defaults to, and
resolve nothing through `t` where a sentence is what is being checked: asserting
on keys would stop them noticing that the copy is wrong. `LoginView.test.js`
pins French for one describe block, which is what checks the wiring in between.
`i18n/catalogues.test.js` is what makes drift loud — it fails when a key exists
in one catalogue and not the other, or when a translation drops a placeholder.

## Prose: Campaign Manager markdown

Every long-form field in the app — a session note, a scene, an act's
description — is markdown in one dialect, rendered by one component. Not a
session-note feature: naming it after its first caller would have produced a
second dialect the moment scenes arrived. `src/markdown/` is the whole of it.

```markdown
The party meets :npc[Fen Warden] outside :location[the Drowned Chapel].
She wants :item[the Tarnished Key] back, and will pay :dice[2d6]{result=9} gold.

:::read-aloud
The water is waist-deep and colder than it has any right to be.
:::

Owlbears here are unusually aggressive :ref[SRD 5.1]{page=249}.

The ward answers with :color[searing light]{hue=torch tier=bold}.
```

The syntax is [CommonMark generic
directives](https://talk.commonmark.org/t/generic-directives-plugins-syntax/444)
— `:name[label]{attrs}` inline, `:::name` … `:::` as a block — parsed by
`remark-parse` + `remark-directive`. One grammar covers all four components, and
attributes map onto props, so there is no per-directive translation layer.

**`dialect.js` is the dialect.** Directive name → the forms it accepts and the
props to build, with `directives.js` holding the other half of the table —
name → component. A new directive is an entry there, not a branch in the walker.
`ENTITY_KINDS` is asked in `dialect.js` and nowhere else, so adding a kind to the
design system is the whole change needed to make `:that-kind[…]` render.

**`:color` is the one directive that is presentation and nothing else**, and it
is worth naming that rather than discovering it later. Every other directive
says what a phrase _is_; this one says how it looks, so the note is colour-coded
to a convention only its author knows — and the rendered span deliberately
carries no ARIA, because "wyrd, bold" is a decision about ink and reading it out
is noise. A rule the game itself owns (damage types, say) comes back as its own
semantic directive built on the same tokens, never as a preset in the picker.

### Three projections, one parser

| Mode              | What it is for                                                                                                                          |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `block` (default) | the full document — headings, paragraphs, read-aloud boxes                                                                              |
| `inline`          | inline directives still render; block structure flattens to its words. Descriptions, shown where there is no room for a boxed paragraph |
| `toPlainText()`   | no components at all. List cells, `title` attributes, page titles                                                                       |

The third is the one that goes missing: the moment a description is markdown,
every list in the app renders raw `:npc[…]` unless something reduces it. It is a
function rather than a mode because its output is a string, not a tree.

```vue
<CampaignMarkdown class="prose" :source="note.body" />
<CampaignMarkdown mode="inline" :source="act.description" />
```

One root element — `div` for block, `span` for inline — so `class` and the rest
fall through and the reading measure is applied from outside.

### Why it renders vnodes, and never HTML

**There is no `v-html` here, and there must not be one.** Bodies are
user-authored, and once campaigns are shared they are authored by someone other
than the reader — a stored-XSS surface with a direct path to the session token.

The parser stops at mdast and the walker builds vnodes with `h()`. No HTML
string is ever produced, so there is nothing to sanitise and nothing to get
wrong: a raw `<script>` in the source is an mdast `html` node, whose value is
handed to Vue as text, and text is all it can become. `EntityTag`'s prop
validator still runs, so a bad kind is caught rather than styled.

That guarantee is a fact about the dependency list. **`remark-rehype`,
`remark-stringify`, any `rehype-*` or any sanitiser appearing in
`package.json` means a compiler is back and this stopped being true.**
`remark-gfm` is the one safe addition — mdast in, mdast out.

**CodeMirror does not weaken it.** The writing side is a CodeMirror view since
#152 — a `<textarea>` renders one text style for its whole value, so it could
never draw the formatting the field is meant to show. It builds DOM nodes rather
than markup, exactly as `render.js` does, so there is still no string for
anything to be injected into. What it must never gain is a grammar:
`@codemirror/lang-markdown` would be a second parser reading the same text as
the one above, and the two would disagree precisely where it matters.

### What the field draws

`**bold**` reads as bold while it is being written and the asterisks come back
when the caret reaches them (#153). The decorations come from the **same tree**
`CampaignMarkdown` renders: `parse()` records an offset on every node, so which
characters are a `strong` is a lookup rather than a second opinion.

Two modules, split the way `toolbar.js` and `MarkdownField.vue` are split.
`livePreview.js` is pure — a tree, the text, and where the caret is, in; `hide`,
`mark`, `line` and `widget` descriptors out — and is tested without a DOM.
`editor.js` turns those into CodeMirror decorations and has no decisions left to
make.

**A construct opens when the selection touches it**, which is the whole of "the
caret can still reach the characters": one filter in a pure function rather than
caret handling spread across a view plugin. Quotes and list items open a line at
a time, because opening all of a four-paragraph quote would put markers back on
screen nowhere near where anyone is looking.

**Enter continues what the line was carrying.** A list drawn as a list is one
Enter has to be able to continue: `- a rope` gives `- `, `3.` gives `4.`, a
quote goes on being quoted, and a marker with nothing after it is taken away
instead of repeated — which is how a writer gets out of a list.

`continuation.js` holds that rule, and holds it without importing CodeMirror at
all, since a command is a function handed a view and a keymap entry is a plain
object. It is bound ahead of `defaultKeymap` and answers `false` on every line
with no marker, which hands Enter straight back.

**It is the one question here the tree does not answer**, deliberately: the `>`
on a quote's second line is not a node — it sits inside a text node with the
words — so a prefix is a lexical fact about one line rather than an opinion
about the document, which is why `quoteLines` reads markers the same way.
`@codemirror/lang-markdown` ships exactly this behaviour and taking it would
mean taking the Lezer grammar with it.

**The document is re-read after a pause, not on the keystroke.** Measured: the
walk costs under a millisecond on a two-thousand-word body and the parse costs
twenty to thirty, every keystroke, because the whole document is the only unit
`remark-parse` takes. The delay is uniform rather than reserved for long bodies,
because `**bold` is a half-written construct and re-reading between the two
asterisks makes marks flicker under the fingers. While a tree is stale the
decorations are carried along by the edits rather than dropped.

Dropping `v-html` does not close every hole on its own:
`[click](javascript:…)` is an ordinary markdown link, and `h('a', { href })`
would fire it. `render.js` whitelists link schemes and renders the rest as text.
Images render as their alt text until the asset context exists — a remote
`<img>` in a shared note is a tracking pixel.

### Nothing disappears

A directive the dialect does not recognise — a typo, or a note written against a
newer version — renders as the text the author typed, marked with
`.markdown__unknown`. So does a directive used in the wrong form, or carrying an
attribute that cannot be honoured: `:dice[1d20]{outcome=nat20}` shows as text
rather than as a chip reading "fumble", because `DiceChip` renders any outcome it
is handed as one word or the other. Silently swallowing a GM's writing is the
one failure mode with no signal attached.

## State and the API

Pinia is the single state pattern; there is no second way to hold shared state.
Stores live in `src/stores/`, and `installTheme()` still runs from `main.js`
before mount so the theme class is on `<html>` before first paint.

### Talking to the API

Two modules, and the split between them is load-bearing:

| module          | what it does                                                       |
| --------------- | ------------------------------------------------------------------ |
| `api/http.js`   | builds and sends one request; knows nothing about who is signed in |
| `api/client.js` | attaches the access token, and renews it on a 401                  |

**Feature stores call `request` from `client.js`.** The auth store is the one
exception: signing in, refreshing and signing out go straight to `apiFetch`, so
a refresh can never be intercepted by the 401 handling that exists to serve it.
That is what stops it looping.

**The API host is runtime configuration, not part of the build.** `index.html`
loads `/config.js` before the app, and that file sets
`window.__CONFIG__ = { apiUrl }`. `api/http.js` reads it once at import.

| where         | where `/config.js` comes from                       | from                                         |
| ------------- | --------------------------------------------------- | -------------------------------------------- |
| production    | `/opt/dnd/config/config.js`, aliased by nginx       | whatever configures the host                 |
| dev / preview | the `dev-runtime-config` plugin in `vite.config.js` | `VITE_API_URL`, else `http://localhost:8000` |

Vite substitutes `VITE_*` at **build** time, so a host in the bundle makes the
artifact correct in exactly one environment and silently wrong in every other —
which is how a build once shipped calling `localhost:8000`. Nothing in `dist/`
names a host now, so the same artifact deploys anywhere and moving the API is one
line on the server.

**No deploy step writes it.** It sits outside `/opt/dnd/frontend-dist`, which the
deploy replaces wholesale, so it is host state rather than something every deploy
has to restore — and it is the first thing that should become an Ansible task
rather than a step to translate.

Three things follow, and all three are load-bearing:

- **It fails closed.** A production build that finds no `apiUrl` throws at import
  rather than falling back to localhost. A fallback there would be the original
  bug again, in production, silently. The error names the file and where it
  lives, because that is the only clue anyone will get.
- **`/config.js` must not be cached.** It carries no content hash, unlike
  everything under `/assets/`, so `nginx/lastdawn.fr.conf` serves it `no-cache`.
  Without that a browser can keep pointing at yesterday's API host.
- **The script tag is deliberately not a module.** It has to have run before the
  app's first import; `type="module"` defers it and it would not have.

### Moving a row: two gestures, one call

The outline can be rearranged with the `⋮` menu or by dragging (#109), and the
relationship between them is not negotiable.

**The menu is the one that must always work.** WCAG 2.2's **2.5.7 Dragging
Movements** asks that anything achievable by dragging also be achievable with a
single pointer and no drag — the menu is what makes that true, and it is also the
only path a keyboard or a screen reader has. A change that breaks it is a
regression however good the drag feels. Its tests are the canary and should stay
untouched.

**Both end in the same `structure.place` call.** Two gestures building their own
request bodies would drift, and the way that shows up is an omitted parent —
which the API reads as "put this on the campaign", not as "reorder".

`directives/dragToPlace.js` is the whole of the drag, and three things in it are
load-bearing:

- **The DOM is handed back before the API is asked.** SortableJS moves real
  nodes; Vue believes its own vnode tree. `onEnd` puts the element back exactly
  where it started, then calls `place`, and the response redraws — without that,
  the next patch runs against a shape Vue never made and `insertBefore` throws.
- **Each list describes itself on itself** (`data-parent-id`, `data-parent-kind`,
  `data-accepts`; rows carry `data-id` / `data-kind`). A drop can land in a
  different list than it started in, so the answer has to be readable off the
  target rather than held in the closure of whichever list the drag began in.
  It also makes the placement a pure function over a document, which is the one
  part of a drag that can honestly be unit tested.
- **`forceFallback: true`.** Native HTML5 dragging is desktop-only — on touch
  SortableJS falls back anyway — so leaving it on means two gestures to reason
  about and only one of them ever seen on a phone. It also stops the row's link
  being dragged as a URL instead.

What may hold what is enforced in `group.put` while dragging, so an illegal drop
is refused **visibly** — the placeholder never appears in a list that will not
have the row — rather than being accepted and undone. A cycle is impossible as a
consequence of that rather than as a rule of its own: no list inside an act
accepts an act.

**The gesture cannot be tested in jsdom**, which lays nothing out. The split is
the one #109 asks for: the placement arithmetic and the wiring are unit tested,
and the gesture is checked by hand — see the PR for what was walked through.

### When a write is refused

**Reads and writes fail differently, and the app answers them differently.** The
distinction is worth stating because getting it wrong is how the outline came to
swallow every write failure silently (#111).

| what failed                                                    | who holds it                 | what is shown                                        |
| -------------------------------------------------------------- | ---------------------------- | ---------------------------------------------------- |
| a read (`ensureLoaded`, `ensureNode`)                          | `structure.error`            | a `Message` in place of the page, with **Try again** |
| a write from a **form** (`SceneView`, `GroupingPage`)          | the page's own `failure` ref | a `Message` beside the fields                        |
| a write from a **control** (move, add, rename, delete, status) | nobody — it is transient     | a toast, via `useWriteFailure()`                     |

The third row is the one that did not exist. Those writes come from a `⋮` menu
and a plus rather than from a form, so a rejection had nowhere to go: every one
of them was `try`/`finally` with no `catch`, the spinner stopped, the row stayed
where it was, and the only trace was an uncaught `ApiError` in a console no game
master has open.

- **`useWriteFailure()` is the one mechanism**, and `COULD_NOT_SAVE` is the one
  sentence. The two forms keep their own `failure` ref — they have somewhere to
  put a message, and that ref also carries `"Give it a title."`, which is not a
  write failure — but they import the sentence rather than writing a fourth.
- **`failed()` takes no argument, deliberately.** The API's own detail is written
  for whoever wrote the request, so there is no door for it to come through
  (#102 settled that reasoning for signup).
- **The toast is sticky.** It carries a close button and no `life`: a message
  that fades is the easiest one to miss, and this one says the screen is not what
  was asked for.
- **`<Toast />` is rendered once, in `App.vue`**, outside the `auth.ready` gate,
  and `ToastService` is installed in `main.js`. It is the app's only toast — if a
  second kind of message ever wants one, decide then whether it is the same voice.
- **Nothing needs rolling back.** `place` writes the tree from the response and
  the other writes refetch, so a refused write never changed the screen; the
  status dot is drawn from the tree and holds no state of its own. What was
  missing was only saying so.

### Sessions

The backend issues a short access token in the response body and a long-lived
refresh token in an `httpOnly` cookie (#35). Three things follow, all of which
are easy to undo by accident:

- **Nothing is persisted by the auth store.** The access token lives in memory
  only. A reload restores the session from the cookie, so there is no
  long-lived credential on disk for an XSS to reach. Don't add `localStorage`
  here — the reason it looks like it needs it is the reason it must not have it.
- **Every request sends `credentials: 'include'`.** The API is a different origin
  in every environment — `api.lastdawn.fr` from `lastdawn.fr`, `:8000` from
  `:5173` — so without it the cookie is neither stored nor sent, and every
  session ends at the first reload.
- **Refreshes are serialised, per tab and across tabs.** The backend rotates the
  refresh token on every use and treats a re-presented one as a leak, revoking
  the whole session. So two refreshes racing do not waste a request — they sign
  the user out. `stores/auth.js` holds one in-flight promise per tab and takes a
  Web Lock across them; both are covered by tests, and neither is optional.

**A failed refresh is not the same as a refused one (#68).** `renewOnce` branches
on what came back, because three very different things used to end a session
identically:

| failure                         | session  | why                                                                           |
| ------------------------------- | -------- | ----------------------------------------------------------------------------- |
| `401`                           | ends     | The cookie is finished — expired, revoked or replayed. Nothing to tell apart. |
| `429`                           | ends     | The emergency stop. Revoked through `POST /users/logout` first, then cleared. |
| network error (`fetch` rejects) | **kept** | It never reached the server. "We could not ask" is not "the answer was no".   |
| `5xx`                           | **kept** | The same situation with a status on it — nginx while the backend restarts.    |

The middle two are the ones to be careful with:

- **A network failure must never clear the store.** It does not even arrive as an
  `ApiError` — `http.js` only builds one from a response — so a `TypeError` from
  `fetch` sails through any `catch` that is not looking for it. `boot()` runs on
  every page load, so getting this wrong means _open the app during a deploy and
  you are signed out_, holding a perfectly good thirty-day cookie.
- **The 429 stop is deliberate, and the client pulls the trigger.** Clearing
  locally alone would leave the refresh cookie alive, so a reload once the window
  passed would sign the user back in without a password. The store calls
  `POST /users/logout` — straight to `apiFetch`, for the same reason everything
  else here does — and clears anyway if that call fails too. The server's own
  sentence and its `Retry-After` travel to the login page in
  `auth.signedOutReason`, which `LoginView` reads once.

The first render waits on `auth.ready`, which the boot refresh flips when it
settles. Rendering earlier means a returning user sees a signed-out app for a
moment before it corrects itself. **It settles three ways, not two**: `reachable`
is false when boot never got an answer, and then the guard lets the navigation
stand — URL and all — while `App.vue` renders `ServerUnreachable` in place of the
app. Redirecting to `/login` there would be the app claiming to know something it
does not.

## Testing

Tests use [Vitest](https://vitest.dev/) with a `jsdom` environment and
[@vue/test-utils](https://test-utils.vuejs.org/) for mounting components. Test
files live next to the component they cover as `*.test.js`.
