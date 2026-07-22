# Internet-Backed Election Data System

## Data-System Overview

The platform should treat the public internet as a continuously changing election-information database.

Instead of depending on a single static dataset, the system should gather, organize, verify, update, and reconcile information from multiple public sources. These sources may include official boards of elections, state election agencies, municipal websites, candidate websites, public records, campaign-finance databases, local journalism, public meeting records, debate recordings, and other credible sources.

The system should not assume that any single source is complete or permanently accurate.

Election information changes frequently. Candidates may enter or leave races, filing statuses may change, district boundaries may be updated, election dates may move, campaign websites may change, and candidates may publish new policy positions.

The platform should therefore operate as a continuously updated research and verification system rather than as a one-time database import.

---

## Primary Data Principle

The internet is the underlying source environment, but the application should maintain its own structured, versioned, and verified internal database.

The system should:

1. Discover relevant information from public internet sources.
2. Extract the information into structured records.
3. Preserve the original source and retrieval date.
4. Compare the information against other sources.
5. Assign a confidence level.
6. Flag contradictions or missing information.
7. Recheck important records on a recurring basis.
8. Update the user-facing website only when the information meets the appropriate verification threshold.

The internal database should therefore function as a verified representation of public information rather than as an independent source of truth.

---

## Source Priority

Sources should be ranked according to authority and reliability.

### Tier 1: Official election sources

These should be treated as the primary source for determining whether an election, office, candidate, or ballot measure officially exists.

Examples:

* State boards of elections
* County boards of elections
* City or municipal election offices
* Secretaries of state
* Official candidate filing lists
* Official sample ballots
* Official election calendars
* Official district maps
* Official voter-information portals
* Official ballot-measure text
* Certified election results

Official election sources should take priority for:

* Candidate filing status
* Candidate withdrawal status
* Office names
* District identifiers
* Election dates
* Ballot order
* Party affiliation as officially filed
* Ballot measures
* Election results
* Registration deadlines
* Early-voting dates
* Polling-place information

### Tier 2: Official government records

Examples:

* Legislative voting records
* City council minutes
* County commission minutes
* School board minutes
* Government budgets
* Ordinances
* Public hearing records
* Government press releases
* Agency reports
* Public financial disclosures
* Ethics filings
* Campaign-finance records

These sources should be used to verify:

* Voting history
* Prior public-office experience
* Policy actions
* Budget decisions
* Public statements made during official proceedings
* Campaign donations and expenditures
* Government employment or appointments

### Tier 3: Direct candidate sources

Examples:

* Official campaign websites
* Official candidate questionnaires
* Campaign press releases
* Verified campaign social media
* Recorded campaign speeches
* Debate responses
* Public interviews
* Candidate newsletters
* Directly submitted policy statements

These sources should be used to identify:

* Policy positions
* Campaign priorities
* Biographical claims
* Endorsements
* Public commitments
* Responses to local issues

Candidate claims about filing status, election dates, voting records, or official government actions should still be checked against official records.

### Tier 4: Reputable independent sources

Examples:

* Established local newspapers
* Public radio
* Regional television news
* Nonprofit investigative journalism
* University election projects
* Recognized voter-guide organizations
* Reputable civic organizations
* Recorded public candidate forums

These sources may be used to:

* Confirm candidate statements
* Add context
* Find debate responses
* Identify disputes
* Summarize local issues
* Locate information missing from candidate websites

### Tier 5: Community and secondary sources

Examples:

* Local blogs
* Community forums
* Neighborhood associations
* Social media posts
* User submissions
* Archived pages
* Public discussion boards

These sources may be useful for discovering leads, but they should not normally be treated as verified evidence without confirmation from stronger sources.

---

## Source Registry

Every source used by the system should be stored in a source registry.

A source record should include:

```ts
interface SourceRecord {
  id: string;
  url: string;
  domain: string;
  title: string;
  publisher: string | null;
  sourceType:
    | "official-election"
    | "official-government"
    | "candidate-website"
    | "candidate-social-media"
    | "campaign-finance"
    | "voting-record"
    | "news"
    | "debate"
    | "candidate-questionnaire"
    | "public-meeting"
    | "community-source"
    | "user-submission"
    | "other";
  authorityTier: 1 | 2 | 3 | 4 | 5;
  jurisdictionId: string | null;
  candidateId: string | null;
  datePublished: string | null;
  dateFirstRetrieved: string;
  dateLastRetrieved: string;
  lastSuccessfulCheck: string | null;
  lastModifiedDetected: string | null;
  contentHash: string | null;
  archiveUrl: string | null;
  isActive: boolean;
  isAccessible: boolean;
  requiresManualReview: boolean;
  notes: string | null;
}
```

The system should keep a record even when a source later disappears.

Where legally and technically appropriate, the platform may preserve:

* A short excerpt
* A text snapshot
* A content hash
* Structured extracted claims
* An archived link
* The date and time of retrieval

The system should not republish full copyrighted articles.

---

## Core Election Data Models

The internal database should include structured records for jurisdictions, elections, offices, candidates, issues, positions, sources, evidence, and verification events.

### Jurisdiction

```ts
interface Jurisdiction {
  id: string;
  name: string;
  type:
    | "state"
    | "county"
    | "city"
    | "town"
    | "township"
    | "village"
    | "school-district"
    | "special-district"
    | "legislative-district"
    | "judicial-district"
    | "precinct";
  stateCode: string;
  parentJurisdictionId: string | null;
  officialWebsite: string | null;
  electionAuthorityUrl: string | null;
  geographicBoundarySource: string | null;
  lastVerifiedAt: string | null;
}
```

### Election

```ts
interface Election {
  id: string;
  name: string;
  jurisdictionId: string;
  electionType:
    | "general"
    | "primary"
    | "special"
    | "runoff"
    | "referendum"
    | "recall"
    | "nonpartisan";
  electionDate: string;
  registrationDeadline: string | null;
  earlyVotingStart: string | null;
  earlyVotingEnd: string | null;
  absenteeDeadline: string | null;
  officialElectionUrl: string | null;
  status:
    | "scheduled"
    | "filing-open"
    | "filing-closed"
    | "active"
    | "completed"
    | "cancelled"
    | "postponed";
  verificationStatus:
    | "unverified"
    | "partially-verified"
    | "verified"
    | "disputed";
  lastVerifiedAt: string | null;
}
```

### Office

```ts
interface Office {
  id: string;
  electionId: string;
  jurisdictionId: string;
  title: string;
  districtName: string | null;
  seatNumber: string | null;
  termLengthYears: number | null;
  numberOfSeats: number | null;
  isPartisan: boolean;
  responsibilitiesSummary: string | null;
  officialSourceId: string | null;
  lastVerifiedAt: string | null;
}
```

### Candidate

```ts
interface Candidate {
  id: string;
  officeId: string;
  fullName: string;
  normalizedName: string;
  party: string | null;
  incumbentStatus:
    | "incumbent"
    | "challenger"
    | "open-seat"
    | "unknown";
  filingStatus:
    | "filed"
    | "qualified"
    | "certified"
    | "withdrawn"
    | "disqualified"
    | "write-in"
    | "pending"
    | "unknown";
  campaignWebsite: string | null;
  photoUrl: string | null;
  biography: string | null;
  email: string | null;
  publicPhone: string | null;
  officialCandidateSourceId: string | null;
  firstDetectedAt: string;
  lastVerifiedAt: string | null;
  verificationStatus:
    | "unverified"
    | "partially-verified"
    | "verified"
    | "disputed";
}
```

### Issue

```ts
interface Issue {
  id: string;
  name: string;
  category: string;
  description: string;
  jurisdictionTypes: string[];
  active: boolean;
}
```

### Candidate Position

```ts
interface CandidatePosition {
  id: string;
  candidateId: string;
  issueId: string;
  summary: string;
  normalizedScore: -2 | -1 | 0 | 1 | 2 | null;
  positionType:
    | "explicit"
    | "voting-record"
    | "strongly-inferred"
    | "weakly-inferred"
    | "unknown";
  confidence:
    | "high"
    | "medium"
    | "low"
    | "unknown";
  evidenceCount: number;
  hasConflictingEvidence: boolean;
  firstDetectedAt: string;
  lastVerifiedAt: string | null;
  lastChangedAt: string | null;
  reviewerStatus:
    | "automated-only"
    | "pending-review"
    | "human-reviewed"
    | "rejected";
}
```

### Evidence Record

```ts
interface EvidenceRecord {
  id: string;
  candidatePositionId: string;
  sourceId: string;
  evidenceType:
    | "direct-quote"
    | "paraphrase"
    | "recorded-vote"
    | "questionnaire-answer"
    | "policy-page"
    | "debate-answer"
    | "public-statement"
    | "news-summary"
    | "social-media-post";
  excerpt: string | null;
  paraphrase: string | null;
  sourceDate: string | null;
  retrievedAt: string;
  supportsScore: -2 | -1 | 0 | 1 | 2 | null;
  extractionMethod:
    | "manual"
    | "rule-based"
    | "ai-assisted";
  extractionConfidence: number | null;
  verifiedByHuman: boolean;
  notes: string | null;
}
```

---

## Internet Discovery Process

The system should discover relevant election sources through a layered process.

### Step 1: Identify the jurisdiction

Use the user’s ZIP code or address to determine all relevant jurisdictions.

Possible methods include:

* Government geographic-information systems
* Census geographic data
* State district maps
* County GIS portals
* Municipal boundary files
* School-district maps
* Google Civic Information API
* Other validated civic-geography services

The address should be converted into jurisdiction identifiers and then discarded unless the user explicitly chooses to save it.

### Step 2: Locate the official election authority

For each jurisdiction, locate the relevant:

* State election website
* County election office
* Municipal clerk
* Board of elections
* School-district election page
* Special-district election page

The system should maintain a verified directory mapping jurisdictions to official election authorities.

### Step 3: Discover current elections

Search official sources for:

* Upcoming election dates
* Filing calendars
* Candidate lists
* Sample ballots
* Office lists
* Ballot measures
* Notices of withdrawal
* Election cancellations
* Runoff requirements

### Step 4: Discover candidate sources

For every candidate, locate:

* Official campaign website
* Campaign social media
* Candidate filing record
* Candidate biography
* Candidate questionnaire responses
* Debate appearances
* News interviews
* Voting record
* Campaign-finance filings

Candidate identity matching must account for:

* Middle initials
* Name suffixes
* Nicknames
* Alternate spellings
* Duplicate names
* Multiple candidates with similar names

### Step 5: Discover issue positions

The system should search for statements related to locally relevant issues.

Searches may combine:

* Candidate name
* Office
* Jurisdiction
* Issue name
* Local terminology
* Debate name
* Candidate questionnaire
* Relevant ordinance or policy proposal

Example searches:

```text
"Candidate Name" housing zoning
"Candidate Name" school funding
"Candidate Name" police budget
"Candidate Name" property tax
"Candidate Name" city council debate
"Candidate Name" candidate questionnaire
site:candidatewebsite.com transportation
site:county.gov "Candidate Name"
```

The system should not rely on general web search alone. It should first inspect known official and direct candidate sources.

---

## Continuous Update Process

The platform should continuously recheck important information.

Suggested update frequency:

### High-priority records

Check daily or more frequently during active election periods:

* Candidate filing lists
* Candidate withdrawals
* Candidate qualification status
* Election dates
* Sample ballots
* Polling information
* Official election notices
* Election results

### Medium-priority records

Check every few days or weekly:

* Candidate websites
* Policy pages
* Candidate questionnaires
* Debate schedules
* Campaign press releases
* Campaign-finance filings
* Local-news election coverage

### Lower-priority records

Check weekly or monthly:

* Candidate biographies
* Historical voting records
* Office descriptions
* Archived government records
* General jurisdiction information

The update schedule should become more frequent as election day approaches.

The system may use:

* Scheduled crawling
* RSS feeds
* Public APIs
* Sitemap monitoring
* Page-change detection
* Content hashes
* Official downloadable files
* Structured data feeds
* Manual researcher review

---

## Change Detection

Every retrieved page or document should be checked for meaningful changes.

The system may compare:

* Page content hash
* Structured fields
* Publication date
* Candidate list length
* Filing status
* Issue-position text
* Document revision date
* Newly added links
* Removed content

When a change is detected, create a change event.

```ts
interface ChangeEvent {
  id: string;
  entityType:
    | "jurisdiction"
    | "election"
    | "office"
    | "candidate"
    | "candidate-position"
    | "source";
  entityId: string;
  changeType:
    | "created"
    | "updated"
    | "removed"
    | "status-change"
    | "conflict-detected"
    | "source-unavailable";
  previousValue: unknown;
  newValue: unknown;
  detectedAt: string;
  sourceId: string | null;
  requiresReview: boolean;
}
```

Important changes should trigger manual review.

Examples:

* Candidate removed from official filing list
* Election date changed
* Candidate policy page deleted
* Candidate reverses a position
* Two official sources disagree
* A candidate is disqualified
* A race is cancelled
* A ballot measure is amended

The system should not silently overwrite important historical information.

---

## Version History

Important records should be versioned.

The platform should preserve previous versions of:

* Candidate filing status
* Election dates
* Candidate positions
* Candidate biographies
* Policy statements
* Ballot-measure text
* Source excerpts
* Confidence ratings

A user-facing profile may show the current verified version, while administrators can inspect the record history.

```ts
interface EntityVersion {
  id: string;
  entityType: string;
  entityId: string;
  versionNumber: number;
  data: unknown;
  validFrom: string;
  validUntil: string | null;
  changedBy:
    | "automated-process"
    | "human-reviewer"
    | "candidate-submission"
    | "user-correction";
  changeReason: string | null;
}
```

---

## Verification Rules

Information should be verified according to the type of claim.

### Candidate existence

A candidate should be marked as verified only when confirmed by an official filing list, certified ballot, or official election authority.

A campaign website alone is not sufficient to prove that a candidate has qualified for the ballot.

### Election date

Election dates should be confirmed through an official state, county, or municipal election authority.

### Candidate policy position

A position may be marked as high confidence when supported by:

* Direct candidate policy page
* Candidate questionnaire
* Recorded debate answer
* Official public statement
* Recorded legislative vote directly relevant to the issue

A position may be marked as medium confidence when supported by:

* Reputable news interview
* Multiple consistent public statements
* Clear but indirect campaign material

A position should be marked low confidence when:

* The statement is vague
* The evidence is old
* The source is secondary
* The position requires interpretation
* Only one weak source exists

### Candidate biography

Biographical claims should be checked against:

* Official candidate filings
* Employer or organization websites
* Government records
* Professional licenses
* Official biographies
* Reputable news profiles

### Endorsements

Endorsements should be verified through the endorsing organization or person whenever possible.

### Campaign finance

Campaign-finance information should come from official disclosure systems or official filing documents.

---

## Multi-Source Verification

Important claims should be confirmed by more than one source when possible.

Examples:

* Candidate filing status:

  * Official candidate list
  * Certified sample ballot

* Candidate policy position:

  * Official campaign statement
  * Debate response or candidate questionnaire

* Prior office:

  * Government biography
  * Election record or meeting record

* Endorsement:

  * Candidate announcement
  * Endorsing organization announcement

A single authoritative official source may be sufficient for basic administrative facts.

For disputed or politically sensitive claims, the system should seek at least two independent sources.

---

## Contradiction Handling

When sources conflict, the system should not choose a version silently.

It should create a contradiction record.

```ts
interface DataConflict {
  id: string;
  entityType: string;
  entityId: string;
  fieldName: string;
  sourceIds: string[];
  conflictingValues: unknown[];
  detectedAt: string;
  status:
    | "open"
    | "under-review"
    | "resolved"
    | "unresolved";
  resolution: string | null;
  resolvedAt: string | null;
}
```

Examples:

* One official page lists a candidate as active while another lists the candidate as withdrawn.
* A candidate website states support for a policy while a recent debate answer appears to oppose it.
* News coverage reports an endorsement that the endorsing organization denies.
* Two government pages list different election dates.

Until resolved, the user-facing interface should display an uncertainty warning.

For policy contradictions, the platform should display both statements and their dates.

A newer statement should not automatically erase an older one. It may indicate that the candidate changed position.

---

## Staleness and Expiration

Every record should have a freshness status.

Possible states:

* Current
* Recently verified
* Needs recheck
* Stale
* Source unavailable
* Disputed

Suggested rules:

* Candidate filing status becomes stale quickly during filing season.
* Election dates should be rechecked frequently.
* Candidate positions may remain valid but should be rechecked after major debates, questionnaires, or platform updates.
* Old candidate websites should not be assumed to represent current positions.
* Positions from prior election cycles should be clearly labeled as historical.

The user interface should show:

* Last verified date
* Source date
* Whether information is from the current election cycle
* Whether more recent information may exist

---

## AI-Assisted Research

AI may be used to assist with:

* Finding relevant pages
* Extracting candidate names
* Extracting office names
* Summarizing policy statements
* Classifying statements by issue
* Identifying possible contradictions
* Suggesting numerical position values
* Detecting duplicate candidates
* Detecting page changes
* Generating research queues

AI output must not automatically become verified public data.

AI-extracted information should be stored with:

* Source URL
* Exact supporting text
* Extraction confidence
* Model or process used
* Retrieval timestamp
* Review status

Low-confidence or politically sensitive extractions should require human review.

The system should never publish an unsupported AI-generated position.

---

## Human Review

The system should include an administrative review queue.

Reviewers should be able to:

* Confirm candidate identity
* Confirm election details
* Review extracted policy positions
* Adjust confidence levels
* Resolve contradictions
* Reject unreliable evidence
* Add missing sources
* Mark records stale
* Approve corrections
* Restore previous versions
* View change history

Priority should be given to:

* Upcoming elections
* Contested races
* Candidate withdrawals
* Disputed facts
* Low-confidence matches
* User-reported errors
* Sources that have changed
* AI-generated position classifications

---

## Candidate and Public Corrections

Candidates, campaigns, election officials, journalists, and users should be able to submit corrections.

A correction submission should include:

```ts
interface CorrectionSubmission {
  id: string;
  entityType: string;
  entityId: string;
  submitterName: string | null;
  submitterRole: string | null;
  submitterEmail: string | null;
  claimedError: string;
  proposedCorrection: string;
  supportingUrls: string[];
  submittedAt: string;
  status:
    | "received"
    | "under-review"
    | "accepted"
    | "partially-accepted"
    | "rejected";
  reviewerNotes: string | null;
}
```

Corrections should not be accepted only because a candidate requests them.

They must be supported by evidence.

The platform should keep an audit trail of accepted and rejected corrections.

---

## Data Completeness

The platform should calculate coverage metrics for every race.

Possible metrics include:

* Percentage of candidates verified
* Percentage of candidates with a campaign website
* Percentage of candidate positions documented
* Number of issues with evidence
* Number of unresolved conflicts
* Average data confidence
* Date of last full review

Example:

```ts
interface RaceCoverage {
  officeId: string;
  candidateCount: number;
  verifiedCandidateCount: number;
  issuesTracked: number;
  documentedPositionCount: number;
  possiblePositionCount: number;
  coveragePercentage: number;
  averageConfidence: number;
  unresolvedConflictCount: number;
  lastFullReviewAt: string | null;
}
```

Users should be warned when a race has limited information.

A candidate should not receive an artificially low alignment score because less information is available about them.

---

## Matching-System Data Rules

Only sufficiently supported candidate positions should affect the matching score.

Recommended rules:

* High-confidence explicit positions: full weight
* Medium-confidence positions: reduced weight
* Low-confidence positions: display but exclude by default
* Unknown positions: exclude
* Conflicting positions: exclude until reviewed or show as unresolved
* Historical positions: exclude unless confirmed for the current race
* Party-based assumptions: never include
* Endorsement-based assumptions: never include without direct evidence

The result should display both:

* Alignment score
* Evidence coverage score

The system should explain when a result is based on incomplete information.

---

## Search and Retrieval Architecture

The application should separate internet retrieval from user-facing application logic.

Suggested components:

```text
Source Discovery Service
        |
        v
Web and API Retrieval Layer
        |
        v
Content Extraction Layer
        |
        v
Entity Resolution Layer
        |
        v
Verification and Conflict Detection
        |
        v
Human Review Queue
        |
        v
Versioned Election Database
        |
        v
Public API
        |
        v
Website and Questionnaire
```

### Source Discovery Service

Finds likely official and candidate sources.

### Retrieval Layer

Downloads pages, APIs, PDFs, feeds, and structured files.

### Content Extraction Layer

Converts unstructured content into candidate, election, and policy records.

### Entity Resolution Layer

Determines which records refer to the same jurisdiction, election, office, or candidate.

### Verification Layer

Applies authority, confidence, freshness, and contradiction rules.

### Review Queue

Allows humans to approve, reject, or edit uncertain records.

### Versioned Database

Stores current and historical structured data.

### Public API

Provides verified data to the website without exposing internal research systems.

---

## API Design

The public application may use endpoints such as:

```text
GET /api/jurisdictions/lookup?zip=21620

GET /api/elections?jurisdictionId=jurisdiction_123

GET /api/elections/:electionId/offices

GET /api/offices/:officeId/candidates

GET /api/candidates/:candidateId

GET /api/candidates/:candidateId/positions

GET /api/candidates/:candidateId/sources

GET /api/offices/:officeId/comparison

POST /api/alignment/calculate

POST /api/corrections
```

Internal administrative endpoints may include:

```text
POST /api/admin/sources/discover

POST /api/admin/sources/recheck

POST /api/admin/extractions/review

POST /api/admin/conflicts/resolve

POST /api/admin/candidates/merge

POST /api/admin/positions/approve
```

---

## Auditability

Every user-facing fact should be traceable.

For each fact, the system should be able to answer:

* Where did this information come from?
* When was it published?
* When was it retrieved?
* When was it last checked?
* Was it extracted automatically?
* Was it reviewed by a human?
* Has it changed?
* Are there conflicting sources?
* Why was this confidence rating assigned?

This audit trail is essential because the platform may influence voting decisions.

---

## Failure Handling

The system should handle incomplete or unavailable data honestly.

Examples:

### Official website unavailable

Display the most recently verified information with a warning that the official source is temporarily unavailable.

### No candidate website

Continue searching official filings, debates, local news, questionnaires, and public records.

### No policy information

Display:

> No documented position found.

Do not generate or infer a position.

### Conflicting candidate statements

Display both statements, their dates, and an unresolved-position warning.

### Recently changed ballot

Prioritize the official election source and trigger immediate re-verification.

### Limited local internet coverage

Allow community members, candidates, journalists, and officials to submit sources for review.

---

## Initial Prototype Implementation

The first version does not need to crawl the entire internet.

It should establish the architecture required for future live data collection.

The prototype should include:

* A source registry
* Mock official election sources
* Mock candidate sources
* Source authority tiers
* Retrieval timestamps
* Confidence values
* Verification statuses
* Change history
* Contradiction examples
* Candidate-position evidence
* Data freshness indicators
* An administrative review interface
* A simulated update process
* Clear code boundaries for future web-search, API, and crawling services

Use fictional data in the prototype, but structure all models and services as though they will later operate on real internet data.

---

## Final Operating Principle

The platform should never present itself as possessing perfect or complete election information.

Its purpose is to create the most accurate, transparent, and current structured representation possible from publicly available information.

The system should continuously:

* Search
* Retrieve
* Compare
* Verify
* Update
* Preserve history
* Display uncertainty
* Invite corrections

The website’s reliability should come not from claiming certainty, but from showing evidence, using authoritative sources, detecting change, and making the verification process visible.
