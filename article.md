# I Gave My Support Bot Hindsight Memory of the Fixes That Failed

The most expensive thing our support bot ever said was "try uninstalling and reinstalling the Print Agent." It wasn't wrong in general. It was wrong for Priya, who had already done exactly that six months earlier, lost two hours of dispatch in the middle of a holiday rush, and told us in writing: "please don't make me reinstall things again, it never fixes anything."

Our CRM had a record of that ticket. It was one line: `T-4471 'Labels printing blank / cut off' (resolved, high)`. It didn't record the fix that failed, the one that worked, or what she'd asked us never to do again. That gap is what this article is about.

## What Relay is

Relay is the support agent for ShipRelay, a shipping and fulfilment platform for online merchants. It handles label printing through our desktop Print Agent, carrier rate quotes, Shopify/WooCommerce/Etsy order sync, tracking webhooks and billing. It answers customers in chat, looks up shipments and invoices, opens tickets, issues credits (capped at $200 without a human), and escalates.

The architecture is deliberately boring:

```
Browser  ──►  FastAPI
                 │
                 ▼
           SupportAgent
   ┌─────────────┼─────────────────┐
   ▼             ▼                 ▼
Hindsight     LLM (OpenAI-       SQLite system of record
memory        compatible,        (customers, shipments, invoices,
              tool calling)       tickets, credits, service status)
```

The split that matters is between the two data stores. Structured facts such as plan, MRR, shipments and invoices live in the relational database, the system of record every support team already has. The narrative is what the CRM never captures: what the customer's setup looks like, what broke, what fixed it, what *didn't* fix it, what we promised, and how they like to be talked to. That goes into [Hindsight, an open-source agent memory system](https://github.com/vectorize-io/hindsight).

Each turn runs the same loop: recall from memory, build a system prompt from the CRM record plus the recalled memories, run a tool-calling loop (max five rounds), reply, then retain the updated transcript. There's also a memory-off mode that runs the same model with the same prompt and tools but skips recall and retain. We use it as an honest baseline: it's what most support bots are.

## The through-line: negative knowledge

When I started, I thought of memory as "remember the customer's setup so they don't have to repeat it." That's useful, but it isn't what changed outcomes. What changed outcomes was remembering **what failed**.

Look at how a human support rep gets good. It isn't only knowing the right fix. They know which of the obvious fixes will waste this particular customer's afternoon. A generic LLM agent has the opposite instinct: it reaches for the most statistically common troubleshooting step, which is exactly the step an experienced customer has already tried.

So I designed the whole memory layer around one question: *when this customer writes in again, what should the agent not say?*

That shows up in four places: what we tell Hindsight to extract, how banks are partitioned, how recall is queried, and what we write back when a case closes.

## Telling Hindsight what's worth remembering

Hindsight doesn't just store text and embed it. On retain, it runs an extraction pass that pulls facts, entities and timestamps out of the content. You can steer that pass with a `retain_mission` on the bank. This was the single highest-leverage piece of configuration in the project:

```python
CUSTOMER_RETAIN_MISSION = (
    "You are building the long-term memory of a customer support team for ShipRelay, a shipping and "
    "fulfilment platform. Extract facts a support agent would need the next time this customer writes in: "
    "their technical environment (store platform, printer model, plugin/firmware versions, OS, carriers), "
    "each problem they had with its root cause, the fix that worked and any suggestion that did NOT work, "
    "their frustration level and risk of churn, promises or commitments we made to them, credits issued, "
    "and how they prefer to be communicated with. Ignore pleasantries."
)
```

"Any suggestion that did NOT work" is doing the heavy lifting there. Without it, extraction tends to collapse a ticket into its resolution ("DPI set to 203, labels fixed"), because that's the salient outcome. The failed reinstall is exactly the detail a summariser drops, and it's the one we need.

The same idea applies to the shared playbook bank, with one extra constraint:

```python
PLAYBOOK_RETAIN_MISSION = (
    "You are building a troubleshooting playbook for ShipRelay support. Extract reusable, anonymised "
    "knowledge: the symptom as a merchant would describe it, the environment it happens in, the root cause, "
    "the exact fix that worked (menu paths, settings, versions) and fixes that did not work. Never store "
    "customer names, emails or company names."
)
```

The [Hindsight documentation on banks and missions](https://hindsight.vectorize.io/) covers the knobs. The lesson I'd pass on: write the mission as if you were briefing a new hire on what to write in their notebook, and name the things they'd be tempted to leave out.

## Two kinds of bank, on purpose

Every customer gets their own bank (`shiprelay-customer-c1001`). There's one shared bank, `shiprelay-playbook`, for anonymised resolutions.

I went back and forth on this. One big bank with tag filters would have been simpler to operate. But per-customer banks give me an isolation boundary that doesn't depend on a filter being correct at query time. One merchant's details can't be recalled into another merchant's answer, because they aren't in the bank being searched. Anything that should cross customers has to go through the playbook, and it only goes there after an explicit, anonymising distillation step.

Every turn recalls both banks in parallel, and a failure in either one degrades the turn instead of killing it:

```python
async def _recall(self, customer_id: str, query: str, result: TurnResult) -> None:
    cust, play = await asyncio.gather(
        self.memory.recall_customer(customer_id, query),
        self.memory.recall_playbook(query),
        return_exceptions=True,
    )
    if isinstance(cust, Exception):
        log.warning("customer recall failed: %s", cust)
        result.warnings.append(f"Customer memory unavailable: {cust}")
    else:
        result.customer_memories = [m.to_dict() for m in cust]
    # ...same for playbook
```

The customer bank gets a `mid` recall budget and up to 12 results. The playbook gets `low` and 6. Personal history is usually the higher-signal source, and I'd rather spend latency there.

## The recall query bug that took me too long to see

Early on, recall worked beautifully on the first message and fell apart on the second. A customer would write "labels are blank again," get a good answer, then reply "yes, same printer" or "still broken." Recall on "still broken" returns noise, because the query carries almost no meaning on its own.

The fix is small and I now put it in every agent I build:

```python
prev = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
query = f"{user_message}\n\n(Previous agent message: {prev[:300]})" if prev else user_message
await self._recall(customer["id"], query, result)
```

The previous agent turn anchors the follow-up in context. It's truncated to 300 characters so a long tool-heavy reply doesn't drown out what the customer actually said.

## Writing memory without making the customer wait

After every turn we retain the full transcript to the customer bank. Two details matter.

First, it uses `retain_async=True`. Extraction is an LLM pass on Hindsight's side and there is no reason for the customer to wait on it.

Second, every retain for a conversation uses the same `document_id` with `update_mode="replace"`. My first version appended each turn as a new document, and a ten-turn chat produced ten overlapping copies of the same facts. Recall then returned the same fact several times in slightly different words and crowded out everything else. Keying on the conversation ID means Hindsight replaces the previous version of the transcript, so a chat is one document that grows rather than ten documents that overlap.

Every memory is also retained with a real timestamp, and customer recall passes `query_timestamp`. That's what lets the agent say "this is the third FedEx timeout this quarter" and have it be true, instead of treating a two-year-old incident as if it happened yesterday.

## Closing the loop: resolve and learn

When an agent or customer resolves a conversation, one LLM call distils the transcript into a JSON object with a ticket subject, a `customer_summary` for that customer's bank, and a `playbook_note` for the shared bank. The prompt asks for the same negative knowledge again: "anything that did NOT work" in the summary, "what did not work" in the playbook note, and "No names or company names" for the latter. If nothing reusable was learned, the note is `null` and nothing goes to the playbook.

Both writes go to Hindsight with their own document IDs (`<conversation>-summary`, `<conversation>-playbook`), so a resolved chat becomes three documents: the raw transcript, a customer-specific summary, and an anonymised lesson. The raw transcript preserves detail, the summary preserves judgement, and the lesson is the only part allowed to travel.

Finally, reps get a **Brief me** button that calls Hindsight's `reflect` over the customer bank with a reflect mission that says, in part, "Lead with anything that changes how the agent should behave (recurring issue, at-risk account, promises made, things not to suggest again)." Reflect reasons over the whole bank rather than returning top-k snippets, which is what you want for a five-bullet pre-reply brief.

## What it looks like in practice

Same model, same prompt, same tools. The only difference is whether memory is on.

**Priya (bakery, Zebra ZD421):** *"Labels are printing blank again, it's Diwali week."*
Without memory, the agent suggests restarting the printer and reinstalling the Print Agent. With memory, it recalls T-4471: a Zebra firmware update had reset the printer to 203 dpi while her label template was set to 300. It gives her the fix (Print Agent › Settings › Printers › Zebra ZD421 › DPI 203, then a test label), tells her she won't need to reinstall anything, and acknowledges the rush before troubleshooting.

**Rahul (three weeks old, no history):** *"Labels blank since the printer updated overnight."*
His customer bank is empty. The playbook isn't. Priya's case, stripped of her name and company, surfaces as a playbook entry: Zebra firmware update, DPI reset to 203, set it back in the Print Agent, and "reinstalling the Print Agent does NOT fix it." He gets the right fix on the first reply, and the system prompt tells the model to use playbook fixes without ever mentioning other customers.

**Elena (Enterprise, Reno warehouse):** *"FedEx rates timing out AGAIN for Reno."*
Memory says this is the third time this quarter and that her account manager, Dana, promised an immediate human escalation with Elena copied. The agent calls `check_service_status`, sees the FedEx rates API is degraded upstream, escalates P1 and copies Dana. The baseline, with no history, opens with troubleshooting questions.

**Tom (non-technical, Etsy + CSV):** *"Import says invalid header again."*
The baseline explains CSV encodings. With memory, the agent knows it was Mac Excel saving UTF-16 last time and walks him through *File › Save As › CSV UTF-8* one step at a time, because that's how he asked to be helped.

A large part of what memory contributes is simply the removal of wrong suggestions.

## Lessons

**1. Store the failures, not just the fixes.** The resolution is the least interesting part of a ticket. The failed attempts are what stop an agent from repeating a mistake, and they're exactly what summarisation drops unless you ask for them explicitly, in the retain mission, the resolve prompt and the reflect mission.

**2. Make isolation structural.** Per-customer banks mean a cross-customer leak requires a bug in bank selection, not just a missing filter. Knowledge that should be shared goes through a separate, anonymised channel with its own extraction mission.

**3. Recall queries need conversational context.** Short follow-ups are the majority of real chat turns. Folding the previous agent message into the query is a two-line change that fixes most multi-turn recall failures.

**4. Upsert conversations; don't append them.** A stable `document_id` per conversation with replace semantics keeps the bank from filling with near-duplicates that crowd out real signal.

**5. Memory must never break the turn.** Recall failures become warnings, retain is async and wrapped, and the agent still answers from the CRM record if Hindsight is unreachable. A support agent that goes silent because its memory layer hiccupped is worse than one with no memory.

If you're weighing whether [persistent agent memory](https://vectorize.io/what-is-agent-memory) is worth the extra moving part, my answer after building Relay is yes, but only if you're deliberate about what you ask it to remember. "Everything" gets you a slower RAG pipeline. "What we got wrong last time" gets you an agent that stops making the same mistake twice.
