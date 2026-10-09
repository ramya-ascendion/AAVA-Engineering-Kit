# Before saying "the system cannot do that"

**Read this before writing down that something is absent, missing, impossible, or
not supported.**

A session that claims something is missing is usually wrong, and when it is
wrong the search is the reason: it looked in one place, under one name, with one
tool. A false "this does not exist" is expensive because it is believed. It ends
the investigation, and it gets copied into a document where it outlives the
session that made it. These rules exist to widen the search before the claim is
made.

- **Search every code base that could hold it.** A capability absent from one
  repository or service is often present in another. List the code bases in
  play and search each, or say which ones you did not search.
- **Search for the fact, not the tool name.** A property on a record can answer
  "is the thing up" with no tool, function or endpoint named "status" in sight.
  A capability unwrapped by any helper is not a capability the system lacks.
  Search for the data and the behavior, then for the name.
- **A thing absent from a deployment is not a thing that does not exist.** "Not
  in the test environment" can mean nobody has deployed it. Check the product's
  own documentation before concluding it has no such component.
- **Check the live status before claiming the API lacks something**, and do not
  trust a version read once at startup. A running system can change under you
  between your first call and your last.
- **The same trap catches documents.** A search for a document by its title can
  miss it because the file's actual heading is worded differently. Search the
  text of the thing, not only its label.
- **State the scope of a search.** "No database driver in the monitoring stack"
  says nothing about the application the stack monitors. A negative result is
  about where you looked.
- **A class definition is a floor, not the schema.** A constructor that takes
  arbitrary keyword arguments can carry far more properties than its signature
  lists. Query the live data for its real keys.
- **An endpoint that exists may not answer your question.** One that reports
  structure and field-level change can still carry no timestamp.
- **Check credentials before trusting an empty answer.** An authorization
  failure can come back as a silent `0 rows` rather than an obvious error.
- **Say whether a claim is read or seen; keep docs apart from code.** A vendor's
  documentation that lists three ways to manage a device says nothing about
  which of them you checked. Name the one you verified.
- **Reading, watching, and proving are different powers.** A system that can
  alert on a value is not the same as one that can prove the value stayed in
  range, or one that shows the event. "Cannot alert on it" does not mean "cannot
  verify with it".
- **A snapshot has no history.** A state sampled every few minutes can miss a
  brief flap entirely.
- **A log line proves an event happened; its absence proves nothing.** The
  source may simply not log it.
- **Write tools may register only in a read-write mode.** A write path can exist
  in code and still be unreachable in a read-only deployment.
