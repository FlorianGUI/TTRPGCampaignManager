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
    saveNode,
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
  const played = scenes.filter((scene) => scene.status === 'played').length
  const pending = scenes.filter((scene) => scene.status === 'planned').length

  return {
    total: scenes.length,
    played,
    label: !scenes.length ? 'empty' : !played ? 'not started' : !pending ? 'finished' : 'ongoing',
    fill: scenes.length ? Math.round((played / scenes.length) * 100) : 0,
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
