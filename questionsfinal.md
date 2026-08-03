


Local Election Questionnaire — Claude-Optimized
Use this file as structured questionnaire content.

For each item:

Question is the voter-facing prompt.

1–2 is the short label for answers favoring Approach 1.

3 means neutral, unsure, or prefer a balance.

4–5 is the short label for answers favoring Approach 2.

Preserve the numbering and answer direction exactly.

1. Housing density
Question:
Should more apartments and duplexes be allowed?

1–2:
No—protect existing neighborhoods.

4–5:
Yes—allow more housing.

2. Affordable housing
Question:
Should developers be required to build affordable housing?

1–2:
Yes—require affordable units.

4–5:
No—use incentives instead.

3. Historic preservation
Question:
Should older buildings be easier to redevelop?

1–2:
No—protect historic buildings.

4–5:
Yes—make redevelopment easier.

4. Taxes and services
Question:
Should taxes rise to protect public services?

1–2:
Yes—maintain public services.

4–5:
No—keep taxes lower.

5. Business incentives
Question:
Should businesses receive local tax breaks?

1–2:
No—spend money elsewhere.

4–5:
Yes—attract businesses and jobs.

6. Government borrowing
Question:
Should local government borrow for major projects?

1–2:
No—save and pay gradually.

4–5:
Yes—complete projects sooner.

7. Minor offenses
Question:
How should minor offenses be handled?

1–2:
More arrests and prosecution.

4–5:
More treatment and alternatives.

8. Public-safety spending
Question:
Where should public-safety funding go?

1–2:
More police funding.

4–5:
More community and crisis programs.

9. Cash bail
Question:
Should people accused of nonviolent crimes have to pay bail?

1–2:
Yes—use cash bail or detention.

4–5:
No—use non-cash release options.

10. School funding
Question:
Should school funding rise if taxes must rise?

1–2:
Yes—fund schools more.

4–5:
No—keep school taxes lower.

11. School choice
Question:
Should families have more school choices?

1–2:
No—focus on neighborhood public schools.

4–5:
Yes—expand school-choice options.

12. Youth programs
Question:
Should local government spend more on youth programs?

1–2:
Yes—expand youth services.

4–5:
No—keep spending lower.

13. Transportation priorities
Question:
What should transportation funding prioritize?

1–2:
Roads, parking, and cars.

4–5:
Transit, bikes, and walking.

14. Infrastructure costs
Question:
Who should pay for roads and infrastructure?

1–2:
All taxpayers.

4–5:
Users and developers.

15. Environmental rules
Question:
Should development face stricter environmental rules?

1–2:
Yes—stronger environmental protections.

4–5:
No—fewer development restrictions.

16. Open land
Question:
Should open land be preserved or developed?

1–2:
Preserve parks and open space.

4–5:
Allow more private development.

17. Extreme-weather preparation
Question:
Should local government spend more to prepare for extreme weather?

1–2:
Yes—invest in protection now.

4–5:
No—prioritize other needs.

18. Neighborhood control
Question:
Who should control neighborhood decisions?

1–2:
City or county leaders.

4–5:
Neighborhoods and community boards.

19. Public input
Question:
Should major decisions require more public input?

1–2:
No—make decisions faster.

4–5:
Yes—allow more public input.

20. Elected boards
Question:
Should more local boards be elected?

1–2:
No—keep boards appointed.

4–5:
Yes—let voters choose.

Scoring & Verification Methodology

1. Scoring the seven-axis radar chart

The radar chart shows local-policy priorities, so each axis should represent how much the voter cares about that category, not the direction of their views (a radar axis communicates magnitude far better than a signed lean).

For each of the 7 categories, take the voter’s importance ratings (1–5) on every question in that category.

Average them, then rescale to 0–100:

category score = 100 × (average importance - 1) / 4

Plot the 7 category scores as the radar chart axes.

Optionally pair the radar chart with a secondary indicator (color scale, icon, or small paired bar chart) per axis showing the voter’s average directional lean in that category, since a single radar line cannot legibly encode both magnitude and sign.

2. Scoring the two-axis ideological compass

For each axis (economic; social/institutional), use only the questions with a non-zero weight on that axis:

Convert each answer (1–5) to a position value from -1 to +1:

position = (answer - 3) / 2

Multiply by that question’s axis weight (0–2) to get its contribution:

contribution = weight × position

Calculate the axis score:

axis score = sum(contributions) / sum(weights used), producing a result on the same −2..+2 scale as the individual weights. Rescale to −100..+100 for display if desired.

Recommendation: compute compass placement from policy position only, not importance. Reserve importance weighting for the compatibility score below — this keeps the compass comparable across voters regardless of how engaged they are with any one topic, while still letting personal priorities drive the candidate match.

3. Voter–candidate compatibility

Compatibility should be calculated per race, using only questions where a verified candidate position exists.

For each qualifying question, express both the voter's answer and the candidate's position on the same 1–5 scale (maximum possible distance = 4).

Per-question compatibility: compatibility = 1 - (abs(voter answer - candidate position) / 4).

Weight each question by the voter's importance rating (map 1–5 directly).

overall compatibility % = 100 × sum(weight × compatibility) / sum(weight).

Report the same weighted average broken out by radar category and by compass axis, so the site can explain why a match scored as it did, not just the final number.

Never substitute a neutral (3) or zero-weight value for a candidate position that is simply unknown — exclude that question from both the numerator and denominator for that candidate rather than silently penalizing or crediting them.

4. Hide questions that do not apply to the voter's jurisdiction

Several questions above are only meaningful where the referenced office or policy lever exists locally. Showing and scoring an inapplicable question misleads the voter about what local officials actually control, and it injects noise into both the radar chart and the compass. Maintain a jurisdiction-metadata table and use it to programmatically filter which questions are shown and scored for each voter; do not default a hidden question to neutral in scoring — simply exclude it, the same as an unanswered question. See questionnaire.md for full show-if conditions and office mappings per question.

5. Verifying candidate positions

This framework defines only the voter-facing questionnaire and scoring logic. No candidate positions should ever be invented, assumed, or inferred from party affiliation, endorsements, or general reputation. Populate candidate positions only from sourced, checkable material — official government records, direct candidate responses to this questionnaire, established third-party candidate questionnaires (League of Women Voters/Vote411, Ballotpedia's Candidate Connection), campaign materials and public statements, voting/decision histories for incumbents, and reputable local reporting. Attach a visible source citation and last-verified date to every candidate position shown to voters. If no credible source exists for a given question, display the position as "not available" and exclude that question from the compatibility calculation for that candidate rather than guessing. Re-verify positions close to each election. See questionnaire.md Section 5 for full detail.
