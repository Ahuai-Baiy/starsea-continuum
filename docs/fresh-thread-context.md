# What to carry into a fresh thread

When Continuum says `rebuild`, or tells you a thread has grown too old or too
heavy, your app starts a new thread. This guide is about the next five seconds:
**what you put into that new thread so the conversation does not feel cut.**

The goal is simple to state and easy to miss:

> The person on the other side should never feel the window change.

No "what were we talking about?". No sudden politeness, as if meeting for the
first time. No forgetting the correction they made ten minutes ago, or the
promise made yesterday. If the switch is done well, nobody notices it
happened.

Continuum decides *when* a fresh thread is needed and *why*. Building the
context for it is your app's job — and this page describes how to do it well.

## The five layers

Build the new thread from layers, ordered from the most stable to the most
recent. Each layer has its own job and its own budget.

| # | Layer | What it carries | Why it is needed |
|---|---|---|---|
| 1 | **Fresh instructions** | System / developer instructions, rebuilt from your current configuration | The old thread may have been built on instructions that changed. Never copy them from it. |
| 2 | **Current facts** | The current version of facts and preferences the assistant relies on | So a corrected fact wins over an old mention of it. |
| 3 | **Summary** | The main line of the conversation so far: topics, state, open loops, commitments | Keeps the thread of the story without paying for every word. |
| 4 | **Recent moments, verbatim** | A few short excerpts from earlier windows that a summary would flatten | Keeps *how* things were said, not just *that* they were said. |
| 5 | **Recent tail, verbatim** | The last turns exactly as they were exchanged | So the next reply picks up mid-sentence, not mid-topic. |

Then append the new message.

Ordering stable-to-recent also helps prompt caching: the layers that change
least sit at the front.

### 1. Fresh instructions

Assemble them from your current settings — mode, preset, persona, tools —
exactly as you would for a brand-new conversation, and compute the
`developer_digest` from what you actually send. If the rebuild happened
*because* instructions changed (`developer_instructions_changed`), this layer
is the whole point.

Keep anything that changes every turn — the current time, live status, tool
availability — **out** of the instructions and in the turn input instead.
Otherwise the digest changes every turn and every turn becomes a rebuild.

### 2. Current facts

Give the model the *current* version of what it needs to know about the
person and the situation. When something was corrected, say so plainly:

```text
Current: daily summary emails are OFF (changed by the user on T2).
Older messages may still mention them as ON — that is history, not the present.
```

This is the layer that keeps "remembering the past" from turning into
"believing the past". If your app tracks fact versions, pass them to
Continuum as `fact_versions` so a change triggers a rebuild in the
first place.

### 3. Summary

A rolling summary of everything older than the recent tail: what the
conversation is about, decisions made, open questions, things promised, and
the mood if it matters. Write it for the model, not for a human
reader — short, factual, in order.

A summary is context, not authority. If it disagrees with layer 2, layer 2
wins.

### 4. Recent moments, verbatim

A summary keeps what happened and loses how it was said. "Read it back to me
before you send anything, okay?" becomes "the user prefers to review drafts",
and the model no longer knows how firmly that was meant.

So keep a handful of short **original excerpts** from earlier windows — a
correction, a request that changed behavior, a moment that set the tone —
each with one or two sentences of context explaining why it matters. Rules
that keep this layer honest:

- **Quote, don't paraphrase.** Store message ids and offsets, and re-read the
  text from your message store when building the context.
- **Verify before injecting.** If the source message was edited or deleted,
  or its digest no longer matches, drop the excerpt.
- **Keep it small.** A dozen excerpts is plenty; this layer is seasoning.

### 5. Recent tail, verbatim

The last several turns, exactly as exchanged, from the **current branch**
only. This layer usually deserves the largest share of the budget: it is what
lets the next reply continue the sentence rather than restart the topic.

Always cut on a turn boundary. Never include a half-finished reply.

## Budgets

Give every layer a ceiling and stick to it. A reasonable starting split for
the carried context (tune it for your model and use case):

| Layer | Share |
|---|---|
| Fresh instructions | whatever they need — they are not optional |
| Current facts | ~10% |
| Summary | ~20% |
| Recent moments | ~15% |
| Recent tail | ~55% |

If a layer overflows, shrink *that* layer (shorter summary, fewer excerpts,
fewer tail turns). Do not let one layer silently eat another.

## Never carry

- **Turns from another branch.** If a message was edited, regenerated,
  deleted, or resent, the replaced version is gone. Build from the branch the
  person is on now.
- **Half-finished replies.** If the previous turn never completed
  (`previous_turn_incomplete`, `thread_resume_failed`), stop at the last
  completed turn.
- **Stale facts presented as current.** Old statements may appear in the
  summary or tail; label them as past when they conflict with layer 2.
- **Unverified quotes.** If an excerpt no longer matches its source, drop it.
- **Hidden reasoning.** Do not carry the model's private thinking from the old
  thread into the new one. Carry what was actually said.
- **Pretend continuity.** If some stretch could not be included, say so
  ("some earlier turns are summarized, not quoted") instead of implying the
  model saw everything.

## By reason code

What to emphasize depends on why the fresh thread is needed.

| Reason | What to do |
|---|---|
| `operation_edit`, `operation_regenerate`, `operation_delete`, `operation_resend`, `regenerated_user_turn` | Rebuild from the current branch only. The replaced turn and its reply are not carried. |
| `mode_changed`, `preset_changed`, `model_changed`, `channel_changed`, `call_changed` | Carry all five layers; rebuild instructions for the new mode, preset, model, or channel. |
| `developer_instructions_changed` | Carry all five layers with the new instructions. |
| `facts_changed`, `fact_baseline_missing`, `fact_metadata_missing` | Carry all five layers; make sure the changed fact is stated in layer 2 and flagged where it conflicts with history. |
| `context_window_changed`, `context_window_invalidated`, `context_window_baseline_missing` | Refresh layer 4 from the current window. |
| `continuity_epoch_changed` | Something your app considers invalidating happened. Regenerate the summary from the message store rather than reusing the old one. |
| `previous_turn_incomplete`, `thread_resume_failed` | Carry up to the last completed turn; never the partial reply. |
| `persistent_thread_idle` | Carry all five layers, and tell the model the current time — time has passed. |
| `turn_limit_reached`, `context_capacity_reached` | The classic window switch. Carry all five layers. This is where seamlessness matters most. |
| `branch_or_history_gap`, `stale_history_revision`, `head_message_mismatch`, `parent_metadata_missing` | Rebuild from the current branch; do not trust the old thread's view of history. |
| `stored_state_invalid`, `accepted_backend_missing`, `rollover_input_invalid` | Your own state or inputs are broken. Rebuild normally, and fix the inputs. |

`new` (`first_persistent_turn`, `conversation_mismatch`) is a first turn for this
binding: build the same five layers, which may simply be empty.

`catchup` is different: the thread is still good. Send only the turns it
missed, in order, then the new message. No summary, no excerpts.

## A sketch

```python
def build_fresh_context(plan, store, conversation):
    parts = [
        build_instructions(store.current_settings(conversation)),  # layer 1
        render_current_facts(store.current_facts(conversation)),   # layer 2
        store.rolling_summary(conversation, budget=SUMMARY_BUDGET),  # layer 3
    ]
    for excerpt in store.recent_moments(conversation, limit=12):  # layer 4
        if store.verify_excerpt(excerpt):        # source unchanged?
            parts.append(render_excerpt(excerpt))
    parts.extend(store.recent_turns(              # layer 5
        conversation,
        branch=store.current_branch(conversation),
        completed_only=True,
        budget=TAIL_BUDGET,
    ))
    if plan.reason_codes[0] == "persistent_thread_idle":
        parts.append(render_current_time())
    return parts
```

The storage calls are your own. Continuum never reads your messages; it only
tells you which situation you are in.

## Did it work?

After a fresh thread starts, the first reply should:

- continue the current topic without asking what it was;
- keep the tone and the way the two of you talk;
- respect corrections made recently;
- remember open loops and promises;
- know what time it is, if time matters.

If people can tell when the window changed, one of the layers is missing or
starved. `plan_event()` and `summarize()` show how often fresh threads happen
and why; pair them with your own review of the first reply after each one.

## Not covered yet

A stricter form of carrying context — validated recovery packages with
explicit provenance, gaps, and single-use consumption — is designed but not
shipped. See [D003 — Bounded Recovery](../decisions/D003-bounded-recovery.md)
and the [recovery package example](../examples/recovery-package.json).
