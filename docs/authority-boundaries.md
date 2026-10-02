# Authority boundaries

Continuity systems compose safely only when temporal validity, durable
authority, retrieval relevance and scheduling remain separate responsibilities.

The names below describe generic roles; an integration may implement them with
different components.

| Role | Owns | Must not decide |
|---|---|---|
| Continuum | temporal/generation validity and recoverable-context identity | durable belief truth, general relevance, scheduling |
| Authority store | durable judgment admission, revision and currentness | temporal recovery ownership, generic retrieval ranking |
| Memory | relevant events and durable background retrieval | durable-authority admission, Continuum validity |
| Scheduler | timing, follow-up and initiative | authority admission, history rewriting |

## Rules

1. A checkpoint or summary is context material, not durable authority.
2. A relevant historical hit cannot make a superseded statement current.
3. Repetition does not promote generated output into authority.
4. Restoring an old scene must not restore an obsolete durable state.
5. A consumer receives another subsystem's accepted interface, not its write
   authority.

These boundaries permit fail-soft composition: an invalid optional
contribution can be removed without collapsing ordinary continuity.
