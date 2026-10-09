# Provenance

This kit is called **Aurora Kit**, after the project whose engineering method it carries. The name is the kit's own. It does not mean the product is here.

The method in this kit was extracted on 2026-10-07 from the Aurora project, an
internal reference repo that Ramya Cheruvu chose as the model for how a team
designs, builds and gates software.

**Only the engineering method was taken.** That is the writing standard, the
design lifecycle, the ticket rules, the hook and CI gates, the skills layout,
and the generic decisions behind them. Aurora's product domain was left behind.
This kit holds none of its architecture, glossary, decision records, tickets or
customer names.

- Skills in `vendor/mattpocock-skills/` are third-party, MIT licensed, and
  copied pristine. Their license is `vendor/mattpocock-skills/LICENSE`. They are
  never edited here. The pinned upstream revision is recorded in `skills-lock.json`.
- Everything else was rewritten from Aurora's files and scrubbed of its names.
  `bin/check-no-leaks` fails if a domain word comes back.

## What was removed

The kit once held a verbatim copy of the reference project's method files
(`reference/`) and its 20 own skills (`aurora-*`). They named the reference
project's customer, its Jira project, its tooling server and its product code,
and none of that belongs in a kit other projects install. They were removed on
2026-10-09, along with `bin/verify-reference` and the `--with-aurora` installer
flag that served them. The generic `aes-*` skills, the rule pages and the gates
at the kit root are the working versions, and nothing in them depends on what
was removed. `bin/check-no-leaks` fails if the reference project's domain words
return.
