# ElectMatch — Business Plan

**Everett Smith · October 12, 2026**
Tompkins County pilot → commercial validation → national coverage

---

## 1. The pitch

I built a free voter tool with an institutional revenue model. ElectMatch helps
people compare local candidates on the issues they care about, with sources
they can check themselves — nonpartisan, down-ballot-focused, and explicit
about what it doesn't know. The first test is Tompkins County this fall. The
longer-term plan is national coverage, paid for by the organizations whose
audiences need a reliable local guide: newsrooms, civic groups, and
public-interest funders.

The product is live at **electmatch.com** today. I wrote the matching
algorithm, the AI research pipeline, and the frontend myself. What follows is
my own read of where it stands, grounded in the actual code and my real
spending to date — not a hedge about whether the work exists.

## 2. The problem

Down-ballot information is scattered across campaign pages, PACs, and local
news in incompatible formats, candidates get uneven coverage, and comparing
claims (vs. evidence, vs. silence) takes real research time most voters don't
have. ElectMatch's bet: ask office-specific questions (not one national
quiz), show the evidence behind every position with its confidence level, and
make missing information visible instead of guessing silently.

## 3. What's live, honestly

The site works end to end: ZIP code → local races → an evidence-backed
candidate comparison → a personalized match score → a "make a plan to vote"
calendar reminder.

**Home page** (electmatch.com, checked live today) — clean, nonpartisan
framing, a single ZIP input, and a live-product screenshot in the hero
itself (not a mockup): "Know who represents your community." Badges read
*Nonpartisan · Source-based · Local-election focused · Transparent about
uncertainty.* This is the one visual worth pulling into a pitch deck — grab
a fresh screenshot of the homepage once the 401 below is fixed.

**What I found testing it just now, live:** a ZIP search for 21401 sat on a
loading screen ("Searching for local elections — this can take up to 30
seconds") for 50+ seconds, then failed with a backend `401 authentication_error:
invalid x-api-key`. **The production Anthropic API key in the Render
environment is currently invalid** — the site cannot serve a single real
request right now. This is almost certainly fallout from the API key
rotation I just did after the old key was exposed and revoked; the new key
was set locally but evidently never updated in the Render dashboard's
environment variables. **This is the single most urgent fix, ahead of
anything else in this document** — a prospective buyer or distribution
partner hitting the live site today sees a 401 error, not a product.

## 4. What the real unit economics are (not the $1,500 guess)

This is the part the first draft of this plan got wrong, and it's wrong in a
specific, fixable way I can show from the code.

**How research actually runs today.** The moment a voter searches a ZIP code,
the frontend eagerly kicks off full AI research for *every* race found —
whether or not the voter ever opens that race
(`frontend/src/context/appData.tsx:158`). For each candidate, that means 12
Tavily searches (official site, Ballotpedia, VOTE411, news, social accounts,
etc. — `election_lookup.py:_candidate_search_queries`), one Claude Sonnet
synthesis call reading all that evidence, and — because a down-ballot
candidate essentially never has sourced coverage of all 20 questions — a
second Claude call to fill the rest with a labeled, non-scoring "unverified
estimate." If the voter then sets issue priorities, a third pass fires more
targeted searches (up to 10 more per candidate) and another Claude call for
any category still uncovered. **None of this is cached or stored.** There is
a Postgres database (`answer_storage.py`), but it only logs anonymized
questionnaire answers — candidate research is recomputed from scratch, with
live AI calls, on every single visit, for every race, for every voter.

**That's not a hypothetical cost. I already paid for it.** My recorded
spending to date is $422: $272 of that is Anthropic API usage from one block
of testing, on top of a steady-state baseline of Tavily $30/mo + Anthropic
$12/mo. A $272 bill from development-level traffic (a few dozen ZIP
searches during testing) is exactly what the architecture above predicts —
and it means the original plan's target of 150–300 *real* completed
comparisons this semester, each touching multiple races, would multiply that
well past where "$100 incremental AI/hosting" (the old estimate) was ever
a credible number.

**The fix is a precondition, not a nice-to-have.** Compute each race's
research once, have the reviewer approve it (which the product already
intends — see the published-rubric-and-review-before-publication plan), and
serve that to every voter from storage until the next scheduled refresh.
This is a bounded engineering task against infrastructure I already have
(Postgres is already provisioned for exactly this). It turns the cost curve
from *scales with voter traffic* into *fixed per race, amortized over
unlimited voters* — which is also just a more defensible editorial model: a
reviewer signs off on one answer per candidate, not on whatever a live model
call happens to return at 11pm to whichever voter is asking.

**Real cost per verified race, under the fixed (cached) architecture:**

| Item | Basis | Cost |
|---|---|---|
| AI research (one-time per race, cached) | ~2–4 candidates × (12–22 Tavily searches + 1–2 Claude calls) | ~$1–5 |
| Reviewer + founder labor | 12–14 hrs/race at $25/hr (my own logged estimate from earlier testing) | ~$300–350 |
| **Total true cost per verified race** | | **~$305–355** |

For a 5-race pilot, that's **~$1,525–$1,775 in true delivery cost before any
margin** — which is already at or above the $1,500 price the earlier draft
proposed. That price didn't just have thin margin; at realistic effort it
didn't clear cost at all. The earlier draft's own footnote said as much (a
$100 *loss* at 60 combined hours across 5 races, i.e. 12 hrs/race) — that
belongs in the main economics, not a footnote, because it's the actual
finding: **the business is "get the verified cost per race down," not "sell
guides at $1,500."**

## 5. What this is actually worth, against real comps

I already did this research — I just priced under it. BallotReady's
co-branded "Civic Center" product starts at **$5,000**. guides.vote
(donation-funded, fiscal-sponsor model) reports a cost of roughly **$3,500
per guide**. Those aren't apples-to-apples (different scope, different
production quality), but they're real reference points from organizations
solving the same problem, and my own delivery cost for a 5-race pilot is
already ~$1,500–1,800. Pricing at $1,500 was pricing *below my own labor
cost* and well under a third of the nearest real comp. There's no
information in that gap that a buyer would read as a discount — they'd read
it as an untested product with no sense of its own cost.

**Repriced first pilot: $2,500–$3,500 for a 5-race, one-geography guide**
(scope otherwise unchanged from the original plan: partner-branded guide,
reviewed profiles, defined updates, launch support, usage report). That's
roughly 1.7–2.3× the original ask, still meaningfully below BallotReady's
floor — appropriate for an unproven, single-founder product — but it clears
real delivery cost with 30–45% contribution margin instead of losing money
at a normal review workload.

## 6. Who pays, who uses it

| Role | Target | What's being validated |
|---|---|---|
| User | Voters researching unfamiliar local races | Less research effort, a clearer comparison |
| Buyer | Local publisher or civic org with an election budget | A reliable guide without building the tool |
| Distribution | Cornell Votes, LWV Tompkins, libraries | A useful resource for an audience they already have |
| Supporter | Public-interest grant program, disclosed coverage sponsor | Verified, independent local election information |
| Adviser | Cornell mentors, existing contacts (Alan Pentz, Ken Rother) | Pricing critique, introductions |

The user and the payer are different people by design — same as every
comp above. Nobody has cracked direct-to-voter payment for an election guide
used once or twice a year, and I'm not going to be the first.

## 7. How I'm going to make money

**Primary: institutional licensing, priced at real cost plus margin — not
donations, not ads, not a voter subscription.**

1. **B2B/B2B2C guide licensing** (lead). Sell a reviewed, branded local guide
   to the organization whose audience needs it — local newsrooms first (they
   have an existing election-coverage budget and a direct incentive),
   civic orgs and libraries second. Price per geography per cycle, once the
   caching fix makes marginal cost per *voter* near zero — the entire
   pricing logic above only works because cost becomes per-race, not
   per-visit.
2. **Grants and disclosed sponsorship** (secondary, blended with #1 — this is
   exactly how VOTE411 and guides.vote actually fund themselves, donation
   plus sponsorship, not pure commercial). Use this to cover the gap between
   what one local newsroom can pay and what full county coverage costs,
   never to replace the commercial ask. Disclose every sponsor; same
   questions and correction rights for every candidate regardless of who's
   funding coverage, so funding can never be read as buying a better match.
3. **Free voter layer stays free, forever** — it's the trust and
   distribution engine for #1 and #2, not a revenue line. A tip jar or
   premium-voter-tier is explicitly not the plan; it doesn't fit how often
   anyone actually uses this.
4. **Data/API licensing** — real optionality once the verified-position
   dataset is large and trusted (year 2+), not a near-term plan. Don't build
   for it yet.

**What I'm explicitly not doing:** investor equity at this stage. At a
$2,500–3,500 pilot price there's no venture-scale return story yet — that's
a cash-flow question, not an investment, and matches the earlier plan's own
conclusion to revisit VC only after repeat demand and real margins.

## 8. Near-term plan (this semester)

| Window | Focus | Output |
|---|---|---|
| Now | **Fix the production API key** (critical — site is down) | Working live site |
| Oct 12–23 | Implement research caching (Postgres), re-measure real per-race cost with logging | Confirmed $/race number, not an estimate |
| Oct 24–Nov 3 | Tompkins County test: 3–5 verified races, real voters | Usage data, review hours logged per race |
| Nov 4–22 | Qualify buyers, send 2–3 proposals at the repriced rate | Signed pilot or specific written commitment |
| Nov 23–Dec 15 | Deliver or follow up, write the case study | Results memo, repeat/no-repeat decision |

One honest caveat on scope: the November 3, 2026 Tompkins ballot is federal
and statewide — the races with the *most* existing coverage and the *least*
need for what ElectMatch does. The genuinely down-ballot offices (county
legislature, city council, town boards) are odd-year and land in November
2027. This fall's test proves the workflow, the review process, and the real
cost-per-race number — it does not yet prove the down-ballot thesis. Say
that plainly to anyone being pitched.

## 9. The ask

**Up to $500, spent on two things, not reviewer hours:** (1) fixing and then
load-testing the caching architecture so "cost per race" is a measured
number from real logs, not a guess, and (2) funding the first verified
Tompkins County race set under the new architecture. That answer — a real,
logged cost per verified race, under a cached architecture — is the one
number that determines whether $2,500–3,500 per pilot is a profitable
product or still underpriced. It's answerable this semester for a few
hundred dollars, same as the original instinct, just aimed at the number
that's actually load-bearing.

**Next gate:** a real cost-per-race number from logs, one paying or
committed buyer at the repriced rate, and a working production site with no
401s.
