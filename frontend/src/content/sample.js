/*
 * Sample content for the spike's judgement surface.
 *
 * The prose is written for this repo. The owlbear stat block is from the
 * System Reference Document 5.1, © Wizards of the Coast LLC, used under
 * CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode) — it's here
 * because a design decision about dense tabular type has to be judged against
 * real source-book data, not lorem ipsum.
 */

import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
import { t } from '../i18n/index.js'

/*
 * The Campaign section is gone from here: what a campaign holds is real now
 * (#88) and comes from `CampaignNav`, which reads the structure endpoint. These
 * two are still invented, and stay here until they are not.
 *
 * **What a campaign is made of, and what running it takes.** The split was
 * `Library` and `Characters`, which cut the wrong way twice: it put the party
 * and the NPCs in one place and the world they move through in another, and it
 * called a shelf of rulebooks the library when what a game master actually keeps
 * is their own material. Resources is everything the campaign is made of;
 * Organization is the work of running it.
 *
 * The icons come from `ENTITY_KINDS` wherever an item names a kind that exists
 * there, which is the authority on how a kind is marked. So the chip a
 * `:location[…]` renders as in a scene and the way into every location carry the
 * same icon, rather than the sidebar picking its own.
 *
 * **No counts.** The old ones were invented — #59 says so of the spike, and
 * `SpikeView`'s are the same numbers — and there is nothing to count for a
 * location or an agenda yet. A number nobody has counted is worse than no
 * number: it reads as data.
 */
/*
 * A function rather than a constant, because the copy in it is translated and
 * the locale is not known at import time: modules evaluate before `main.js`
 * resolves the language, so an array built at the top level would be built in
 * English and stay that way. Called from a computed in `App.vue`, which runs
 * after the app is up.
 */
export function sections() {
  return [
    {
      label: t('nav.resources'),
      context: 'resources',
      items: [
        { label: t('nav.pcs'), icon: 'pi-users' },
        { label: t('nav.npcs'), icon: ENTITY_KINDS.npc.icon },
        { label: t('nav.locations'), icon: ENTITY_KINDS.location.icon },
        { label: t('nav.factions'), icon: ENTITY_KINDS.faction.icon },
      ],
    },
    {
      label: t('nav.organization'),
      context: 'organization',
      items: [
        /*
         * These two pick their own, and are the exception to the rule above.
         *
         * The calendar goes to the agenda, which is the thing with dates in it —
         * what is coming, and when. Sessions are what has already been played, so
         * they take the list. `ENTITY_KINDS.session` keeps the calendar for the
         * chip a `:session[…]` renders as in prose, where it names one evening
         * rather than the record of all of them.
         */
        { label: t('nav.sessions'), icon: 'pi-list' },
        { label: t('nav.agenda'), icon: 'pi-calendar' },
      ],
    },
  ]
}

export const owlbear = {
  name: 'Owlbear',
  meta: 'Large monstrosity, unaligned',
  lines: [
    { label: 'Armor Class', value: '13 (natural armor)' },
    { label: 'Hit Points', value: '59', dice: '7d10 + 21' },
    { label: 'Speed', value: '40 ft.' },
  ],
  abilities: { str: 20, dex: 12, con: 17, int: 3, wis: 12, cha: 7 },
  details: [
    { label: 'Skills', value: 'Perception +3' },
    { label: 'Senses', value: 'darkvision 60 ft., passive Perception 13' },
    { label: 'Languages', value: '—' },
    { label: 'Challenge', value: '3 (700 XP)' },
  ],
  traits: [
    {
      name: 'Keen Sight and Smell',
      text: 'The owlbear has advantage on Wisdom (Perception) checks that rely on sight or smell.',
    },
  ],
  actions: [
    {
      name: 'Multiattack',
      text: 'The owlbear makes two attacks: one with its beak and one with its claws.',
    },
    {
      name: 'Beak',
      text: 'Melee Weapon Attack: +7 to hit, reach 5 ft., one creature. Hit: 10',
      dice: '1d10 + 5',
      after: 'piercing damage.',
    },
    {
      name: 'Claws',
      text: 'Melee Weapon Attack: +7 to hit, reach 5 ft., one target. Hit: 14',
      dice: '2d8 + 5',
      after: 'slashing damage.',
    },
  ],
  source: { work: 'SRD 5.1', page: 344 },
}
