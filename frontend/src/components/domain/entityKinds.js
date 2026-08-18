/*
 * The entity kinds a chip can represent. Lives outside EntityTag.vue because
 * `defineProps()` is hoisted out of setup() and so may only reference imported
 * bindings, not locals declared alongside it.
 *
 * Each kind pairs an accent token with an icon and a spoken-out label, so the
 * kind is never communicated by colour alone.
 *
 * The label is a catalogue key rather than the word, because this table is built
 * when the module is imported — before the locale is known — and the word is
 * what a screen reader says. `EntityTag` resolves it at render.
 */
export const ENTITY_KINDS = {
  npc: { icon: 'pi-user', label: 'entity.npc' },
  location: { icon: 'pi-map-marker', label: 'entity.location' },
  item: { icon: 'pi-box', label: 'entity.item' },
  monster: { icon: 'pi-eye', label: 'entity.monster' },
  faction: { icon: 'pi-flag', label: 'entity.faction' },
  session: { icon: 'pi-calendar', label: 'entity.session' },
}
