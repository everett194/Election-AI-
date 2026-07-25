Nonpartisan Local-Election Questionnaire — Design Framework
20 questions, a seven-axis radar chart, a two-axis ideological compass, and voter–candidate compatibility scoring.
This file defines only the questionnaire and scoring logic. It contains no candidate positions — none should ever be invented, assumed, or inferred. See Section 5 for how to source real candidate positions.

Purpose
This framework generates the questionnaire used by a local-election information site. It defines the 20 questions voters answer, how those answers populate a seven-axis radar chart of local-policy priorities, how they place a voter on a two-axis ideological compass, and how a voter's answers should be compared against verified candidate positions to produce a compatibility score.
Scoring convention (applies to every question below)
Every question uses the same five-point policy-position scale: 1 = Strongly favor Approach 1, 2 = Somewhat favor Approach 1, 3 = Neutral / unsure / prefer a balance, 4 = Somewhat favor Approach 2, 5 = Strongly favor Approach 2.
Every question also carries a separate five-point importance scale, collected once per question: 1 = Not important to me, 2 = Slightly important, 3 = Moderately important, 4 = Very important, 5 = One of my top priorities.
For every question, Approach 1 is written as the pole associated with greater public investment/regulation (economic axis) or greater enforcement/authority/centralization (social axis). Approach 2 is written as the pole associated with markets/private development/lower taxation (economic axis) or civil liberties/rehabilitation/decentralization/community participation (social axis).
econ_weight and social_weight below are magnitudes from 0 to 2 representing how strongly a question loads on each compass axis. 0 means the question is radar-only (categorization/priority signal), not used for the compass. Because Approach 1 is always the negative pole and Approach 2 is always the positive pole, the signed contribution of a fully "strongly favor" answer is -weight (Approach 1) or +weight (Approach 2) — this realizes the full −2..+2 scoring range without repeating a sign per row.
Radar categories: housing, taxes, safety, education, transportation, environment, accountability.

Summary table
#
id
Category
econ_weight
social_weight
Question
1
housing_zoning_density
housing
2
0
When it comes to zoning in residential neighborhoods, which approach should the city or county prioritize?
2
housing_affordable_mandate
housing
1
0
How should local government try to increase the supply of affordable housing?
3
housing_preservation_redevelopment
housing
2
0
Should the city or county make it easier or harder to redevelop older buildings and lots, including through historic-preservation or design-review rules?
4
taxes_shortfall
taxes
2
0
If local government faced a budget shortfall, which should it prioritize?
5
taxes_business_incentives
taxes
2
0
Should local government offer tax breaks or subsidies to attract new businesses and development?
6
taxes_capital_debt
taxes
1
0
How should local government pay for large capital projects, such as a new fire station or major road project?
7
safety_lowlevel_response
safety
0
2
How should local government respond to low-level, nonviolent offenses such as minor drug possession or public disorder?
8
safety_police_funding
safety
0
2
Should local government increase or decrease funding and staffing for police relative to other public-safety approaches?
9
safety_bail_pretrial
safety
0
2
How should the local criminal justice system handle pretrial release for people awaiting trial on non-violent charges?
10
education_funding_levy
education
2
0
Should local school funding be increased, even if it requires higher local property taxes or a school levy?
11
education_choice_vs_traditional
education
1
1
Should local education policy prioritize expanding school-choice options, or prioritize investment in traditional neighborhood public schools?
12
education_youth_services
education
1
0
Should local government expand funding for youth services outside of school, such as after-school programs, libraries, or recreation centers?
13
transportation_mode_priority
transportation
0
0
When local government has limited transportation funding, which should it prioritize?
14
transportation_funding_mechanism
transportation
1
0
How should local road and infrastructure improvements be funded?
15
environment_regulation_cost
environment
2
0
Should local government adopt stricter environmental rules for local development and business, even if it raises costs for developers or businesses?
16
environment_parks_vs_development
environment
2
0
When land becomes available, should local government prioritize acquiring or preserving it as parks and open space, or prioritize allowing private development?
17
environment_climate_resilience
environment
2
0
Should local government invest in climate-resilience projects, such as flood control, stormwater upgrades, or extreme-heat preparedness, even if it requires new spending or fees?
18
accountability_neighborhood_control
accountability
0
2
For decisions that affect specific neighborhoods, such as zoning changes or new development, how much power should neighborhoods or community boards have relative to citywide government?
19
accountability_public_input
accountability
0
2
Should local government be required to hold more extensive public-comment periods before major decisions, even if it slows down decision-making?
20
accountability_elected_vs_appointed
accountability
0
1
Should more local oversight bodies, such as police oversight boards, planning commissions, or utility boards, be filled by direct election rather than appointment?



Full question detail
Q1 — housing_zoning_density
Category: housing
Question: When it comes to zoning in residential neighborhoods, which approach should the city or county prioritize?
Approach 1: Maintain current limits on multi-family and higher-density housing to preserve existing neighborhood character.
Approach 2: Loosen zoning restrictions to allow more apartments, duplexes, and multi-family homes to be built.
Offices involved: City council; planning/zoning board; county government (unincorporated areas)
econ_weight: 2 · social_weight: 0
Why useful: Zoning density is one of the highest-leverage, most consistently local decisions and cleanly separates market-oriented from restriction-oriented candidates.
Show-if: Show wherever the jurisdiction holds residential zoning authority (nearly all cities/counties).
Q2 — housing_affordable_mandate
Category: housing
Question: How should local government try to increase the supply of affordable housing?
Approach 1: Require developers to set aside a share of affordable units in new residential projects (mandatory inclusionary zoning).
Approach 2: Rely on tax incentives, expedited permitting, or public-private partnerships to encourage, not require, affordable units.
Offices involved: City council; county housing authority; planning board
econ_weight: 1 · social_weight: 0
Why useful: Distinguishes candidates who prefer regulatory mandates from those who prefer market incentives to reach similar housing goals.
Show-if: Applicable in all jurisdictions; importance weighting naturally reduces impact where affordability is not an active concern.
Q3 — housing_preservation_redevelopment
Category: housing
Question: Should the city or county make it easier or harder to redevelop older buildings and lots, including through historic-preservation or design-review rules?
Approach 1: Strengthen preservation and design-review requirements to protect existing buildings and neighborhood character.
Approach 2: Ease preservation and design-review requirements to make redevelopment and new construction faster and less costly.
Offices involved: City council; historic preservation commission; planning/zoning board
econ_weight: 2 · social_weight: 0
Why useful: Surfaces a concrete, recurring local fight distinct from raw zoning density that often splits candidates who otherwise agree on housing supply.
Show-if: Show only where a historic district, design-review board, or active redevelopment debate exists; hide elsewhere.
Q4 — taxes_shortfall
Category: taxes
Question: If local government faced a budget shortfall, which should it prioritize?
Approach 1: Raise local taxes or fees to maintain current service levels.
Approach 2: Cut spending or reduce services to avoid raising local taxes or fees.
Offices involved: City council; county commission/board; mayor; school board (levies)
econ_weight: 2 · social_weight: 0
Why useful: The clearest, most direct test of the taxation-versus-spending tradeoff at the core of the economic axis.
Show-if: Applicable in nearly all jurisdictions with local taxing authority.
Q5 — taxes_business_incentives
Category: taxes
Question: Should local government offer tax breaks or subsidies to attract new businesses and development?
Approach 1: Limit or reduce tax breaks and subsidies for businesses, relying on general revenue for community priorities instead.
Approach 2: Continue or expand tax breaks and incentives to attract businesses and development.
Offices involved: City council; county commission; economic development authority; mayor
econ_weight: 2 · social_weight: 0
Why useful: Development incentives are a frequent, high-dollar local decision that separates candidates on the market-versus-public-investment spectrum.
Show-if: Most relevant where the locality has an active economic-development program; hide only if no such authority exists.
Q6 — taxes_capital_debt
Category: taxes
Question: How should local government pay for large capital projects, such as a new fire station or major road project?
Approach 1: Fund projects gradually through the regular budget or reserves, even if it means delaying projects.
Approach 2: Borrow through bonds or debt financing to complete projects sooner, even if it costs more in interest over time.
Offices involved: City council; county commission; school board (bond measures)
econ_weight: 1 · social_weight: 0
Why useful: Distinguishes fiscally cautious candidates from growth-oriented candidates willing to use debt; a recurring practical budget decision.
Show-if: Applicable in nearly all jurisdictions with capital budgeting or bonding authority.
Q7 — safety_lowlevel_response
Category: safety
Question: How should local government respond to low-level, nonviolent offenses such as minor drug possession or public disorder?
Approach 1: Prioritize arrest, citation, and prosecution as the primary response.
Approach 2: Prioritize diversion programs, treatment referrals, or civil citations instead of arrest and prosecution.
Offices involved: Police department/chief; sheriff; city council (police policy); prosecutor/district attorney
econ_weight: 0 · social_weight: 2
Why useful: One of the clearest tests of the enforcement-versus-rehabilitation dimension, and a real point of variation among sheriffs, prosecutors, and councils.
Show-if: Applicable wherever local law enforcement or prosecutorial authority exists (nearly universal).
Q8 — safety_police_funding
Category: safety
Question: Should local government increase or decrease funding and staffing for police relative to other public-safety approaches?
Approach 1: Increase police funding and staffing as the priority.
Approach 2: Redirect funding toward non-police approaches, such as mental-health crisis teams or violence-interruption programs.
Offices involved: City council; mayor; county commission; sheriff; police chief
econ_weight: 0 · social_weight: 2
Why useful: Captures the budget-allocation version of the enforcement-versus-alternatives tradeoff, complementing the policy-response question above.
Show-if: Most meaningful where the locality funds its own police department; still generally applicable elsewhere.
Q9 — safety_bail_pretrial
Category: safety
Question: How should the local criminal justice system handle pretrial release for people awaiting trial on non-violent charges?
Approach 1: Rely on cash bail and pretrial detention to help ensure court appearance and public safety.
Approach 2: Expand non-monetary release options, such as personal recognizance or supervised release, to reduce pretrial detention.
Offices involved: Local courts; prosecutor/district attorney; sheriff (jail administration); county commission (jail funding)
econ_weight: 0 · social_weight: 2
Why useful: A concrete, locally decided practice that strongly differentiates elected prosecutors and judges on the authority-versus-civil-liberties dimension.
Show-if: Show only where prosecutor, sheriff, or judicial positions are locally elected/accountable, or the county sets pretrial policy; hide if set entirely at the state level.
Q10 — education_funding_levy
Category: education
Question: Should local school funding be increased, even if it requires higher local property taxes or a school levy?
Approach 1: Increase school funding and programs, even if it requires higher local taxes or a levy.
Approach 2: Hold the line on local school taxes, even if it limits funding for new programs.
Offices involved: School board; city/county council where levy or shared tax authority applies
econ_weight: 2 · social_weight: 0
Why useful: A direct test of the taxation-and-spending tradeoff applied specifically to schools, which is often decided somewhat independently of general budgets.
Show-if: Applicable in nearly all jurisdictions with local school funding authority; hide where school funding is set entirely at the state level.
Q11 — education_choice_vs_traditional
Category: education
Question: Should local education policy prioritize expanding school-choice options, or prioritize investment in traditional neighborhood public schools?
Approach 1: Prioritize investment in traditional neighborhood public schools.
Approach 2: Prioritize expanding school-choice options, such as charter schools or open enrollment.
Offices involved: School board; city/county government where charter authorization applies
econ_weight: 1 · social_weight: 1
Why useful: Distinguishes candidates on a recurring, often contentious school-board issue that does not reduce simply to funding levels.
Show-if: Show only where charter schools, open enrollment, or vouchers are legally available; hide where no school-choice mechanism exists.
Q12 — education_youth_services
Category: education
Question: Should local government expand funding for youth services outside of school, such as after-school programs, libraries, or recreation centers?
Approach 1: Expand funding for after-school and youth recreation or library programs, even if it requires new spending.
Approach 2: Keep youth-services spending at current levels and rely on schools, nonprofits, or families to fill gaps.
Offices involved: City council; county commission; library board; parks & recreation department
econ_weight: 1 · social_weight: 0
Why useful: Captures a youth-focused public-investment question distinct from core school funding, relevant to councils and commissions rather than only school boards.
Show-if: Applicable broadly, though the specific funding structure varies by locality.
Q13 — transportation_mode_priority
Category: transportation
Question: When local government has limited transportation funding, which should it prioritize?
Approach 1: Expanding and maintaining road capacity for cars, including new lanes, parking, and road repair.
Approach 2: Expanding public transit, bike lanes, and pedestrian infrastructure.
Offices involved: City council; county commission; regional transportation authority; public works department
econ_weight: 0 · social_weight: 0
Why useful: A concrete, recurring capital-spending tradeoff that residents experience directly through traffic, transit access, and walkability.
Show-if: In areas with no transit system, narrow the framing to bike/pedestrian versus road investment only.
Q14 — transportation_funding_mechanism
Category: transportation
Question: How should local road and infrastructure improvements be funded?
Approach 1: Fund improvements through general local taxes shared across all residents.
Approach 2: Fund improvements through user fees, tolls, or charges tied to specific developments or users.
Offices involved: Public works department; city council; county commission; regional transportation authority
econ_weight: 1 · social_weight: 0
Why useful: Tests a common infrastructure-funding tradeoff, broad tax base versus user-pays, adding economic-axis signal from this category.
Show-if: Hide toll-specific wording where state law prohibits local tolling; framing can shift to fees/exactions only.
Q15 — environment_regulation_cost
Category: environment
Question: Should local government adopt stricter environmental rules for local development and business, even if it raises costs for developers or businesses?
Approach 1: Adopt stricter local environmental rules, even if it raises costs for development or business.
Approach 2: Limit local environmental rules to reduce costs and regulatory burden on development and business.
Offices involved: City council; county commission; environmental/planning board
econ_weight: 2 · social_weight: 0
Why useful: A direct test of the regulation-versus-market-cost tradeoff applied to environmental policy, a growing area of local authority.
Show-if: Applicable in all jurisdictions with local land-use or environmental regulatory authority.
Q16 — environment_parks_vs_development
Category: environment
Question: When land becomes available, should local government prioritize acquiring or preserving it as parks and open space, or prioritize allowing private development?
Approach 1: Prioritize acquiring or preserving land as parks and public open space.
Approach 2: Prioritize allowing private development of available land.
Offices involved: City council; county commission; parks department; planning/zoning board
econ_weight: 2 · social_weight: 0
Why useful: A concrete public-versus-private land-use tradeoff that recurs whenever vacant or public land is discussed, complementing the zoning questions.
Show-if: Most relevant in growing or land-constrained areas; importance weighting naturally reduces impact elsewhere.
Q17 — environment_climate_resilience
Category: environment
Question: Should local government invest in climate-resilience projects, such as flood control, stormwater upgrades, or extreme-heat preparedness, even if it requires new spending or fees?
Approach 1: Invest in climate-resilience projects now, even if it requires new local spending or fees.
Approach 2: Limit new spending on climate-resilience projects unless required, prioritizing other budget needs.
Offices involved: City council; county commission; public works/utilities department
econ_weight: 2 · social_weight: 0
Why useful: A forward-looking infrastructure question increasingly relevant across urban, suburban, and rural localities facing flooding, heat, or drought.
Show-if: Most relevant where the locality has documented flood, drought, wildfire, or heat risk; de-emphasize or hide in very low-risk areas.
Q18 — accountability_neighborhood_control
Category: accountability
Question: For decisions that affect specific neighborhoods, such as zoning changes or new development, how much power should neighborhoods or community boards have relative to citywide government?
Approach 1: Centralize authority with the city or county government to ensure consistent, citywide standards.
Approach 2: Give neighborhoods, community boards, or local advisory councils more direct authority over decisions that affect them.
Offices involved: City council; planning/zoning board; neighborhood or community advisory boards
econ_weight: 0 · social_weight: 2
Why useful: A core test of the centralized-versus-decentralized dimension of the social axis, independent of any specific policy area.
Show-if: Show only where neighborhood councils or similar bodies exist or are under active consideration; hide otherwise.
Q19 — accountability_public_input
Category: accountability
Question: Should local government be required to hold more extensive public-comment periods before major decisions, even if it slows down decision-making?
Approach 1: Streamline decision-making with fewer or shorter public-input requirements.
Approach 2: Require more extensive public comment and community input, even if it slows decisions.
Offices involved: City council; county commission; all boards/commissions with public-meeting requirements
econ_weight: 0 · social_weight: 2
Why useful: Distinguishes candidates on process and transparency preferences, not just policy outcomes, a recurring theme in local governance debates.
Show-if: Applicable in nearly all jurisdictions with public-meeting or comment requirements.
Q20 — accountability_elected_vs_appointed
Category: accountability
Question: Should more local oversight bodies, such as police oversight boards, planning commissions, or utility boards, be filled by direct election rather than appointment?
Approach 1: Keep these positions appointed by elected officials, to preserve accountability through the existing chain of command.
Approach 2: Make more of these positions directly elected, to increase independent accountability to voters.
Offices involved: City council/mayor (appointment authority); any board considering elected-versus-appointed structure
econ_weight: 0 · social_weight: 1
Why useful: Surfaces views on institutional design and accountability structure, a less obvious but consequential local governance question.
Show-if: Show only where such a change is within local/charter discretion; treat as informational where structure is fixed by charter or state law.

Scoring & Verification Methodology
1. Scoring the seven-axis radar chart
The radar chart shows local-policy priorities, so each axis should represent how much the voter cares about that category, not the direction of their views (a radar axis communicates magnitude far better than a signed lean).
For each of the 7 categories, take the voter's importance ratings (1–5) on every question in that category.
Average them, then rescale to 0–100: category_score = 100 * (avg_importance - 1) / 4.
Plot the 7 category scores as the radar chart axes.
Optionally pair the radar chart with a secondary indicator (color scale, icon, or small paired bar chart) per axis showing the voter's average directional lean in that category, since a single radar line cannot legibly encode both magnitude and sign.
2. Scoring the two-axis ideological compass
For each axis (economic; social/institutional), use only the questions with a non-zero weight on that axis:
Convert each answer (1–5) to a position value from −1 to +1: position = (answer - 3) / 2.
Multiply by that question's axis weight (0–2) to get its contribution: contribution = weight * position.
axis_score = sum(contributions) / sum(weights_used), producing a result on the same −2..+2 scale as the individual weights. Rescale to −100..+100 for display if desired.
Recommendation: compute compass placement from policy position only, not importance. Reserve importance weighting for the compatibility score below (Section 3) — this keeps the compass comparable across voters regardless of how engaged they are with any one topic, while still letting personal priorities drive the candidate match.
econ_score   = sum(w_i * ((answer_i - 3) / 2) for i in questions where econ_weight_i != 0)
             / sum(econ_weight_i for i in questions where econ_weight_i != 0)

social_score = sum(w_i * ((answer_i - 3) / 2) for i in questions where social_weight_i != 0)
             / sum(social_weight_i for i in questions where social_weight_i != 0)
3. Voter–candidate compatibility
Compatibility should be calculated per race, using only questions where a verified candidate position exists.
For each qualifying question, express both the voter's answer and the candidate's position on the same 1–5 scale (maximum possible distance = 4).
Per-question compatibility: compatibility_i = 1 - (abs(voter_i - candidate_i) / 4).
Weight each question by the voter's importance rating (map 1–5 directly).
overall_compatibility_pct = 100 * sum(weight_i * compatibility_i) / sum(weight_i).
Report the same weighted average broken out by radar category and by compass axis, so the site can explain why a match scored as it did, not just the final number.
Never substitute a neutral (3) or zero-weight value for a candidate position that is simply unknown — exclude that question from both the numerator and denominator for that candidate rather than silently penalizing or crediting them.
4. Warning: hide questions that do not apply to the voter's jurisdiction
Several questions above are only meaningful where the referenced office or policy lever exists locally — for example, elected-prosecutor or elected-sheriff questions in jurisdictions where those roles are appointed, pretrial/bail questions where the state controls the policy entirely, school-choice questions where no charter or open-enrollment law exists, or neighborhood-council questions where no such body exists or could exist. Showing and scoring an inapplicable question misleads the voter about what local officials actually control, and it injects noise into both the radar chart and the compass because the answer reflects an opinion about a lever nobody in that race can pull.
Maintain a jurisdiction-metadata table (form of government, which offices are elected versus appointed, which government level controls zoning/schools/bail/tolling, whether neighborhood or community boards exist, relevant charter and state-preemption rules) and use it to programmatically filter which questions are shown and scored for each voter. Do not default a hidden question to neutral in scoring — simply exclude it, the same as an unanswered question.
Per-question show-if conditions are listed in the Full question detail section above and should map directly to fields in that jurisdiction-metadata table.
5. Verifying candidate positions
This framework defines only the voter-facing questionnaire and scoring logic. No candidate positions should ever be invented, assumed, or inferred from party affiliation, endorsements, or general reputation. Populate candidate positions only from sourced, checkable material, and label each one with where it came from:
Official government records — actual votes cast, motions made, ordinances sponsored or opposed, and budget votes, drawn from meeting minutes and legislative records.
Direct candidate responses to this questionnaire — the most reliable and directly comparable source, since it maps one-to-one onto the same 20 questions and scale used for voters.
Established third-party candidate questionnaires with a comparable structure, such as League of Women Voters/Vote411 guides or Ballotpedia's Candidate Connection survey.
Campaign materials and public statements — platform pages, debate and forum transcripts, and social media statements, clearly attributed and dated.
Voting or decision histories for incumbents — roll-call votes and board minutes, which are especially valuable because they reflect actions rather than rhetoric.
Reputable local reporting — newspaper and public-radio coverage of candidate forums, records, and platforms, favoring outlets with a track record of nonpartisan local accuracy.
Attach a visible source citation and last-verified date to every candidate position shown to voters. If no credible source exists for a given question, display the position as "not available" and exclude that question from the compatibility calculation for that candidate rather than guessing — an incomplete but honest profile is more useful, and more defensible, than a complete but invented one. Re-verify positions close to each election, since candidates' stated views can change over the course of a campaign.

