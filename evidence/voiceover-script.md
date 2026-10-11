# Receipts demo: voiceover script (2:57)

Times are for `receipts-3min-silent.mp4` / `receipts-3min-voiceover.mp4`. Read each line when its time comes up. Each line fits its shot at a normal speaking pace.

**0:00.5 – 0:10.0** · _Landing stats, then 'Open a case'_

Debited but not credited. Receipts resolves that bank complaint end to end, and it can't tell a customer anything it can't prove from a trace.

**0:10.5 – 0:22.0** · _Case 28: v1 and v3 side by side_

Same complaint, two versions. Version one checked the sender bank, the switch and the beneficiary, called the reversal tool, got 'reversed' back, and told the customer the money was returned.

**0:22.5 – 0:31.0** · _neatlogs trace of v1_

The neatlogs trace shows the truth. The tool said reversed, nobody read the ledger after it, and the money never moved.

**0:31.5 – 0:47.0** · _v3 card: claims, receipts, trace id_

Version three can't do that. Every sentence cites a receipt, the neatlogs span ID of the tool call that proves it. A deterministic verifier checks the source, checks the proof isn't stale, and checks the sentence doesn't claim more than the receipt says.

**0:48.0 – 1:01.0** · _neatlogs trace of v3_

In the v3 trace, it re-reads the stale switch, reverses, reads the ledger again, sees the debit still open, and escalates. The verifier allowed it.

**1:02.0 – 1:18.0** · _Numbers table, then rule cards_

Thirty cases, three runs each, graded against hidden truth. v1 sent thirty-one false claims. v2 fixed the words but got bolder with money: eleven harmful reversals. v3 gates the action too. Ninety out of ninety.

**1:18.5 – 1:27.5** · _What broke, per version_

Reading the traces gave us this failure list for each version. By v3, it's empty.

**1:28.5 – 1:42.5** · _neatlogs prompts: versions and the production label_

All three prompts live in neatlogs as versions of one managed prompt. The production label moved from v1 to v2 to v3, and the agent runs whatever that label points at.

**1:43.0 – 1:48.0** · _Ask once: 59 to 39_

v3 was safe, but it sent two thirds of cases to a human.

**1:48.5 – 2:00.0** · _GitHub commit with Entire-Checkpoint_

So it asks once. I decided in plain words. Headless Claude Code turned that into a rule and a test and committed it, and Entire checkpointed the session on that commit.

**2:00.5 – 2:22.0** · _Case 22: v3 vs v3 with rules_

The next case like it resolves itself. Here the switch says failed, but the beneficiary bank says credited. v3 escalated it. With the rule, the agent proves the credit and cites the policy. Across ninety runs, escalations dropped from fifty-nine to thirty-nine, still with zero false claims.

**2:22.5 – 2:36.0** · _Bachs checkout, paid_

Banks pay only for replies we proved, two thousand naira each. Our first billing partner couldn't onboard a Nigerian business, so we collect through Bachs. Fifty-one resolutions, paid in the sandbox.

**2:36.5 – 2:48.0** · _cfo.ai: Ari's pricing analysis_

Ari, on cfo.ai, built the plan from our measured costs, and it was blunt: at two thousand naira and sixty-six percent escalation, margin is only about twenty-five percent.

**2:48.5 – 2:57.0** · _cfo.ai: runway and escalation slider_

So we price per proved resolution with a monthly minimum. Receipts. It doesn't say done until it can prove it.
