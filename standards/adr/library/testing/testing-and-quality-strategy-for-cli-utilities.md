# ADR Library: Testing and Quality Strategy for CLI Utilities

## Description

This reusable draft defines a layered testing and quality strategy for command-line utilities. It makes the externally observable CLI contract the defining test boundary, supplements it with lower-cost unit and integration tests, and adds specialized assurance practices only when their risk triggers apply.

Before adoption, identify the utility's supported command-line surface, distinguish production commands from internal scripts, select the applicable risk-driven additions, adapt the verification and tooling details to the repository, add its required ADR metadata, and obtain explicit acceptance.

```markdown
# Test CLI utilities through observable contracts and risk-driven quality practices

## Context and Problem Statement

This repository contains command-line utilities intended for use by humans, automation, scripts, continuous integration systems, and other software.

CLI software has a particularly important public boundary: the command-line interface itself. Consumers can depend on command names, arguments, options, exit codes, standard output, standard error, filesystem effects, configuration precedence, environment handling, and machine-readable output.

Testing only internal functions is therefore insufficient. A CLI can have comprehensive unit coverage while still being broken from the perspective of its users. Failures can include:

- incorrect argument parsing;
- wrong exit codes;
- diagnostics written to `stdout` instead of `stderr`;
- behavior differences between the internal API and installed executable;
- broken packaging or entry points;
- unexpected configuration precedence;
- failure to propagate subprocess errors;
- incorrect handling of paths, symbolic links, Unicode, or unusual filesystem states;
- partial filesystem mutation after a failed operation;
- unstable machine-readable output; and
- regressions in commands relied upon by scripts.

This decision governs the testing and quality strategy for all CLI utilities developed in this repository, whether invoked by a person or by automation.

It does not govern library-only modules, the selection of a particular testing framework, or fixed numeric ratios among test levels. Security, privacy, model-behavior, formal-assurance, and functional-safety practices apply only when a utility has the corresponding risk or capability. The complete required baseline applies to production utilities; non-production utilities apply the strategy in proportion to their supported behavior and consequences.

How should production CLI utilities establish confidence in the behavior their consumers depend upon without imposing every available testing methodology on every utility?

## Decision Drivers

- Treat the actual command-line interface as a first-class public contract.
- Detect defects that internal-function tests and coverage percentages cannot establish.
- Keep most feedback fast and diagnostically precise.
- Make external and nondeterministic dependencies testable without distorting stable pure logic.
- Exercise success, failure, cleanup, compatibility, and automation-facing behavior.
- Add specialized security, privacy, AI, assurance, or safety practices in proportion to actual risk.
- Preserve flexibility in implementation language and test framework.

## Considered Options

- Use a layered strategy centered on CLI integration and contract testing, with risk-driven additions.
- Rely on unit tests of internal functions.
- Rely primarily on end-to-end executable tests.
- Use mock-heavy testing as the default.
- Require every listed testing and assurance methodology for every utility.

## Decision Outcome

Chosen option: **use a layered strategy centered on CLI integration and contract testing, with risk-driven additions**. The behavior consumers observe at the production invocation boundary defines CLI correctness; lower-cost test levels establish that behavior where they can do so with sufficient confidence.

This decision governs all CLI utilities developed in this repository. It does not govern library-only modules, exact test-framework choices, or fixed proportions among test levels. The complete required baseline applies to production utilities, and specialized practices remain conditional on the triggers defined below.

### CLI integration and contract testing

CLI integration and contract testing is a core testing practice.

Tests SHALL exercise the actual CLI entry point, installed command, packaged executable, or equivalent production invocation path where practical. These tests verify the public contract rather than internal implementation details.

Depending on the utility, the CLI contract includes:

- command and subcommand names;
- positional arguments;
- flags and options;
- required options;
- optional values and defaults;
- mutually exclusive arguments;
- argument ordering where significant;
- short and long option forms;
- command discovery;
- help behavior;
- version behavior;
- exit status;
- `stdout`;
- `stderr`;
- error messages;
- machine-readable output formats;
- filesystem effects;
- files and directories created, modified, or removed;
- configuration discovery;
- configuration precedence;
- environment-variable handling;
- current-working-directory behavior;
- standard input;
- pipes and redirection;
- TTY versus non-TTY behavior where significant;
- subprocess invocation;
- subprocess error propagation;
- network dependency behavior where applicable;
- permission failures;
- filesystem failures;
- symbolic-link behavior;
- path normalization;
- Unicode and unusual filenames;
- temporary-file behavior;
- cleanup after failures;
- signal and interruption handling;
- idempotency where promised;
- deprecated commands or arguments;
- backward compatibility of stable CLI interfaces; and
- shell completion where provided.

Not every utility requires tests for every item above. The applicable contract surface SHALL be identified from the utility's actual behavior.

Tests of internal command-handler functions SHALL NOT be treated as substitutes for tests of the actual CLI boundary.

### Testing pyramid

The test suite SHALL generally follow a testing pyramid:

1. Many fast unit and component tests cover:

   - domain logic;
   - parsing;
   - validation;
   - transformations;
   - state transitions; and
   - isolated failure behavior.

2. A smaller set of integration tests covers:

   - filesystem interactions;
   - subprocesses;
   - configuration;
   - persistence;
   - network clients;
   - operating-system facilities; and
   - interactions among major components.

3. A focused set of CLI contract and end-to-end tests covers:

   - actual CLI invocation;
   - packaging and entry-point behavior;
   - representative workflows; and
   - critical failure paths.

The exact proportions are not prescribed. Test value and execution cost take precedence over arbitrary numeric ratios.

### Property-based testing

Property-based testing SHOULD be used where behavior is better described by invariants than by a small number of hand-selected examples.

It is especially appropriate for:

- command-line parsing;
- configuration parsing;
- path manipulation;
- serialization and deserialization;
- parsers;
- encoders and decoders;
- data transformations;
- normalization;
- state machines;
- bounded numeric input;
- malformed input;
- Unicode;
- unusual filenames; and
- combinations of independently valid options.

Properties SHALL represent meaningful invariants rather than merely duplicating example-based tests with generated values.

### Mutation testing

Mutation testing SHOULD be used for important deterministic logic where conventional coverage metrics cannot establish whether tests meaningfully detect defects.

It is particularly valuable for:

- validation logic;
- branching decisions;
- comparison operators;
- authorization or permission decisions;
- state transitions;
- error handling;
- destructive operations;
- safety checks; and
- parsing and normalization rules.

Mutation score SHALL be treated as evidence about test-suite effectiveness, not as an optimization target in isolation.

Projects MAY limit mutation testing to high-value modules when full-suite mutation testing would impose disproportionate execution cost.

### Test seams

Code SHOULD provide explicit seams around external or nondeterministic dependencies.

Common CLI seams include:

- filesystem access;
- process execution;
- environment variables;
- clocks;
- randomness;
- user input;
- terminal capabilities;
- operating-system information;
- networking;
- remote APIs;
- persistence; and
- credential providers.

Seams SHOULD permit deterministic testing without unnecessarily abstracting stable pure logic.

A seam SHALL NOT be introduced solely to satisfy a particular mocking framework if doing so degrades the design.

### Test doubles

Test doubles MAY be used where replacing a dependency materially improves test determinism, speed, fault injection, or isolation.

The following test-double classifications apply.

#### Fake

Fakes are generally preferred where a lightweight working implementation can reproduce important dependency semantics.

Typical examples include:

- in-memory repositories;
- temporary filesystem implementations;
- fake clocks;
- fake command runners; and
- local API substitutes.

A fake SHALL accurately reproduce the semantics upon which the code under test relies.

#### Stub

Stubs SHOULD be used to provide deterministic responses or failures from dependencies.

They are especially useful for:

- error paths;
- unavailable services;
- unusual return values;
- rate limits;
- timeouts; and
- malformed external responses.

#### Spy

Spies MAY be used where a test needs to observe interactions while allowing real or realistic collaborator behavior.

#### Mock

Mocks MAY be used where interaction itself is part of the contract.

Mocks SHOULD NOT be the default testing mechanism for ordinary domain logic.

Tests that assert large numbers of implementation-specific calls SHOULD be avoided because they create unnecessary coupling between the test suite and internal structure.

#### Dummy

Dummy values MAY be used to satisfy interfaces when a dependency is irrelevant to the behavior under test.

### Test-driven development

Test-driven development is supported but is not mandated as the exclusive development workflow.

Developers MAY use the conventional red/green/refactor cycle:

1. Write a failing test.
2. Implement the minimum behavior required for the test to pass.
3. Refactor while preserving behavior.

Chicago-school TDD is the preferred TDD orientation for most domain and CLI logic. Tests SHOULD favor observable state and behavior and use real collaborators where they are fast and deterministic.

London-school TDD MAY be used where interaction-heavy components benefit from collaborator-first design and explicit mocks. It SHOULD be applied selectively because extensive interaction mocking can make tests brittle and tightly coupled to implementation structure.

### Behavior-driven development and Gherkin

Behavior-driven development (BDD) MAY be used for high-level user-visible behavior. It is particularly useful when documenting stable command behavior such as:

> Given a repository with invalid configuration, when the user invokes `tool sync`, then the command exits unsuccessfully, reports the configuration error on `stderr`, and leaves the repository unchanged.

BDD scenarios SHOULD focus on observable behavior rather than internal implementation steps. BDD is not required for every feature or test.

Gherkin MAY be used as the representation for executable or human-readable BDD scenarios. It SHALL NOT be introduced merely to restate ordinary unit tests in Given/When/Then syntax.

Its use should provide at least one of the following:

- clearer acceptance criteria;
- executable acceptance specifications;
- communication across implementation and non-implementation roles; or
- durable documentation of externally visible behavior.

### Security testing and threat modeling

Security practices are risk-dependent rather than universally required.

#### STRIDE

STRIDE SHOULD be used when a CLI crosses meaningful trust boundaries or performs security-sensitive operations.

Examples include utilities that:

- execute subprocesses;
- accept untrusted files or input;
- operate with elevated privilege;
- manage credentials;
- modify security-sensitive configuration;
- communicate over a network;
- expose interprocess communication mechanisms;
- alter permissions or ownership;
- perform remote execution;
- install software; or
- mutate repositories or deployment state.

The threat model SHOULD explicitly consider CLI-specific attack surfaces such as:

- command injection;
- argument injection;
- unsafe shell invocation;
- path traversal;
- symbolic-link attacks;
- time-of-check to time-of-use races;
- unsafe temporary files;
- permission errors;
- credential exposure;
- environment-variable manipulation;
- untrusted configuration; and
- dependency and artifact integrity.

#### OWASP Top 10

The OWASP Top 10 MAY be used when the utility exposes or interacts with relevant web-application or HTTP service surfaces.

It SHALL NOT serve as the sole or primary security taxonomy for a standalone CLI.

#### LINDDUN

LINDDUN SHOULD be considered when a utility handles:

- personally identifiable information;
- user identities;
- telemetry tied to individuals;
- private usage history;
- location data; or
- sensitive personal data.

It is not required for utilities without a meaningful privacy threat surface.

### LLM evaluations

Large language model (LLM) evaluations SHALL be added when a CLI's correctness or usefulness materially depends on nondeterministic model behavior.

Examples include:

- AI-generated classifications;
- summarization;
- natural-language transformation;
- agentic planning;
- semantic extraction;
- model-selected actions; and
- generated code or configuration.

Traditional deterministic tests SHOULD continue to cover all deterministic portions of such utilities.

LLM evaluations SHOULD measure model-dependent qualities that cannot be represented adequately through exact expected-value assertions.

### Formal inspection

Fagan inspection MAY be used for high-assurance components, specifications, designs, or changes.

It is not part of the default development workflow because the ceremony and cost are disproportionate for ordinary CLI utilities. Projects requiring greater assurance MAY adopt formal inspection based on risk.

### Functional safety

IEC 61508 Safety Integrity Level practices are outside the normal scope of this decision.

They become applicable only if a utility is incorporated into a safety-related system governed by IEC 61508 or another applicable functional-safety regime.

No project SHALL claim IEC 61508 or Safety Integrity Level compliance merely because conventional software tests are comprehensive. Such compliance requires the broader lifecycle, assurance, verification, independence, documentation, and process requirements imposed by the applicable standard.

### Required baseline

Unless a utility's scope makes an item genuinely inapplicable, each production CLI utility SHALL have:

1. Unit or component tests for deterministic business logic.
2. CLI integration or contract tests exercising the production invocation boundary.
3. Tests of successful and unsuccessful exit behavior.
4. Assertions covering `stdout` and `stderr` where those streams form part of the interface.
5. Tests of externally visible filesystem changes where the utility mutates the filesystem.
6. Tests of configuration and environment behavior where supported.
7. Representative malformed-input and boundary-condition tests.
8. Test seams around important nondeterministic or external dependencies.
9. Integration tests for important external system boundaries.
10. Regression tests for defects whose recurrence would be material.

Property-based and mutation testing SHOULD supplement this baseline where their use materially improves confidence.

### Risk-driven additions

The following practices SHALL be added when their trigger condition exists:

| Condition | Additional practice |
| --- | --- |
| Complex input spaces or important invariants | Property-based testing |
| Critical deterministic logic | Mutation testing |
| Significant trust boundaries | STRIDE |
| Web or API attack surface | Relevant OWASP guidance |
| Personal or sensitive data | LINDDUN |
| Nondeterministic LLM behavior | LLM evaluations |
| High-assurance development requirement | Formal inspection |
| Functional-safety system | Applicable IEC 61508 or Safety Integrity Level lifecycle requirements |

### Test design principles

Across all test levels, tests SHOULD:

- verify externally meaningful behavior;
- be deterministic unless nondeterminism is the explicit subject of the test;
- make failure causes clear;
- avoid unnecessary dependence on implementation details;
- exercise negative and failure paths, not only success paths;
- verify atomicity or cleanup where partial failure could leave harmful state;
- use realistic boundary conditions;
- reproduce fixed defects with regression tests;
- remain independently executable where practical;
- avoid reliance on ordering between unrelated tests;
- avoid using production credentials or mutable production services;
- minimize timing-dependent assertions; and
- test guarantees made to automation as strictly as guarantees made to human users.

Coverage percentages MAY be collected as diagnostic information, but coverage percentage SHALL NOT be treated as proof of test adequacy.

A smaller suite that meaningfully detects defects is preferable to a larger suite optimized primarily for coverage statistics.

### Consequences

- Good, because the actual command-line interface becomes a first-class test boundary.
- Good, because the strategy reduces the risk of internal tests passing while the packaged CLI is broken.
- Good, because it creates a common quality vocabulary across utilities.
- Good, because explicit test seams encourage deterministic architecture.
- Good, because example-based, property-based, integration, and mutation testing are used where each is most effective.
- Good, because heavy methodologies are not mandatory when their associated risks do not exist.
- Good, because security, privacy, AI, assurance, and functional safety are explicit risk-driven concerns.
- Good, because the strategy reduces overreliance on mocks and implementation-coupled tests.
- Good, because implementation language and test-framework choices remain flexible.
- Bad, because this strategy requires more test infrastructure than unit testing alone.
- Bad, because some tests are slower when they invoke actual executables or external boundaries.
- Bad, because projects may need temporary filesystems, subprocess harnesses, fake services, or controlled test environments.
- Bad, because stable CLI contract tests create an ongoing maintenance responsibility.
- Bad, because commands relied upon by automation can create backward-compatibility obligations.
- Bad, because property-based or mutation testing may increase CI runtime when applied extensively.

These costs are accepted because CLI correctness is defined by observable command behavior, not solely by correctness of internal functions.

### Confirmation

Determine applicability by inventorying the repository's CLI utilities and documenting each utility's actual command-line contract and risk triggers.

For each production utility, conformance is confirmed when the required baseline covers every applicable contract surface; production invocation tests exercise representative success and critical failure paths; triggered risk-driven practices are present; and the repository's documented test gate passes against the packaged or otherwise production-equivalent command boundary. For each non-production utility, conformance is confirmed when the layered strategy covers its supported behavior and proportionate failure consequences.

Out-of-scope library-only modules receive no finding under this decision.

## Pros and Cons of the Options

### Layered, contract-centered testing with risk-driven additions

- Good, because it tests the boundary consumers actually use while retaining fast, precise lower-level feedback.
- Good, because specialized assurance work follows concrete risk triggers.
- Bad, because it requires deliberate classification of contract surfaces and risk conditions.

### Unit tests of internal functions

- Good, because unit tests are fast and diagnostically precise.
- Bad, because internal correctness does not prove that argument parsing, packaging, executable entry points, output streams, exit codes, or filesystem effects work correctly.

### Primarily end-to-end executable tests

- Good, because these tests exercise realistic workflows through the public boundary.
- Bad, because a suite dominated by full executable tests is slower, less diagnostically precise, and more difficult to exercise comprehensively.

### Mock-heavy testing by default

- Good, because mocks can isolate interaction-heavy components and force specific failures.
- Bad, because extensive interaction mocking couples tests to internal implementation and can permit the tested model of a dependency to diverge from its real behavior.

### Every methodology for every utility

- Good, because it creates a superficially uniform checklist.
- Bad, because privacy modeling, LLM evaluations, formal safety processes, formal inspection, mandatory BDD or Gherkin, and repository-wide mutation testing create disproportionate process where no corresponding risk exists.
- Bad, because the OWASP Top 10 is oriented toward web applications and does not adequately represent many standalone CLI risks as a primary taxonomy.

## More Information

At adoption, record the production commands governed by this decision, the owner of the canonical test gate, the supported platforms, the stable machine-readable interfaces, and the selected risk-driven practices. Link to any threat model, privacy analysis, evaluation suite, packaging qualification, or functional-safety authority that applies.

Revisit this decision when a utility adds a materially different invocation path, trust boundary, data sensitivity, nondeterministic model dependency, high-assurance obligation, or safety-related role.

The governing principle is: **test the behavior consumers depend upon, then use the lowest-cost test level capable of establishing that behavior with sufficient confidence.**
```
