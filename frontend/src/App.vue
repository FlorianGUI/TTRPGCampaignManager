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
      <div class="page__main">
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
            habit rather than duty — nobody has come this way in a season, and the moss has taken
            the handrails. Travellers who stop to rest here report a sound under the boards that is
            not water.
          </p>
          <p>
            The party arrives at dusk. If they push on through the night, the marsh lights begin
            about an hour in; these are harmless, but the Wardens believe otherwise and any Warden
            escort will refuse to continue until dawn. A successful
            <strong>DC 14 Wisdom (Survival)</strong> check finds the dry hummock the old surveyors
            used as a camp — otherwise a long rest here is interrupted on a roll of
            <DiceChip notation="1d6" :result="2" /> or lower.
          </p>
        </div>

        <ReadAloud>
          <p>
            The causeway ends at a sunken arch, half-swallowed by the peat, its keystone carved with
            a face you cannot quite meet the eyes of. Water moves through the opening in a slow,
            deliberate way — not with the current, but against it, as though something below were
            breathing.
          </p>
        </ReadAloud>

        <div class="prose">
          <p>
            Anyone who studies the arch for a full minute and succeeds on a
            <strong>DC 16 Intelligence (History)</strong> check recognises the mason's mark of the
            drowned city of Ilmareth <SourceRef work="Cities of the Vale" :page="88" />. The Wardens
            will pay <EntityTag kind="item" label="200 gp" /> for a rubbing of it, no questions
            asked, and rather more if the party neglects to mention the sound.
          </p>
        </div>

        <div class="rule-fleuron" role="presentation">
          <span aria-hidden="true">❖</span>
        </div>

        <h2 class="page__section-heading">Encounter — the nesting pair</h2>

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

      <!--
        Reference rail. Today it holds the encounter's stat block; it's the seat
        for whatever entity is in focus, which is what an EntityTag click will
        drive once that lands.
      -->
      <aside class="page__rail" aria-label="Reference">
        <StatBlock :creature="owlbear" />
      </aside>
    </article>
  </AppShell>
</template>

<style scoped>
/*
 * Two columns across the whole page: narrative hard against the left edge,
 * reference rail hard against the right. Full bleed — the page spans the pane,
 * so no parchment is left blank at either edge.
 *
 * align-items: start keeps the rail at its natural height instead of stretching
 * it to the narrative's.
 */
.page {
  /*
   * Fluid so the rail stays secondary. Fixed at 26rem it came out nearly 50/50
   * with the narrative just above the stacking breakpoint, which reads as two
   * peer columns rather than text-plus-reference.
   */
  --rail-width: clamp(18rem, 24vw, 26rem);

  display: grid;
  grid-template-columns: minmax(0, 1fr) var(--rail-width);
  gap: var(--space-6);
  align-items: start;
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

/* min-width: 0 so long prose lines can't push the grid column wider than 1fr. */
.page__main {
  min-width: 0;
}

/*
 * --measure is deliberately not applied here: the narrative column fills its
 * grid track rather than clamping to 68ch, so no parchment is left blank.
 * The rail claws back most of the cost — lines land around 90 characters at
 * 1920 rather than the ~190 they ran at full bleed — but that is still above
 * what the type was tuned for. Restore `max-width: var(--measure)` here if the
 * trade stops being worth it.
 */
.page .prose {
  max-width: none;
}

.page__rolls,
.page__buttons {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

/* No room for two columns: the rail drops under the narrative it refers to. */
@media (max-width: 1100px) {
  .page {
    grid-template-columns: minmax(0, 1fr);
  }

  .page__rail {
    max-width: var(--rail-width);
  }
}
</style>
