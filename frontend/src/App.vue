<script setup>
/*
 * SPIKE — the judgement surface for the design direction (issue #23).
 *
 * Not a styleguide and not a feature screen: one realistic page of prep notes,
 * built so the type, palette and ornament can be judged the way they'll
 * actually be read. Iterate on src/design-system/preset.js and look here.
 *
 * This whole file is expected to be replaced by real routes once the direction
 * is settled.
 */
import Button from 'primevue/button'
import AppShell from './components/AppShell.vue'
import StatBlock from './components/domain/StatBlock.vue'
import ReadAloud from './components/domain/ReadAloud.vue'
import DiceChip from './components/domain/DiceChip.vue'
import EntityTag from './components/domain/EntityTag.vue'
import SourceRef from './components/domain/SourceRef.vue'
import { sections, owlbear } from './content/sample.js'
</script>

<template>
  <AppShell :sections="sections" active="Session notes">
    <article class="page">
      <p class="label-smallcaps">Session 14 — prep</p>
      <h1>The Hollow Beneath Greyfen</h1>

      <p class="page__byline">
        <EntityTag kind="location" label="Greyfen Marsh" />
        <EntityTag kind="faction" label="The Fen Wardens" />
        <EntityTag kind="npc" label="Maerin Holt" />
        <EntityTag kind="session" label="Session 14" />
      </p>

      <hr class="rule-double" />

      <div class="prose prose--opener">
        <p>
          Three days east of the last waystone the road gives up entirely, and what remains is a
          causeway of black timber laid across standing water. The Wardens keep it passable out of
          habit rather than duty — nobody has come this way in a season, and the moss has taken the
          handrails. Travellers who stop to rest here report a sound under the boards that is not
          water.
        </p>
        <p>
          The party arrives at dusk. If they push on through the night, the marsh lights begin about
          an hour in; these are harmless, but the Wardens believe otherwise and any Warden escort
          will refuse to continue until dawn. A successful
          <strong>DC 14 Wisdom (Survival)</strong> check finds the dry hummock the old surveyors
          used as a camp — otherwise a long rest here is interrupted on a roll of
          <DiceChip notation="1d6" :result="2" /> or lower.
        </p>
      </div>

      <ReadAloud>
        <p>
          The causeway ends at a sunken arch, half-swallowed by the peat, its keystone carved with a
          face you cannot quite meet the eyes of. Water moves through the opening in a slow,
          deliberate way — not with the current, but against it, as though something below were
          breathing.
        </p>
      </ReadAloud>

      <div class="prose">
        <p>
          Anyone who studies the arch for a full minute and succeeds on a
          <strong>DC 16 Intelligence (History)</strong> check recognises the mason's mark of the
          drowned city of Ilmareth <SourceRef work="Cities of the Vale" :page="88" />. The Wardens
          will pay <EntityTag kind="item" label="200 gp" /> for a rubbing of it, no questions asked,
          and rather more if the party neglects to mention the sound.
        </p>
      </div>

      <div class="rule-fleuron" role="presentation">
        <span aria-hidden="true">❖</span>
      </div>

      <h2 class="page__section-heading">Encounter — the nesting pair</h2>

      <!--
        The stat block is a floated aside rather than a grid column (issue #25):
        prose reflows around it and continues under it once the aside ends, so a
        section can't leave a dead band bounded by the sidebar and the block.
      -->
      <div class="page__split">
        <StatBlock class="page__aside" :creature="owlbear" />

        <div class="prose">
          <p>
            Two owlbears have made the surveyors' camp their own and will defend the hummock with no
            interest whatsoever in negotiation. The larger of the pair is scarred across the beak —
            a detail worth mentioning, because
            <EntityTag kind="npc" label="Maerin Holt" /> lost a hand to it two winters ago and will
            recognise the animal on sight.
          </p>
          <p>
            Initiative order matters here: the causeway is one creature wide, so the party fights in
            file unless someone thinks to go into the water (difficult terrain,
            <DiceChip notation="1d4" /> cold damage per round).
          </p>
          <p class="page__rolls">
            <DiceChip notation="2d8 + 5" :result="19" outcome="crit" />
            <DiceChip notation="1d10 + 5" :result="7" />
            <DiceChip notation="1d20" :result="1" outcome="fumble" />
          </p>

          <p class="page__buttons">
            <Button label="Roll initiative" icon="pi pi-play" />
            <Button label="Add to session" icon="pi pi-plus" severity="secondary" outlined />
          </p>
        </div>
      </div>
    </article>
  </AppShell>
</template>

<style scoped>
.page {
  max-width: 72rem;
}

.page__byline {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.page__section-heading {
  margin-bottom: var(--space-4);
}

/*
 * Sized as measure + aside rather than a fraction of the page, so the text
 * beside the float still lands on --measure instead of being squeezed by
 * whatever width the aside happens to be.
 */
.page__split {
  --aside-width: 26rem;

  display: flow-root;
  max-width: calc(var(--measure) + var(--aside-width) + var(--space-6));
}

/*
 * The split's own width already sets the reading measure beside the float;
 * clamping the inner block as well would keep it clear of the aside entirely
 * and no text would ever reflow around it.
 */
.page__split .prose {
  max-width: none;
}

.page__aside {
  float: right;
  width: var(--aside-width);
  margin: 0 0 var(--space-5) var(--space-6);
}

.page__rolls,
.page__buttons {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* Below the split's own width there is no room to float: aside goes full width. */
@media (max-width: 1100px) {
  .page__aside {
    float: none;
    width: auto;
    max-width: var(--aside-width);
    margin: 0 0 var(--space-5);
  }
}
</style>
