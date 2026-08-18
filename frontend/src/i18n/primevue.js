/*
 * PrimeVue's own strings, in the app's language.
 *
 * The components emit copy of their own — a dialog's close button is labelled
 * `aria.close`, an empty `Select` says `emptyMessage` — and none of it passes
 * through `t`. Left alone it stays English underneath a French page, which is
 * the half-translated app #87 is about, so it is configured in the same breath
 * as everything else (`main.js`).
 *
 * **A partial object on purpose.** PrimeVue deep-merges what it is given over
 * its defaults, so this only has to carry what the app's components can
 * actually say — Button, Dialog, Drawer, Menu, Select, Toast, and the two text
 * inputs. Translating a date picker's month names for a date picker nobody has
 * written would be inventing the answer to a question the app has not asked;
 * whatever is added next brings its own strings with it.
 */
const FRENCH = {
  cancel: 'Annuler',
  clear: 'Effacer',
  apply: 'Appliquer',
  choose: 'Choisir',
  accept: 'Oui',
  reject: 'Non',
  emptyMessage: 'Aucune option disponible',
  emptySearchMessage: 'Aucun résultat',
  emptyFilterMessage: 'Aucun résultat',
  emptySelectionMessage: 'Aucun élément sélectionné',
  aria: {
    close: 'Fermer',
    previous: 'Précédent',
    next: 'Suivant',
    navigation: 'Navigation',
    listLabel: 'Liste d’options',
    selectAll: 'Tous les éléments sélectionnés',
    unselectAll: 'Tous les éléments désélectionnés',
  },
}

const LOCALES = { fr: FRENCH }

/*
 * English is PrimeVue's own default, so it asks for nothing: an empty object
 * merges to exactly the defaults rather than to a second copy of them that
 * could fall behind the library's.
 */
export function primevueLocale(locale) {
  return LOCALES[locale] ?? {}
}
