# Lab 5: Static Code Analysis — Loan Eligibility and EMI Calculator

**Your file:** `loan_calculator.py`
**Python:** 3.10 or newer

Follow the lab handout for the full instructions.

## About the program

A bank loan tool. It calculates EMIs, checks loan eligibility, works out the maximum loan a customer can get, builds amortisation schedules, assigns risk bands from credit scores, estimates the interest saved by prepaying and stores application records in a file.

The code works, but only just. It has quality, style and security problems of the kind Pylint, Flake8 and Bandit are built to find.

## What to do

1. **Run it first** and read the output carefully:
   ```bash
   python loan_calculator.py
   ```
   It runs a short built-in demo and prints the results; it does not ask for input. Read every line and ask whether a sensible program would print that. Not every problem in this file is something a tool will flag, so pay attention to output that looks wrong.

2. **Install the tools:**
   ```bash
   python -m pip install pylint bandit flake8
   ```

3. **Run the analysis** and save the reports:
   ```bash
   python -m pylint loan_calculator.py > pylint_report.txt
   python -m bandit -r loan_calculator.py > bandit_report.txt
   python -m flake8 loan_calculator.py > flake8_report.txt
   ```
   Use the `python -m` form: it works everywhere, including Windows where a bare `pylint` is often "not recognized". The tools exit with a non-zero status whenever they find issues; that is expected, not an error. In Windows PowerShell 5.1, `>` saves files as UTF-16; if a report looks garbled, use `python -m pylint loan_calculator.py | Out-File -Encoding utf8 pylint_report.txt` instead.

4. **Document the issues** in `issues.md` using this table (at least 4 rows, high and medium severity first):

   | Issue | Type | Line(s) | Description | Fix Approach |
   |-------|------|---------|-------------|--------------|
   | ... | ... | ... | ... | ... |

5. **Fix the code.** Fix at least 4 of the issues you documented, then rerun all three tools to confirm they are gone. Repeat until you are satisfied. The program should still do its job when you are done.

6. **Reflect.** Answer the four reflection questions from the handout in `reflection.md`.

## Deliverables

1. `loan_calculator.py`: your cleaned version, with at least 4 issues fixed.
2. `issues.md`: the completed issue table.
3. `reflection.md`: your answers to the reflection questions.

**Target:** aim for a Pylint score above 9.5 on your final file. A perfect 10.00/10 is very good.

Be ready to explain the bugs you found and how you fixed them. You may be called on to present.

## Completed implementation

The lab changes, issue table, draft reflection, regression tests and before/after
reports are included. The original assignment above is retained for context.

### Run and verify

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python loan_calculator.py
python -m unittest discover -s tests -v
python -m pylint loan_calculator.py
python -m bandit -r loan_calculator.py
python -m flake8 loan_calculator.py
```

The program uses only Python's standard library. The pinned development tools
were verified on Python 3.14.8; the program retains Python 3.10-compatible syntax.
Older Python versions were not executed in this environment.

Reports in `reports/before/` describe the original commit `cdc0224`; reports in
`reports/after/` describe the cleaned file. They include the demo, tests, tool
versions and exit codes. Pylint scores 9.92/10 with one R0913 argument-count
advisory; Bandit and Flake8 report no findings. No checks are disabled.
The work is organised into three local commits for security, logic/quality,
and formatting/documentation/verification. Nothing has been pushed.

### Calculation and eligibility assumptions

- Annual rates are decimal fractions: `0.09` means 9%. The term is a positive
  whole number of years with monthly payments. Amounts and rates must be finite
  and nonnegative. Zero interest is supported.
- Eligibility requires age 21–60 inclusive, monthly income at least 25000,
  credit score 750–900 inclusive, nonnegative existing EMI no greater than 50%
  of income, and loan type `home`, `car` or `personal`. These thresholds combine
  the checks suggested by the original code; the lab does not define a complete
  business policy. The helper checks existing debt only because the proposed
  EMI is not an input. It does not approve a requested loan amount.
- Risk bands support scores 300–900. Scores outside that range are INVALID.
- Maximum loan is the present value of the monthly repayment capacity after
  existing EMIs. Capacity cannot be negative.
- Prepayment is immediate and reduces EMI while keeping the original term.
  Savings exclude prepaid principal; fees and a reduced-tenure option are not
  modelled. Schedule rows round for display, keeping internal balances unrounded.

### API and integration changes

Public functions now use snake_case (`calculate_emi`, `check_eligibility`,
`max_loan_amount`, `amortisation_schedule`, `application_id`, `save_application`,
`load_applications`, `upload_to_bureau`, `notify_applicant`, `interest_saved`,
`risk_band`). Pass optional eligibility history as `history=my_list`.

Application storage defaults to UTF-8 `loans.json`, replacing `loans.bin`.
Existing marshal files are not loaded or automatically converted. The demo
loads an existing JSON book before appending. Library callers should likewise
load the intended book before saving; saves write the current in-memory book.
Importing the module runs no demo. Local generated records are ignored by Git.

Bureau uploads now use certificate-verified HTTPS POST to `/reports`, with
HTTP Basic authentication over TLS, required `user` and `password` arguments,
a 30-second timeout and checked HTTP status. `BUREAU_HOST` remains an example
host; configure a real bureau supporting this contract before calling the
function. This is a protocol change from the insecure original FTP integration.

Notifications use authenticated SMTP over TLS on the standard implicit TLS
port (465). Set `LOAN_MAIL_FROM`, `LOAN_SMTP_HOST`, `LOAN_SMTP_USER` and
`LOAN_SMTP_PASSWORD` in the environment. Network/authentication failures
propagate to the caller. The demo sends no emails or uploads; integrations are
tested using mocks, not live services.

The supplied handout contains no reflection questions. `reflection.md` clearly
labels four substitute topics for review before submission.
