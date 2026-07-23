/*
 * The entity kinds a chip can represent. Lives outside EntityTag.vue because
 * `defineProps()` is hoisted out of setup() and so may only reference imported
 * bindings, not locals declared alongside it.
 *
 * Each kind pairs an accent token with an icon and a spoken-out label, so the
 * kind is never communicated by colour alone.
 */
export const ENTITY_KINDS = {
  npc: { icon: 'pi-user', label: 'NPC' },
  location: { icon: 'pi-map-marker', label: 'Location' },
  item: { icon: 'pi-box', label: 'Item' },
  monster: { icon: 'pi-eye', label: 'Monster' },
  faction: { icon: 'pi-flag', label: 'Faction' },
  session: { icon: 'pi-calendar', label: 'Session' },
}
