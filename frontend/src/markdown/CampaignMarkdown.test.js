import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CampaignMarkdown from './CampaignMarkdown.vue'
import EntityTag from '../components/domain/EntityTag.vue'
import DiceChip from '../components/domain/DiceChip.vue'
import SourceRef from '../components/domain/SourceRef.vue'
import ReadAloud from '../components/domain/ReadAloud.vue'
import ProseColor from '../components/domain/ProseColor.vue'
import { ENTITY_KINDS } from '../components/domain/entityKinds.js'
import {
  DEFAULT_TIER,
  PROSE_HUES,
  PROSE_TIERS,
  proseColorClass,
} from '../design-system/proseColors.js'

/*
 * Three contracts are worth protecting here, in this order:
 *
 *   1. the directives become the real components, with the real props
 *   2. nothing a GM types can execute — the reason this renders vnodes rather
 *      than an HTML string
 *   3. anything the dialect does not understand stays visible on the page
 *
 * The second is the one that would be quietly lost in a refactor, so it is
 * tested in both modes.
 */

const render = (source, mode = 'block') => mount(CampaignMarkdown, { props: { source, mode } })

describe('CampaignMarkdown directives', () => {
  it('turns an entity directive into a tag carrying the kind and the label', () => {
    const wrapper = render('The party meets :npc[Fen Warden] on the causeway.')
    const tag = wrapper.findComponent(EntityTag)

    expect(tag.props()).toEqual({ kind: 'npc', label: 'Fen Warden' })
    expect(wrapper.text()).toContain('The party meets')
  })

  it('supports every kind the design system defines, and takes them from it', () => {
    for (const kind of Object.keys(ENTITY_KINDS)) {
      const wrapper = render(`:${kind}[Something]`)

      expect(wrapper.findComponent(EntityTag).props().kind, kind).toBe(kind)
    }
  })

  it('maps dice attributes onto props, with the result as a number', () => {
    const wrapper = render('She will pay :dice[2d6+3]{result=11 outcome=crit} gold.')

    expect(wrapper.findComponent(DiceChip).props()).toEqual({
      notation: '2d6+3',
      result: 11,
      outcome: 'crit',
    })
  })

  it('leaves an unrolled die unrolled rather than inventing a result', () => {
    const wrapper = render('Roll :dice[1d20] to notice the water.')

    expect(wrapper.findComponent(DiceChip).props()).toEqual({
      notation: '1d20',
      result: null,
      outcome: null,
    })
  })

  it('renders a source reference with its page', () => {
    const wrapper = render('Owlbears are aggressive :ref[SRD 5.1]{page=249}.')

    expect(wrapper.findComponent(SourceRef).props()).toEqual({ work: 'SRD 5.1', page: '249' })
  })

  it('renders a read-aloud block around its own content', () => {
    const wrapper = render(':::read-aloud\nThe water is waist-deep.\n:::')
    const block = wrapper.findComponent(ReadAloud)

    expect(block.exists()).toBe(true)
    expect(block.props().label).toBe('Read aloud')
    expect(block.text()).toContain('The water is waist-deep.')
  })

  it('lets a read-aloud block be relabelled for another system', () => {
    const wrapper = render(':::read-aloud{label="Boxed text"}\nWaist-deep.\n:::')

    expect(wrapper.findComponent(ReadAloud).props().label).toBe('Boxed text')
  })

  it('renders ordinary markdown around the directives', () => {
    const wrapper = render('# Greyfen\n\nA causeway of **black timber**.\n\n- one\n- two')

    expect(wrapper.find('h1').text()).toBe('Greyfen')
    expect(wrapper.find('strong').text()).toBe('black timber')
    expect(wrapper.findAll('li')).toHaveLength(2)
  })
})

/*
 * The prose palette (#147) — the first directive in the dialect that is
 * presentation and nothing else.
 */
describe('CampaignMarkdown colours', () => {
  it('colours a phrase with the hue and tier it was given', () => {
    const wrapper = render('The ward answers with :color[searing light]{hue=torch tier=bold}.')
    const mark = wrapper.findComponent(ProseColor)

    expect(mark.props()).toEqual({ hue: 'torch', tier: 'bold' })
    expect(mark.text()).toBe('searing light')
  })

  /*
   * An inline directive has room to draw itself where a block one does not, so
   * unlike `:::read-aloud` this survives the inline projection — a description
   * is exactly where a game master would expect the mark they made to hold.
   */
  for (const mode of ['block', 'inline']) {
    it(`renders as a coloured span in ${mode} mode`, () => {
      const wrapper = render('The door is :color[already open]{hue=slate}.', mode)

      expect(wrapper.findComponent(ProseColor).exists(), mode).toBe(true)
      expect(wrapper.find(`.${proseColorClass('slate', DEFAULT_TIER)}`).exists(), mode).toBe(true)
      expect(wrapper.text()).toContain('already open')
    })
  }

  it('offers every hue at every tier, and takes them from the palette', () => {
    for (const hue of Object.keys(PROSE_HUES)) {
      for (const tier of Object.keys(PROSE_TIERS)) {
        const wrapper = render(`:color[word]{hue=${hue} tier=${tier}}`)

        expect(wrapper.find(`.${proseColorClass(hue, tier)}`).exists(), `${hue} ${tier}`).toBe(true)
      }
    }
  })

  it('defaults the tier rather than requiring one', () => {
    expect(render(':color[word]{hue=moss}').findComponent(ProseColor).props().tier).toBe(
      DEFAULT_TIER,
    )
  })

  /* Marked-up words keep their marks: the children are the phrase, not a label
     for it. */
  it('keeps the markup inside a coloured phrase', () => {
    const wrapper = render(':color[the **ward** answers]{hue=wyrd}')

    expect(wrapper.findComponent(ProseColor).find('strong').text()).toBe('ward')
  })

  /*
   * No ARIA, deliberately. Every other directive announces a fact a listener
   * would otherwise miss — `EntityTag` says "(NPC)". This one has no fact:
   * "wyrd, bold" is a decision about ink, and reading it out is noise.
   */
  it('says nothing to a screen reader that a reader cannot see', () => {
    const span = render(':color[quiet]{hue=wyrd tier=bold}').findComponent(ProseColor)

    expect(span.attributes('aria-label')).toBeUndefined()
    expect(span.attributes('role')).toBeUndefined()
    expect(span.text()).toBe('quiet')
  })

  /* A token, resolved by a class — never a hex written into the DOM, which
     could not flip with the theme. */
  it('carries no inline style', () => {
    expect(
      render(':color[quiet]{hue=blood}').findComponent(ProseColor).attributes('style'),
    ).toBeUndefined()
  })

  for (const source of [
    ':color[word]{hue=chartreuse}',
    ':color[word]{hue=moss tier=whisper}',
    ':color[word]',
    // `in` would inherit a truthy answer from Object.prototype and resolve to a
    // class nothing has ever styled.
    ':color[word]{hue=constructor}',
  ]) {
    it(`refuses ${source} and shows it as its own text`, () => {
      const wrapper = render(`Before ${source} after.`)

      expect(wrapper.findComponent(ProseColor).exists()).toBe(false)
      expect(wrapper.text()).toContain(source)
    })
  }

  it('renders the leaf and container forms literally', () => {
    expect(render('::color[word]{hue=moss}').text()).toContain('::color')
    expect(render(':::color{hue=moss}\nword\n:::').text()).toContain(':::color')
    expect(render('::color[word]{hue=moss}').findComponent(ProseColor).exists()).toBe(false)
    expect(render(':::color{hue=moss}\nword\n:::').findComponent(ProseColor).exists()).toBe(false)
  })
})

describe('CampaignMarkdown renders ordinary markdown', () => {
  it('renders ordinary markdown around the directives', () => {
    const wrapper = render('# Greyfen\n\nA causeway of **black timber**.\n\n- one\n- two')

    expect(wrapper.find('h1').text()).toBe('Greyfen')
    expect(wrapper.find('strong').text()).toBe('black timber')
    expect(wrapper.findAll('li')).toHaveLength(2)
  })
})

describe('CampaignMarkdown degradation', () => {
  it('shows a misspelled directive rather than swallowing it', () => {
    const wrapper = render('The party meets :npx[Fen Warden] outside.')

    expect(wrapper.findComponent(EntityTag).exists()).toBe(false)
    expect(wrapper.text()).toContain(':npx[Fen Warden]')
    expect(wrapper.find('.markdown__unknown').exists()).toBe(true)
  })

  it('leaves a malformed directive as the text it is', () => {
    const wrapper = render('The party meets :npc[Fen Warden and leaves.')

    expect(wrapper.findComponent(EntityTag).exists()).toBe(false)
    expect(wrapper.text()).toContain(':npc[Fen Warden and leaves.')
  })

  it('refuses a directive used in the wrong form', () => {
    const wrapper = render(':::npc[Fen Warden]\nA warden.\n:::')

    expect(wrapper.findComponent(EntityTag).exists()).toBe(false)
    expect(wrapper.text()).toContain(':::npc')
    expect(wrapper.text()).toContain('A warden.')
  })

  it('refuses an attribute it cannot honour rather than mislabelling the chip', () => {
    // DiceChip renders any outcome it is given as "crit" or "fumble". A chip
    // reading "fumble" for `outcome=nat20` would be worse than showing the text.
    const wrapper = render('Rolls :dice[1d20]{outcome=nat20}.')

    expect(wrapper.findComponent(DiceChip).exists()).toBe(false)
    expect(wrapper.text()).toContain(':dice[1d20]{outcome=nat20}')
  })

  it('refuses a result that is not a number', () => {
    const wrapper = render('Rolls :dice[1d20]{result=high}.')

    expect(wrapper.findComponent(DiceChip).exists()).toBe(false)
    expect(wrapper.text()).toContain(':dice[1d20]{result=high}')
  })

  /*
   * `DIRECTIVES` is an ordinary object, so a bare lookup finds
   * `Object.prototype.constructor` for this name and asks a function what forms
   * it accepts. That threw, and a TypeError in the walker takes down the page
   * rather than the directive — the one failure this dialect exists to not have.
   */
  it('shows a directive named after a prototype member rather than crashing', () => {
    const wrapper = render('The party meets :constructor[Fen] outside.')

    expect(wrapper.text()).toContain(':constructor[Fen]')
    expect(wrapper.text()).toContain('The party meets')
  })

  it('keeps the contents of an unknown block', () => {
    const wrapper = render(':::spellbook\nMagic missile.\n:::')

    expect(wrapper.text()).toContain(':::spellbook')
    expect(wrapper.text()).toContain('Magic missile.')
  })
})

/*
 * The fallback promises the author's own text, and it used to rebuild that text
 * from the tree — which has already thrown away how the attributes were
 * written. Every case below round-tripped wrong, and none of the degradation
 * tests above caught it, because not one of them uses a quoted value.
 */
describe('CampaignMarkdown quotes the source rather than rebuilding it', () => {
  const cases = [
    [
      'a quoted value, whose spaces an unquoted one would not survive',
      ':npx[Fen]{label="the old man"}',
    ],
    [
      'the id and class shorthand, which the tree stores under other names',
      ':npx[Fen]{#gate .big}',
    ],
    ['a valueless attribute, indistinguishable in the tree from an empty one', ':npx[Fen]{flag}'],
    [
      'an explicitly empty value, indistinguishable in the tree from a bare flag',
      ':npx[Fen]{empty=""}',
    ],
    ['an attribute the dialect knows but refuses', ':dice[1d20]{result=high}'],
  ]

  for (const [what, source] of cases) {
    it(`gives back ${what}`, () => {
      expect(render(`Before ${source} after.`).text()).toContain(source)
    })
  }

  it('gives back what would otherwise become invalid syntax', () => {
    // The old rebuild wrote `{label=the old man}`. An unquoted value ends at the
    // first space, so what was on screen would parse differently from what
    // produced it — a writer copying the fallback back in got a second typo.
    const text = render(':npx[Fen]{label="the old man"}').text()

    expect(text).not.toContain('{label=the old man}')
  })

  it('renders a block directive’s body once, not once as source and once as prose', () => {
    const wrapper = render(':::spellbook{#gate}\nMagic missile.\n:::')
    const occurrences = wrapper.text().split('Magic missile.').length - 1

    expect(occurrences).toBe(1)
    expect(wrapper.text()).toContain(':::spellbook{#gate}')
  })

  it('does not print a closing fence the author never typed', () => {
    expect(render(':::spellbook\nMagic missile.').text()).not.toContain(':::\n:::')
    expect(render(':::spellbook\nMagic missile.\n:::').text()).toContain(':::')
  })

  it('quotes the source in inline mode too', () => {
    expect(render('Before :npx[Fen]{label="the old man"} after.', 'inline').text()).toContain(
      ':npx[Fen]{label="the old man"}',
    )
  })
})

describe('CampaignMarkdown cannot execute what it renders', () => {
  for (const mode of ['block', 'inline']) {
    it(`renders a script tag as text in ${mode} mode`, () => {
      const wrapper = render('Before <script>alert(1)</script> after.', mode)

      expect(wrapper.find('script').exists()).toBe(false)
      expect(wrapper.text()).toContain('<script>alert(1)</script>')
    })

    it(`renders an onerror image as text in ${mode} mode`, () => {
      const wrapper = render('<img src=x onerror="alert(1)">', mode)

      expect(wrapper.find('img').exists()).toBe(false)
      expect(wrapper.text()).toContain('onerror')
    })

    it(`refuses a javascript: link in ${mode} mode`, () => {
      const wrapper = render('[click me](javascript:alert(document.cookie))', mode)

      expect(wrapper.find('a').exists()).toBe(false)
      expect(wrapper.text()).toContain('click me')
    })
  }

  it('is not fooled by control characters in the scheme', () => {
    const wrapper = render('[click me](java\tscript:alert(1))')

    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('still renders the links a GM actually writes', () => {
    const wrapper = render('[the SRD](https://example.com/srd) and [a note](/notes/3)')
    const links = wrapper.findAll('a')

    expect(links.map((link) => link.attributes('href'))).toEqual([
      'https://example.com/srd',
      '/notes/3',
    ])
  })

  it('shows an image as its alt text, since assets have nowhere to live yet', () => {
    const wrapper = render('![A map of the marsh](https://example.com/map.png)')

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('A map of the marsh')
  })

  it('elides an image with no alt rather than putting its URL in the prose', () => {
    const wrapper = render('Look ![](https://example.com/map.png) here')

    expect(wrapper.text()).not.toContain('example.com')
    expect(wrapper.text()).toContain('[…]')
  })
})

describe('CampaignMarkdown inline mode', () => {
  it('still renders inline directives as components', () => {
    const wrapper = render('Prep for :location[Greyfen Marsh].', 'inline')

    expect(wrapper.findComponent(EntityTag).props().label).toBe('Greyfen Marsh')
  })

  it('flattens block structure, which a description has no room for', () => {
    const wrapper = render('# Act II\n\nThe war begins.', 'inline')

    expect(wrapper.find('h1').exists()).toBe(false)
    expect(wrapper.find('p').exists()).toBe(false)
    expect(wrapper.text()).toContain('Act II The war begins.')
  })

  it('keeps a read-aloud block’s words even though it cannot draw the box', () => {
    const wrapper = render(':::read-aloud\nThe water is cold.\n:::', 'inline')

    expect(wrapper.findComponent(ReadAloud).exists()).toBe(false)
    expect(wrapper.text()).toContain('The water is cold.')
  })

  it('separates flattened blocks rather than running them together', () => {
    const wrapper = render('One.\n\nTwo.', 'inline')

    expect(wrapper.text()).toBe('One. Two.')
  })

  it('renders into a span, so it can sit inside a line of interface', () => {
    expect(render('Anything', 'inline').element.tagName).toBe('SPAN')
  })
})

describe('CampaignMarkdown as a component', () => {
  it('renders one root element, so a caller can style the reading measure', () => {
    const wrapper = mount(CampaignMarkdown, {
      props: { source: 'A note.' },
      attrs: { class: 'prose' },
    })

    expect(wrapper.element.tagName).toBe('DIV')
    expect(wrapper.classes()).toContain('prose')
  })

  it('renders nothing for an empty body rather than failing', () => {
    expect(render('').text()).toBe('')
  })

  it('accepts only the modes it implements', () => {
    const { validator } = CampaignMarkdown.props.mode

    expect(validator('block')).toBe(true)
    expect(validator('inline')).toBe(true)
    expect(validator('plain')).toBe(false)
  })
})
