import { defineStore } from 'pinia'
import { ref } from 'vue'
import { request } from '../api/client.js'

/*
 * One campaign's narrative tree: its acts, sequences and scenes.
 *
 * `GET /campaigns/{id}/structure` hands back three ordered lists carrying
 * parentage rather than a nest, and this store keeps them that way. Assembling
 * a tree here and storing that instead would mean the shape the API sent and
 * the shape the app holds could drift, and every write would have to know how
 * to patch both.
 *
 * Kept per campaign rather than as one list, because two tabs can sit in two
 * campaigns (#59 put the id in the path for exactly that) and a single slot
 * would have them overwriting each other's tree on every navigation.
 *
 * It is read on *every* campaign route, not only the structure page: the
 * sidebar names the campaign's own children wherever you are. That is why it is
 * cached and single-flight rather than fetched per view — and why the API has
 * one endpoint for the whole tree instead of a thin `/acts` beside it, which
 * would be two things to keep ordered identically.
 */
export const useStructureStore = defineStore('structure', () => {
  /*
   * campaignId -> { acts, sequences, scenes }. A plain object rather than a Map
   * because Pinia's devtools render it and reactivity on a Map's contents needs
   * more ceremony than one screen's worth of data is worth.
   */
  const trees = ref({})
  const loading = ref(false)
  const error = ref(null)

  /*
   * One load per campaign, shared by everyone who asks — the same shape
   * `campaigns.ensureLoaded` uses, and for the same reason: the sidebar and the
   * view both want this on a structure page, and that should be one request.
   */
  const inflight = {}

  function ensureLoaded(campaignId) {
    inflight[campaignId] ??= load(campaignId)
    return inflight[campaignId]
  }

  /*
   * After a write, or after a failure the user asked to retry. Dropping the
   * in-flight promise is what makes the next `ensureLoaded` actually ask again
   * rather than hand back the settled one.
   */
  function reload(campaignId) {
    delete inflight[campaignId]
    return ensureLoaded(campaignId)
  }

  /*
   * Never rejects, for the reason the campaigns store gives: the callers are a
   * route guard and a template, and neither has anywhere to put a thrown error.
   * The failure lives in `error` where the page can render it and offer a retry.
   */
  async function load(campaignId) {
    loading.value = true

    try {
      trees.value[campaignId] = await request(`/campaigns/${campaignId}/structure/`)
      error.value = null
    } catch (failure) {
      error.value = failure
      // Deliberately not written as an empty tree. A campaign nobody has written
      // in yet and a campaign we could not ask about look identical once they
      // are both `{ acts: [], ... }`, and they want opposite screens.
    } finally {
      loading.value = false
    }
  }

  /*
   * One act, sequence or scene, whole.
   *
   * The tree deliberately carries no scene bodies (#88), so a scene's page has
   * to ask for its own — and once one level needs a detail read, all three may
   * as well go through the same door rather than have the scene page be the odd
   * one out.
   *
   * Keyed by kind *and* id because the three levels have their own id spaces:
   * nothing stops an act and a scene sharing a uuid, and a single map keyed by
   * id alone would have them overwriting each other.
   */
  const nodes = ref({})

  const nodeInflight = {}

  const KINDS = { act: 'acts', sequence: 'sequences', scene: 'scenes' }

  const pathTo = (campaignId, kind, id) => `/campaigns/${campaignId}/${KINDS[kind]}/${id}`

  function ensureNode(campaignId, kind, id) {
    const key = `${kind}:${id}`
    nodeInflight[key] ??= loadNode(campaignId, kind, id, key)
    return nodeInflight[key]
  }

  async function loadNode(campaignId, kind, id, key) {
    try {
      nodes.value[key] = await request(pathTo(campaignId, kind, id))
      error.value = null
    } catch (failure) {
      error.value = failure
      // Left absent rather than written as an empty record: a node that is not
      // this viewer's answers 404 exactly as one that never existed, and the
      // page shows the same thing for both.
    }
  }

  function nodeFor(kind, id) {
    return nodes.value[`${kind}:${id}`] ?? null
  }

  /*
   * A full replacement, not a patch — the rule every write in this API follows.
   * Every field goes on every save, so a body left out of the request would be
   * cleared rather than kept, and the forms are loaded with current values for
   * exactly that reason.
   *
   * Rejects rather than parking the failure, the way the campaign store's writes
   * do: a form has somewhere to put a rejected promise and needs to know which
   * field the API objected to, and painting the whole page as broken because one
   * save was refused would be the wrong screen showing the wrong thing.
   */
  async function saveNode(campaignId, kind, id, fields) {
    const saved = await request(pathTo(campaignId, kind, id), { method: 'PUT', json: fields })

    nodes.value[`${kind}:${id}`] = saved
    /*
     * The tree carries this record's title, and now says something out of date.
     * Refetched rather than patched here: patching would put the tree's shape in
     * a second place, and the two would drift the first time a field was added.
     * A save is a deliberate act and rare — one extra request is the cheaper
     * kind of cost.
     */
    await reload(campaignId)

    return saved
  }

  /*
   * Write a new act, sequence or scene.
   *
   * The parent travels in the body rather than in the path, matching the API:
   * an act takes none, a sequence may name an act, a scene may name either. It
   * lands at the end of whatever it was given, which is what "add" means — a new
   * record has no place in the story yet, and putting it first would push the
   * campaign's opening down every time someone jots something.
   */
  async function createNode(campaignId, kind, fields) {
    const created = await request(`/campaigns/${campaignId}/${KINDS[kind]}/`, {
      method: 'POST',
      json: fields,
    })

    nodes.value[`${kind}:${created.id}`] = created
    await reload(campaignId)

    return created
  }

  /*
   * Remove one act, sequence or scene.
   *
   * What was inside it is **not** removed with it: the API rehomes children to
   * the nearest surviving parent, because cascading is the one answer #80 ruled
   * out — it loses an evening's prep to a single click. An act's sequences and
   * scenes go to the campaign; a sequence's scenes go to the act above it.
   *
   * So this is far less dangerous than it looks, and the confirmation says so
   * rather than trying to frighten anyone out of it.
   */
  async function deleteNode(campaignId, kind, id) {
    await request(pathTo(campaignId, kind, id), { method: 'DELETE' })

    delete nodes.value[`${kind}:${id}`]
    delete nodeInflight[`${kind}:${id}`]
    await reload(campaignId)
  }

  /*
   * Where a record sits: its parent, and its place among that parent's children.
   *
   * **One endpoint for every level** (#109). A drag is one gesture whichever kind
   * of row it grabbed, so the client no longer picks a URL by inspecting what it
   * just picked up — the kind travels in the body instead.
   *
   * `parent` and `after` are `{ id, kind }` or `null`. Null parent is the
   * campaign, which is a real place rather than a fallback; null `after` is the
   * top of the list, a placement rather than an absent argument. The anchor
   * carries its own kind because a sibling group is everything under one parent
   * (#101) — a scene may be dropped below the sequence above it.
   *
   * The response *is* the new tree, so nothing is refetched. A placement can move
   * rows nobody dragged — the gap running out renumbers a whole sibling list —
   * and the old refetch left a window where the screen showed a stale order it
   * had guessed at. This replaces the tree with what the server actually did,
   * which is the half of #111 a status code cannot fix.
   */
  async function place(campaignId, kind, id, { parent = null, after = null } = {}) {
    const tree = await request(`/campaigns/${campaignId}/structure/placement`, {
      method: 'PUT',
      json: { item: { id, kind }, parent, after },
    })

    trees.value[campaignId] = tree
    /*
     * The detail read of this record is now stale in its `position` and parent
     * ids. Dropped rather than patched, so the next page that wants it asks —
     * patching would put the record's shape in a second place.
     */
    delete nodes.value[`${kind}:${id}`]
    delete nodeInflight[`${kind}:${id}`]

    return tree
  }

  function treeFor(campaignId) {
    return trees.value[campaignId] ?? null
  }

  /*
   * The campaign's own children — what the sidebar lists.
   *
   * Depth one, in `position` order, and acts and scenes together rather than
   * "the acts": a scene may hang off the campaign directly, so a one-shot's
   * sidebar is a list of scenes and nothing had to be written for it. Sequences
   * that skip the act level are deliberately *not* here — three kinds at one
   * level reads as a mess in a 15rem column, and they are visible on the
   * structure page where there is room.
   */
  function childrenOf(campaignId) {
    const tree = treeFor(campaignId)
    if (!tree) return []

    return [
      ...tree.acts.map((act) => ({ kind: 'act', node: act })),
      ...tree.scenes
        .filter((scene) => scene.act_id === null && scene.sequence_id === null)
        .map((scene) => ({ kind: 'scene', node: scene })),
    ].sort((a, b) => a.node.position - b.node.position || a.node.id.localeCompare(b.node.id))
  }

  return {
    trees,
    nodes,
    loading,
    error,
    ensureLoaded,
    reload,
    treeFor,
    childrenOf,
    ensureNode,
    nodeFor,
    createNode,
    saveNode,
    deleteNode,
    place,
  }
})

/*
 * How far through an act the table has got, read off its scenes.
 *
 * Derived, never stored: there is no `Act.status` and there must not be, because
 * two sources of truth for "have we played this" is exactly the drift #80 warns
 * about against #81. Exported beside the store rather than hidden in a component
 * so the sidebar and the outline cannot disagree about what "ongoing" means.
 *
 * `empty` is not `not started`. An act with no scenes has not been *written*,
 * which is a different problem from written-and-unplayed, and flattening the two
 * into one grey dot hides the one a game master can act on.
 */
export function actProgress(tree, act) {
  const scenes = scenesUnder(tree, act)
  const done = scenes.filter((scene) => scene.status === 'done').length
  const pending = scenes.filter((scene) => scene.status === 'planned').length

  return {
    total: scenes.length,
    played: done,
    label: !scenes.length ? 'empty' : !done ? 'not started' : !pending ? 'finished' : 'ongoing',
    fill: scenes.length ? Math.round((done / scenes.length) * 100) : 0,
  }
}

/*
 * Every scene under an act, however deep. A scene inside one of the act's
 * sequences counts towards it — the act is what a game master sees progress on,
 * and a sequence is a grouping inside it rather than a boundary around it.
 */
export function scenesUnder(tree, act) {
  const sequenceIds = new Set(
    tree.sequences.filter((sequence) => sequence.act_id === act.id).map((sequence) => sequence.id),
  )

  return tree.scenes.filter(
    (scene) => scene.act_id === act.id || sequenceIds.has(scene.sequence_id),
  )
}

/*
 * What to call something nobody has named yet.
 *
 * Adding is one click now — pick a kind, get a row, type into it — which means a
 * record can exist before it has a title, and a game master who presses Escape
 * gets to keep it that way. Every place a title is rendered goes through here, so
 * an unnamed act reads as an unnamed act rather than as a blank line that looks
 * like a rendering fault.
 *
 * Muted rather than bracketed: it is a real record in a real place, and the only
 * thing missing is a word.
 */
export function titleOf(node, kind) {
  return node?.title?.trim() || `Untitled ${kind}`
}

/*
 * The last record already sitting under a parent, which is what a reparented one
 * should follow.
 *
 * **Reparenting appends.** Arriving at the top of a list whose order you did not
 * choose is more surprising than arriving at the end of it — and `after: null`,
 * which is what an omitted anchor means, is the top. This is the difference
 * between the two, and it is a function rather than a line in each form so the
 * act page and the scene page cannot drift on it.
 *
 * The record being moved is excluded: it may already be in this list, and
 * anchoring something to itself is not a position.
 */
export function lastUnder(tree, kind, { actId = null, sequenceId = null, excluding } = {}) {
  if (!tree) return null

  /*
   * A sibling group is everything under one parent, whatever kind it is (#101),
   * so this walks both tables rather than the one matching `kind`. Anchoring on
   * the last *scene* of an act that also holds sequences would drop the row into
   * the middle of the list its own siblings are already ordered in.
   *
   * A sequence holds only scenes, so that branch asks one kind — not a special
   * case so much as the tree having nothing else to offer there.
   */
  const family =
    sequenceId !== null
      ? tree.scenes
          .filter((s) => s.sequence_id === sequenceId)
          .map((node) => ({ kind: 'scene', node }))
      : [
          ...tree.sequences
            .filter((s) => s.act_id === actId)
            .map((node) => ({ kind: 'sequence', node })),
          ...tree.scenes
            .filter((s) => s.act_id === actId && s.sequence_id === null)
            .map((node) => ({ kind: 'scene', node })),
        ]

  const ordered = family
    .filter((entry) => entry.node.id !== excluding)
    .sort((a, b) => a.node.position - b.node.position || a.node.id.localeCompare(b.node.id))

  const last = ordered.at(-1)
  return last ? { id: last.node.id, kind: last.kind } : null
}

/*
 * Every scene in the campaign, in the order the story goes in.
 *
 * Depth-first through the tree by `position`, which is what makes the stepper on
 * a scene page walk to *the next scene in the story* rather than the next
 * sibling — across the end of a sequence, out of an act and into the next one.
 * That is the payoff for ordering being explicit in the data rather than implied
 * by a timestamp, and it is the only place the flattened order exists.
 */
export function scenesInOrder(tree) {
  const byPosition = (a, b) => a.position - b.position || a.id.localeCompare(b.id)
  const scenesOf = (predicate) => tree.scenes.filter(predicate).sort(byPosition)

  const walkSequence = (sequence) => scenesOf((scene) => scene.sequence_id === sequence.id)

  const walkAct = (act) =>
    [
      ...tree.sequences
        .filter((s) => s.act_id === act.id)
        .map((node) => ({ kind: 'sequence', node })),
      ...scenesOf((scene) => scene.act_id === act.id).map((node) => ({ kind: 'scene', node })),
    ]
      .sort((a, b) => byPosition(a.node, b.node))
      .flatMap((child) => (child.kind === 'sequence' ? walkSequence(child.node) : [child.node]))

  return [
    ...tree.acts.map((node) => ({ kind: 'act', node })),
    ...tree.sequences.filter((s) => s.act_id === null).map((node) => ({ kind: 'sequence', node })),
    ...scenesOf((scene) => scene.act_id === null && scene.sequence_id === null).map((node) => ({
      kind: 'scene',
      node,
    })),
  ]
    .sort((a, b) => byPosition(a.node, b.node))
    .flatMap((child) => {
      if (child.kind === 'act') return walkAct(child.node)
      if (child.kind === 'sequence') return walkSequence(child.node)
      return [child.node]
    })
}

/*
 * What sits above a node, nearest last.
 *
 * Only the direct parent is stored — a scene under a sequence does not also
 * record that sequence's act, because a copy kept there could disagree after a
 * move — so the chain is walked here rather than read off the row.
 */
export function trailTo(tree, kind, node) {
  if (!tree || !node) return []

  if (kind === 'sequence') {
    const act = tree.acts.find((a) => a.id === node.act_id)
    return act ? [{ kind: 'act', node: act }] : []
  }

  if (kind === 'scene') {
    if (node.act_id) {
      const act = tree.acts.find((a) => a.id === node.act_id)
      return act ? [{ kind: 'act', node: act }] : []
    }

    const sequence = tree.sequences.find((s) => s.id === node.sequence_id)
    if (!sequence) return []

    return [...trailTo(tree, 'sequence', sequence), { kind: 'sequence', node: sequence }]
  }

  return []
}

/*
 * Which sibling a record should land after, to move one step up or down.
 *
 * The endpoint takes an anchor rather than an index, so a step is arithmetic on
 * the sibling list — and the arithmetic is not symmetrical, which is the whole
 * reason it lives here with a test rather than inline in a template.
 *
 * Moving **down** past one neighbour means landing after that neighbour:
 * `siblings[index + 1]`. Moving **up** means landing after the record *two*
 * places above, because the one directly above is the neighbour being passed —
 * and two above the top is nothing at all, which is `null`, the head of the list.
 *
 * `undefined` means the move is not available: the first record cannot rise and
 * the last cannot fall. Distinct from `null` on purpose, since `null` is a real
 * destination.
 */
export function anchorForStep(siblings, id, direction) {
  /*
   * Entries (`{ kind, node }`) rather than bare records, because the anchor has
   * to name its own kind: since #101 the row above may be a different kind than
   * the one being moved, and an id alone does not say which it is.
   */
  const index = siblings.findIndex((entry) => entry.node.id === id)
  if (index === -1) return undefined

  const at = (position) => ({ id: siblings[position].node.id, kind: siblings[position].kind })

  if (direction === 'up') {
    if (index === 0) return undefined
    return index >= 2 ? at(index - 2) : null
  }

  if (index >= siblings.length - 1) return undefined
  return at(index + 1)
}

/*
 * The parents a record may legally be given, nearest thing to a menu of them.
 *
 * The tree's shape is the only rule here and it is structural rather than
 * checked: an act has no parent but the campaign, a sequence may take an act,
 * and a scene may take either. The campaign itself is always an option and is
 * listed first, because #80's skippable levels make it a real place rather than
 * a fallback.
 *
 * A record is never offered itself, and a sequence is never offered a parent
 * that would put it inside another sequence — there is no column for that.
 */
export function parentsFor(tree, kind, id) {
  if (!tree || kind === 'act') return []

  const campaign = [{ label: 'The campaign', act_id: null, sequence_id: null }]

  const acts = tree.acts.map((act) => ({ label: act.title, act_id: act.id, sequence_id: null }))

  if (kind === 'sequence') return [...campaign, ...acts]

  const sequences = tree.sequences.map((sequence) => ({
    label: sequence.title,
    act_id: null,
    sequence_id: sequence.id,
  }))

  return [...campaign, ...acts, ...sequences].filter((option) => option.sequence_id !== id)
}
