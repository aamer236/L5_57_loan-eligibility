# Reflection on static code analysis

The supplied handout asks for reflection but does not contain the four questions
mentioned by the README. The following four topics are a draft reflection on
this implementation, not a claim to reproduce those missing questions or the
student's personal experience. Review them before submission.

## 1. What did each tool contribute?

Bandit identified eight security findings, including unencrypted FTP and unsafe
marshal deserialization. Pylint highlighted the shared mutable default, resource
handling, unused variables, naming and missing documentation. Flake8 identified
spacing, line length, an unused import and a redundant f-string. Their overlap
was useful, but each tool emphasised a different aspect of the program.

## 2. How were findings prioritised and addressed?

The high-severity FTP findings and medium-severity deserialization finding were
addressed first. HTTPS with certificate verification replaced plain FTP, and
JSON replaced marshal. Credentials are supplied at runtime, identifiers use
`secrets`, and SMTP over TLS replaces process-based mail. Resource handling and
the shared mutable default were then corrected, followed by naming and formatting.

## 3. What did static analysis miss?

The original demo showed several logical defects that the tools did not flag:
inconsistent annual-rate units, eligibility checks that could be bypassed,
maximum loan calculations that ignored interest, an invalid score labelled LOW,
and prepaid principal included in reported interest savings. Independent
calculation checks and boundary tests were necessary. A clean security report
or a high lint score alone does not establish correct behaviour.

## 4. How were fixes verified and what remains uncertain?

The original reports and demo output were preserved, and the same tools were
rerun against the final file. Pylint reached 9.92/10, Bandit found no issues and
Flake8 produced no findings. Twelve automated tests check the calculations,
eligibility boundaries, JSON persistence and mocked integrations. One Pylint
design advisory remains for the eligibility argument count. Real bureau and
SMTP compatibility are unverified because the repository provides no live
service or credentials. Eligibility thresholds are documented assumptions and
would need confirmation before using the program as an actual lending system.
