# NEKOVA Licensing — Plain English FAQ

NEKOVA is licensed under the [Business Source License 1.1](LICENSE) (BUSL),
the same license used by MariaDB, HashiCorp (Terraform, Vault), Sentry, and
CockroachDB. This document explains what that actually means in plain
language. The [LICENSE](LICENSE) file is the legally binding document — this
FAQ is just here to help you understand it quickly.

---

### Can I use NEKOVA for free?

**Yes**, in almost every case:

- Personal projects — yes
- Learning, school, university courses — yes
- Open source projects — yes
- Internal company tools — yes
- Startups and businesses building products **written in NEKOVA** — yes,
  with no revenue limit at all
- Companies with under $1,000,000/year in revenue, for any use including
  competing services — yes

### What can I NOT do for free?

The license has exactly one restriction. You cannot **sell NEKOVA code
execution as a hosted service to third parties** — for example, building
your own "NEKOVA Cloud Sandbox" or "Run NEKOVA Online" product and charging
other people to use it — **if your organization makes over $1,000,000/year
in revenue.**

This restriction does not apply to you if:
- You're under the $1M/year revenue threshold (most individuals, students,
  startups, and small companies), **or**
- You're building a product *written in* NEKOVA rather than a product that
  *sells access to running* NEKOVA itself

### Wait, so can I build a SaaS app in NEKOVA and charge for it?

**Yes, absolutely, with no restriction and no revenue cap.** If you write
your billing platform, your app backend, your internal tools, or your AI
agent product in NEKOVA, that's exactly what the language is for. Build it,
sell it, scale it to any revenue. The license only restricts reselling
*NEKOVA's own execution engine* as a competing hosted service.

### Why does this restriction exist?

NEKOVA includes a built-in Sandbox — an isolated execution environment for
running untrusted NEKOVA code safely, with resource limits and violation
tracking. This is a real commercial product: companies can pay to run
user-submitted NEKOVA code safely via an API.

Without this license, anyone could take NEKOVA's Sandbox, host it
themselves, and sell the exact same service — undercutting the project that
built it, with none of the revenue going back into NEKOVA's development.
The BUSL protects that one specific thing while keeping everything else
completely open.

### Does this make NEKOVA "not open source"?

Technically, BUSL is not an OSI-approved open source license — it's
sometimes called "source available." The source code is fully public,
readable, modifiable, and forkable on GitHub right now. The only thing
restricted is commercial resale of NEKOVA-as-a-service above the revenue
threshold.

### Does this ever go away?

**Yes — automatically.** Four years after each version of NEKOVA is
released, that version's license converts to Apache License 2.0 — a fully
permissive, OSI-approved open source license with no restrictions at all.
This conversion is written directly into the license text and does not
require any action from anyone. Older versions of NEKOVA become fully open
source over time, even if you never update.

### I run a company over $1M/year and want to offer NEKOVA hosting. What do I do?

Reach out: **emmanuelkingchristopher@gmail.com**. Commercial licenses for
operating a competing hosted NEKOVA service are available — this is a
conversation, not a wall.

### Can I fork NEKOVA and modify it?

Yes. You can copy, modify, and redistribute the Licensed Work freely, as
long as the BUSL license terms travel with it. You just can't strip the
license out and relicense it as something else, and the same hosting
restriction applies to your fork as it does to the original.

### What about the VS Code extension and other tools?

The VS Code extension, CLI, formatter, debugger, notebook, and web IDE are
all part of the Licensed Work and covered by the same terms above. Use them
freely for any of the permitted cases.

---

*This FAQ is provided for clarity and convenience and is not a substitute
for the [LICENSE](LICENSE) file, which is the actual legal agreement.
If anything here conflicts with the LICENSE file, the LICENSE file governs.*