# Static analysis findings and fixes

Line numbers below refer to the original `loan_calculator.py` at commit
`cdc0224`. Reports are preserved in `reports/before/` and `reports/after/`.
High and medium Bandit findings are listed first. Manual findings are labelled
because the tools do not verify the mathematics or the eligibility policy.

| Issue | Type | Line(s) | Description | Fix Approach |
|-------|------|---------|-------------|--------------|
| B402, B321 plain FTP | Security, high | 3, 68–71 | Credentials and applicant reports travel without encryption. | Replace FTP with certificate-verified HTTPS, explicit credentials, a timeout, checked response status and guaranteed connection closure. The real bureau must provide an HTTPS endpoint; the demo host is a placeholder. |
| B302 marshal deserialization | Security, medium | 61–65 | `marshal.loads` is unsuitable for untrusted application records. | Use UTF-8 JSON with context managers; reject non-object documents before replacing the in-memory book. |
| B107 hardcoded password | Security, low | 67 | The upload function embeds a shared default credential. | Require the caller to supply credentials; remove the default password. |
| B311 predictable identifiers | Security, low | 50–51 | Eight decimal digits from `random` are predictable and have a small identifier space. | Generate a 128-bit random token with `secrets.token_hex(16)`. |
| B404, B607, B603 process execution | Security, low | 6, 73–74 | A PATH-resolved mail command receives caller data and its failure is unchecked. | Send structured messages directly through authenticated SMTP over certificate-verified TLS. Credentials and sender come from environment variables; errors propagate. |
| W0102 mutable default | Correctness | 20–21 | The same default history list is reused across calls. | Use keyword-only `history=None`; append only to an explicitly supplied list. |
| R1732 unclosed resources | Reliability | 56–58, 63–65, 70 | Files can remain open when an exception occurs. | Use context managers for files and SMTP, and `finally` for the HTTPS connection. |
| W0603 global rebinding | Maintainability | 62, 64 | Loading replaces the shared dictionary, invalidating references. | Parse into a local value, then clear and update the existing dictionary. |
| W0622, W0612, W0613 | Correctness and maintainability | 33–38 | `sum` shadows a built-in; the loop index and annual rate are unused. The maximum loan ignores interest. | Replace the summation with the present value of affordable monthly payments; floor unavailable capacity at zero. |
| C0103, C0114, C0116 | Style and readability | 1–106 | Functions use inconsistent names and lack documentation. | Use snake_case names and module/function docstrings. |
| Flake8 E302, E305, E501, F541 | Formatting | 14–106 | Missing blank lines, long lines and a constant f-string. | Apply PEP 8 spacing, wrap long expressions and use a regular string. |
| Flake8 F401 / Pylint W0611 | Maintainability | 2 | `math` was unused. | Use `math` deliberately for finite-value checks and stable loan formulas. |
| Mixed rate units | Manual correctness | 14–18, 94 | The demo passes `9` while the other callers pass `0.09`; monthly EMI prints as 375000. | Consistently document decimal annual rates and pass `0.09` for 9%; EMI is about 10379.18. |
| Eligibility bypass | Manual correctness | 22–31 | A good credit score or high income bypasses debt and loan-type checks. | Require all documented eligibility conditions; validate the supported type and avoid dividing by zero. |
| Invalid score accepted | Manual correctness | 81–91 | Scores above 900 are classified LOW, including demo score 950. | Return INVALID outside the supported 300–900 interval, including non-finite values. |
| Principal counted as saved interest | Manual correctness | 76–79 | The payment difference includes the prepaid principal. | Subtract prepayment from that difference. Savings for the demo are about 12275.07 rather than 62275.07. |
| Zero rate and invalid terms | Manual correctness | 14–18 | Zero interest divides by zero; invalid durations and negative/non-finite values produce misleading results. | Handle zero interest explicitly and validate calculation inputs. |
| Import executes demo | Manual reliability | 106 | Importing the module prints output and writes application data. | Guard the demo with `if __name__ == "__main__"`. |

## Verification and remaining advisory

With Python 3.14.8, Pylint 4.1.3, Bandit 1.9.4 and Flake8 7.5.0:

- Pylint improved from **5.17/10 to 9.92/10**, above the required 9.5.
- Bandit improved from **8 findings (2 high, 1 medium, 5 low) to 0**.
- Flake8 improved from **22 findings to 0**.
- Twelve regression tests cover formulas, boundaries, persistence, import
  safety and mocked external integrations.

Pylint still reports R0913 for the six-argument eligibility function. Five
arguments describe the applicant and requested type; optional history remains
available to preserve the original capability. It is keyword-only. This advisory
is retained openly without disabling any checks. Pylint therefore exits with
status 8 even though its score exceeds the lab target. Bandit and Flake8 exit 0.
