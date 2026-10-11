# Recording guide: click by click (about 3 minutes)

No voiceover here; that gets written from the finished video. This guide only covers **what to open, what to click, and how long to stay on each screen.**

Record your whole browser window. Scroll slowly. Whenever this guide says "hold", keep the mouse still for that many seconds so viewers can read.

---

## Scene 0: Set up before you press record (about 10 minutes, not recorded)

Open these **6 tabs, in this order**, in one browser window:

**Tab 1: the demo site**
- Go to https://receipts-tau-liard.vercel.app
- Wait until the four number boxes near the top show numbers, then scroll back to the very top.

**Tab 2: neatlogs, the trace where v1 lied**
1. Go to https://app.neatlogs.com, sign in, and open **Traces** (where your screenshot was).
2. Click the **×** in the search box to clear it. The search box does not search trace IDs.
3. Click the **Session ID** filter (first button in the row under the search box).
4. Paste `cb094350ed08c4d6b183f83622a8e617` and apply. One row appears, dated 11 Oct; it ingested at about 07:24 Lagos time.
   - If nothing appears, change **Last 14 days** to **Last 30 days**.
5. Click the row to open the trace. You should see a tree of steps, including `sender.reverse`, then `verifier.check` at the end.
6. Click the `sender.reverse` step, so its details (the "reversed" acknowledgement) are showing. Leave the tab there.

**Tab 3: neatlogs, the prompt versions**
1. Same site, left menu: open **Prompts**. It may be called **Prompt Management** or sit under **Experiments**.
2. Click **receipts-agent**.
3. Make sure you can see the versions list (1, 2, 3) with the **production** label on version 3. Leave the tab there.

**Tab 4: GitHub, the rule Claude Code wrote**
- Go to https://github.com/Demiladepy/receipts/commit/255f3df
- Scroll so the commit message is at the top of the screen. Its last line says `Entire-Checkpoint: 01M4NJFY1EXVGPZD7C0G08CQXG`.

**Tab 5: the Bachs checkout**
- Go to https://sandbox-checkout.bachs.io/c/IBYLF0bYOTZFbIo
- It shows NGN 102,000.00 for 51 "Receipts: proved resolution". Don't pay.

**Tab 6: cfo.ai, your plan**
- Sign in at cfo.ai and open your Receipts plan after Ari has built it from the message in `evidence/cfo-inputs.md`. Leave the charts on screen.

Finally, click back to **Tab 1** and start recording.

---

## Scene 1: What it is (0:00 to 0:15), Tab 1

1. Start at the top of the demo site: the title "It doesn't say done until it can prove it." **Hold 5 s.**
2. Move the mouse slowly across the four number boxes (Resolved correctly 58 → 90, False claims sent 31 → 0, Harmful reversals 11 → 0, Cost per case). **Hold 8 s.**

## Scene 2: v1 lies to a customer (0:15 to 0:45), Tab 1, then Tab 2

1. Click **Open a case** (purple button, top right). The page jumps to the case section.
2. Check the controls: case **28** is highlighted, **Run 3** is selected, **Compare: v1 vs v3** is selected. That's the default; if not, click them.
3. Scroll so the grey complaint box and the top of both cards are on screen. **Hold 4 s** on the complaint box: "I sent NGN 30,000.00 … not credited", with the red chips "first switch read is stale" and "reversal reports success and never posts".
4. Move to the **left card (v1 · no gate)**. Hover over "What the customer got", the sentence *"We have reversed the debit on your account…"*. **Hold 5 s.**
5. Scroll down a little to the **red boxes** under it ("Lying reversal: told the customer it was done…"). **Hold 4 s.**
6. Scroll to **Claims and their receipts** in the left card. Point at the two lines with **red dots**: the reversal claim says "sender.reverse is not authoritative…". **Hold 4 s.**
7. Switch to **Tab 2** (neatlogs trace). Show the step list, with `sender.reverse` selected and no ledger read after it. **Hold 6 s.**

## Scene 3: v3 tells the truth (0:45 to 1:15), Tab 1

1. Switch back to **Tab 1**, same case.
2. Move to the **right card (v3 · reply + action gate)**, green "correct" badge. Hover over its message: *"…the debit is still open … escalated…"*. **Hold 5 s.**
3. Scroll to its **Claims and their receipts**: every line has a **green dot** and a receipt id. Point at two receipt ids. **Hold 5 s.**
4. If it has a **"blocked attempt"** link, click it to open it and **hold 3 s**. These are replies the checker stopped before they were sent.
5. Scroll to its **Tool calls** list: get_debit, switch (pending, then failed), reverse, get_debit again (debit open), escalate. **Hold 5 s.**
6. At the bottom of the card, point at **neatlogs trace …**. **Hold 2 s.**

## Scene 4: The numbers (1:15 to 1:40), Tab 1, then Tab 3

1. Click **Numbers** in the top menu.
2. Scroll slowly down the table. Rest on these rows: **Resolved correctly** (58 / 79 / 90 / 88), **False claims sent** (31 / 0 / 0 / 0) and **Harmful reversals** (3 / 11 / 0 / 0). **Hold 8 s.**
3. Click **What broke** in the top menu. Show the four cards: v1 has many failure types, v3 shows "Nothing. 0 failures". **Hold 5 s.**
4. Switch to **Tab 3** (neatlogs prompts). Show versions 1–3 and the **production** label on 3. **Hold 5 s.**

## Scene 5: Ask once (1:40 to 2:20), Tab 1, then Tab 4, then Tab 1

1. Back on **Tab 1**, click **Ask once** in the top menu.
2. Show the four boxes: Sent to a human 59 → 39, Unnecessary escalations 14 → 2, Billed resolutions 31 → 51, False claims / harmful 0/0 → 0/0. **Hold 6 s.**
3. Scroll to the **two rule cards** (your decisions in quotes, "licensed", "decided by Demiladepy"). **Hold 6 s.**
4. Switch to **Tab 4** (GitHub commit). Show the commit message, your decision quoted, and the **Entire-Checkpoint** line. **Hold 5 s.** Then scroll down to the files changed (one rule file, plus tests). **Hold 3 s.**
5. Switch back to **Tab 1**, click **Open a case**, click case **22**, and click **Compare: v3 vs v3 + rules**.
6. Show the right card (v3 + 2 committed rules): its message says the money was credited and cites the policy. One claim line is the policy, with a green dot. **Hold 6 s.**

## Scene 6: The business (2:20 to 2:50), Tab 5, then Tab 6

1. Switch to **Tab 5** (Bachs checkout): NGN 102,000.00, 51 × "Receipts: proved resolution". **Hold 6 s.**
2. Switch to **Tab 6** (cfo.ai): the plan Ari built. Hover over the chart and the Base / Downside / Upside lines. **Hold 8 s.** If Ari answered the pricing questions, scroll to that answer and **hold 5 s.**

## Scene 7: Close (2:50 to 3:00), Tab 1

1. Switch to **Tab 1** and scroll back to the very top (the title). **Hold 5 s.** Stop recording.

---

**If a page misbehaves while recording:** keep going. You can cut that part out later.
- If the case cards don't load, refresh Tab 1 and click case 28 again.
- If the neatlogs trace won't open, show the trace id at the bottom of the v1 card on the demo site instead.
