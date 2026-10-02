# What to carry into a fresh thread

When Continuum says `rebuild`, or tells you a thread has grown too old or too
heavy, your app starts a new thread. This guide is about what goes into that
new thread, so the conversation does not feel cut.

> The person on the other side should never feel the window change.

Continuum decides *when* a fresh thread is needed and *why*. Building its
context is your app's job. This page describes one way to do it that keeps
every piece you carry **valid**: bound to the current branch, the current
epoch, and a known source.

## What goes in

Assemble the new thread in this order — the most stable parts first, the most
recent last:

| # | Part | What it carries |
|---|---|---|
| 1 | **Fresh instructions** | System / developer instructions rebuilt from your current settings |
| 2 | **Current facts** | The current version of facts the assistant relies on |
| 3 | **Dated timeline** | Short summaries of recent stretches of conversation, each with absolute dates |
| 4 | **Checkpoint and gap** | The latest valid checkpoint of older history, then the exact messages between that checkpoint and the recent tail |
| 5 | **Recent tail** | The last turns, exactly as exchanged |

Then append the new message.

### 1. Fresh instructions

Assemble them from your current configuration, exactly as for a brand-new
conversation, and compute `developer_digest` from what you actually send.

Keep anything that changes every turn — the current time, live status, the
tool list for this turn — **out** of the instructions and in the turn input.
Otherwise the digest changes every turn and every turn becomes a rebuild.

### 2. Current facts

Give the model the *current* version of what it relies on. When something was
corrected, say so plainly and mark the old version as past:

```text
Current: daily summary emails are OFF (changed by the user on T2).
Older messages may still mention them as ON — that is history, not the present.
```

If your app versions its facts, pass the versions to Continuum as
`fact_versions` so that a change triggers a rebuild in the first place.

### 3. Dated timeline

Summarize finished stretches of conversation as they close — one short entry
per stretch, written for the model. Two rules make these entries survive
being read weeks later:

- **Absolute dates only.** "On March 3rd in the evening", never "yesterday" or
  "recently".
- **In order.** One stretch after another; do not blend different days into
  one sentence.

Each entry records which messages it covers and the continuity epoch it was
written under. When your app bumps the epoch — because history was edited in a
way that invalidates old summaries — entries from the old epoch are not used
again until they are regenerated.

### 4. Checkpoint and gap

For longer conversations, older history is condensed into a **checkpoint**: a
summary that names exactly which range of messages it covers.

When rebuilding, take the latest checkpoint that is still valid for the
current epoch and branch, then add the **gap** — the messages after the
checkpoint that no summary covers yet — verbatim. Checkpoint, gap, and tail
together must cover the conversation with no hole and no overlap.

- **Bounded.** Checkpoints and gaps have declared size limits. If the gap is
  too large to include exactly, fall back to a fuller rebuild rather than
  trimming it silently.
- **Traceable.** A checkpoint records its source range and a digest of what it
  summarized. If those no longer match, do not use it.
- **Consumed once.** A checkpoint prepared for one rebuild is claimed by that
  rebuild. A second rebuild re-validates instead of reusing it blindly.

See [D003 — Bounded Recovery](../decisions/D003-bounded-recovery.md) and the
[recovery package example](../examples/recovery-package.json) for the shape
of this data.

### 5. Recent tail

The last several turns, exactly as exchanged, from the **current branch**
only. This part usually deserves the largest share of the budget: it is what
lets the next reply continue the sentence instead of restarting the topic.

Always cut on a turn boundary. Never include a half-finished reply.

## Budgets

Give every part a ceiling. A reasonable starting split for the carried
context (tune it for your model):

| Part | Share |
|---|---|
| Fresh instructions | whatever they need — they are not optional |
| Current facts | ~10% |
| Dated timeline | ~15% |
| Checkpoint and gap | ~25% |
| Recent tail | ~50% |

If a part overflows, shrink that part. Do not let one part silently eat
another, and never let the budget create a hole between checkpoint, gap, and
tail.

## Never carry

- **Turns from another branch.** If a message was edited, regenerated,
  deleted, or resent, the replaced version is gone. Build from the branch the
  person is on now.
- **Half-finished replies.** If the previous turn never completed, stop at the
  last completed turn.
- **Summaries from an older epoch.** Regenerate them first.
- **Stale facts presented as current.** Label old statements as past when they
  conflict with part 2.
- **Hidden reasoning.** Carry what was said, not the model's private thinking.
- **Pretend continuity.** If some stretch could not be included, say so
  instead of implying the model saw everything.

## By reason code

| Reason | What to do |
|---|---|
| `operation_edit`, `operation_regenerate`, `operation_delete`, `operation_resend`, `regenerated_user_turn` | Rebuild from the current branch. The replaced turn and its reply are not carried; summaries covering it are not reused. |
| `mode_changed`, `preset_changed`, `model_changed`, `channel_changed`, `call_changed` | Carry all five parts; rebuild instructions for the new mode, preset, model, or channel. |
| `developer_instructions_changed` | Carry all five parts with the new instructions. |
| `facts_changed`, `fact_baseline_missing`, `fact_metadata_missing` | Carry all five parts; state the changed fact in part 2 and flag it where it conflicts with history. |
| `context_window_changed`, `context_window_invalidated`, `context_window_baseline_missing` | Rebuild with the context selection your app considers current. |
| `continuity_epoch_changed` | Do not reuse timeline entries or checkpoints from the old epoch; regenerate or fall back to a fuller rebuild. |
| `previous_turn_incomplete`, `thread_resume_failed` | Carry up to the last completed turn; never the partial reply. |
| `persistent_thread_idle` | Carry all five parts, and tell the model the current time — time has passed. |
| `turn_limit_reached`, `context_capacity_reached` | The classic window switch. Carry all five parts. This is where seamlessness matters most. |
| `branch_or_history_gap`, `stale_history_revision`, `head_message_mismatch`, `parent_metadata_missing` | Rebuild from the current branch; do not trust the old thread's view of history. |
| `stored_state_invalid`, `accepted_backend_missing`, `rollover_input_invalid` | Your own state or inputs are broken. Rebuild normally, and fix the inputs. |

`new` (`first_persistent_turn`, `conversation_mismatch`) builds the same
parts, which may simply be empty. `catchup` is different: the thread is still
good, so send only the turns it missed, in order, then the new message.

## A sketch

```python
def build_fresh_context(plan, store, conversation):
    epoch = store.continuity_epoch(conversation)
    branch = store.current_branch(conversation)

    parts = [
        build_instructions(store.current_settings(conversation)),     # 1
        render_current_facts(store.current_facts(conversation)),      # 2
        render_timeline(store.timeline(conversation, epoch=epoch)),   # 3
    ]

    tail = store.recent_turns(conversation, branch=branch,
                              completed_only=True, budget=TAIL_BUDGET)
    checkpoint = store.latest_valid_checkpoint(conversation, epoch=epoch,
                                               branch=branch)
    if checkpoint and store.claim(checkpoint):                        # 4
        gap = store.messages_between(checkpoint.end, tail.start, branch=branch)
        if len(gap) <= GAP_LIMIT:
            parts += [render_checkpoint(checkpoint), *gap]
        else:
            parts += store.fuller_history(conversation, branch=branch)
    parts += tail                                                     # 5

    if plan.reason_codes[0] == "persistent_thread_idle":
        parts.append(render_current_time())
    return parts
```

The storage calls are your own. Continuum never reads your messages; it only
tells you which situation you are in.

## Did it work?

After a fresh thread starts, the first reply should continue the current topic
without asking what it was, keep the tone, respect recent corrections,
remember what is still open, and know what time it is if time matters. If
people can tell when the window changed, a part is missing, starved, or
invalid. `plan_event()` and `summarize()` show how often fresh threads happen
and why.
