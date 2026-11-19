# Review lenses

A **lens** is one area a review covers. Each lens has a finder role, the diff signals that make it worth running, and the checks its finder applies. A **verified** lens returns issues that need the [finding schema](finding-schema.md)'s violated basis, concrete scenario, and source quote. The **advisory** `design` lens returns design notes: opinions checked for agreement by a second model, never presented as defects.

## Suggest lenses

Read `changed_files` in `context.json` and skim the diff. Suggest each lens whose signals appear, and give the matching signal as the reason.

| Lens | Finder | Suggest when the diff |
| --- | --- | --- |
| `correctness` | `turtle-bug-hunter` | Always. Turn it off only when the user explicitly asks. |
| `security` | `turtle-security` | Touches anything beyond docs, comments, or tests. Name the strongest signal: external input, auth or sessions, secrets, shell, SQL or template construction, file paths, deserialization, or shared state across threads or requests. |
| `data` | `turtle-data` | Touches migrations, schema or ORM model files, SQL or query-builder calls, transactions, caches, or a persisted or wire format. |
| `performance` | `turtle-performance` | Adds loops over collections or fetched rows, queries or network calls, work on a request, render, or other hot path, large allocations, or reads without a bound. |
| `design` (advisory) | `turtle-design` | Adds modules or files, changes a public API or exported interface, adds imports across module boundaries, or adds long or deeply nested functions or near-duplicate blocks. |

The finder launch count is the selected lenses × `review` entries. In small mode, one combined finder per `review` entry covers every selected verified lens, and `design` keeps its own finder because it returns notes.

## `correctness` and `security`

Their checks live in the [bug hunter](../../../agents/turtle-bug-hunter.md) and [security](../../../agents/turtle-security.md) role definitions.

## `data`

Apply every check against the actual schema, migration, and query sources:

- **Migrations.** A destructive step (dropped column or table, narrowed type) loses existing data without a backfill or copy. A `NOT NULL` column lacks a default or backfill for existing rows. A rename or removal breaks code that still reads the old name. A down migration is missing where the repository's other migrations have one.
- **Constraints.** Code assumes uniqueness, non-null, or a foreign key the schema does not enforce, or writes a value the schema rejects.
- **Queries.** A join or filter returns the wrong rows, drops a tenant or owner scope, paginates with an off-by-one, or relies on row order without `ORDER BY`.
- **Transactions.** Several writes that must succeed together run outside one transaction, so a mid-way failure leaves partial state. A read-modify-write lacks the lock or isolation level that prevents a lost update. An external side effect inside a transaction fires even when the transaction rolls back.
- **Formats.** A change to a persisted or wire format breaks reading existing rows, files, cache entries, or messages.

A missing-index claim needs the schema source showing the index is absent and a query in the diff that filters or joins on that column.

## `performance`

Apply every check to code the diff adds or changes:

- **Complexity.** A nested loop over input-sized collections replaces a linear pass, or repeated work (a query, regex compile, file read, or deep copy) moves inside a loop.
- **N+1.** A query or network call runs once per item where one batched call served before, or where the codebase's convention batches it.
- **Unbounded work.** A fetch, read, queue, retry, or cache grows with input the caller controls, without the limit, pagination, or eviction the surrounding code uses.
- **Hot paths.** Blocking I/O runs on an event loop or request thread, or new per-call work lands on a path the source documents or measures as hot.
- **Leaks.** A connection, file handle, subscription, or timer stays open on some path.

The basis is a documented latency, memory, or call budget; an existing limit or batching convention; or a bound the code kept before the change. The scenario names a concrete input size or state and the observable cost: call count, complexity, memory growth, or a blocked thread.

## `design` (advisory)

Compare the change with the structure the repository already has, and apply every check:

- **Boundaries.** A module reaches into another's internals, a lower layer imports a higher one, or logic lands in a module whose siblings hold a different concern.
- **Interfaces.** A public function, endpoint, or type exposes an implementation detail, takes a flag that switches between unrelated behaviors, or breaks the naming and shape of its neighbors.
- **Duplication.** The change copies logic that already exists in a helper or another module.
- **Complexity.** A function the change adds or grows is long, deeply nested, or mixes several concerns where a split would make each part easier to read or test.
- **Dead code and naming.** Code the change leaves unreachable, or a name that misleads about what the code does.

Ground each note in the repository: name the neighbor, helper, or convention the change departs from. A note without a concrete suggested change is left out.

A `data` or `performance` candidate whose verifier finds the code behaves as claimed but no violated basis can become a design note with that lens, through the same second-opinion check.
