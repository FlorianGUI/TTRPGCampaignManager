/*
 * Sample content for the spike's judgement surface.
 *
 * The prose is written for this repo. The owlbear stat block is from the
 * System Reference Document 5.1, © Wizards of the Coast LLC, used under
 * CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/legalcode) — it's here
 * because a design decision about dense tabular type has to be judged against
 * real source-book data, not lorem ipsum.
 */

export const sections = [
  /*
   * The Campaign section is gone from here: what a campaign holds is real now
   * (#88) and comes from `CampaignNav`, which reads the structure endpoint.
   * Library and Characters are still invented, and stay here until they are not.
   */
  {
    label: 'Library',
    context: 'library',
    items: [
      { label: 'Bestiary', icon: 'pi-eye', count: 318 },
      { label: 'Spells', icon: 'pi-sparkles', count: 477 },
      { label: 'Magic items', icon: 'pi-box', count: 362 },
      { label: 'Sources', icon: 'pi-book', count: 4 },
    ],
  },
  {
    label: 'Characters',
    context: 'characters',
    items: [
      { label: 'Party', icon: 'pi-users', count: 5 },
      { label: 'NPCs', icon: 'pi-user', count: 41 },
    ],
  },
]

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
