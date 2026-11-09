import os
import math
import base64
import json
import secrets
import smtplib
import ssl
from email.message import EmailMessage
from http.client import HTTPSConnection
from datetime import datetime

# Global loan book
applications = {}
MAX_FOIR = 0.5
BUREAU_HOST = "creditbureau.example"

def _nonnegative(**values):
    """Reject negative or non-finite monetary values and rates."""
    for name, value in values.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative")


def _loan_terms(principal, annual_rate, years):
    """Validate loan inputs and return the number of monthly payments."""
    _nonnegative(principal=principal, annual_rate=annual_rate)
    if isinstance(years, bool) or not isinstance(years, int) or years <= 0:
        raise ValueError("years must be a positive integer")
    return years * 12


def calculateEMI(principal, annual_rate, years):
    """Return monthly EMI, with annual_rate expressed as a decimal (0.09)."""
    months = _loan_terms(principal, annual_rate, years)
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return principal / months
    discount = -math.expm1(-months * math.log1p(monthly_rate))
    return principal * monthly_rate / discount


def checkEligibility(age, income, credit_score, existing_emi, loan_type,
                     *, history=None):
    """Require supported type, valid age, income, credit and existing FOIR."""
    if history is not None:
        history.append(loan_type)
    if not all(math.isfinite(value) for value in
               (age, income, credit_score, existing_emi)):
        return False
    return (21 <= age <= 60 and 750 <= credit_score <= 900
            and income >= 25000 and existing_emi >= 0
            and existing_emi / income <= MAX_FOIR
            and loan_type in ("home", "car", "personal"))


def maxLoanAmount(income, existing_emi, annual_rate, years):
    """Return present value of payments affordable under the FOIR limit."""
    _nonnegative(income=income, existing_emi=existing_emi)
    _loan_terms(0, annual_rate, years)
    available = max(0, income * MAX_FOIR - existing_emi)
    return available / calculateEMI(1, annual_rate, years)


def amortisationSchedule(principal, annual_rate, years):
    """Return monthly interest and balance, rounding only displayed rows."""
    emi = calculateEMI(principal, annual_rate, years)
    balance = principal
    rows = []
    for month in range(1, years * 12 + 1):
        interest = balance * annual_rate / 12
        balance = max(0, balance - (emi - interest))
        if month == years * 12:
            balance = 0
        rows.append((month, round(interest, 2), round(balance, 2)))
    return rows


def applicationId():
    return "LN-" + secrets.token_hex(16)


def saveApplication(name, amount, file="loans.json"):
    app_id = applicationId()
    record = {"name": name, "amount": amount, "date": str(datetime.now())}
    updated = {**applications, app_id: record}
    with open(file, "w", encoding="utf-8") as stream:
        json.dump(updated, stream, allow_nan=False)
    applications.update(updated)
    return app_id


def loadApplications(file="loans.json"):
    with open(file, encoding="utf-8") as stream:
        records = json.load(stream)
    if not isinstance(records, dict):
        raise ValueError("Loan records must be a JSON object")
    applications.clear()
    applications.update(records)


def uploadToBureau(report_path, user, password):
    credentials = base64.b64encode(
        f"{user}:{password}".encode("utf-8")
    ).decode("ascii")
    with open(report_path, "rb") as stream:
        report = stream.read()
    connection = HTTPSConnection(
        BUREAU_HOST, timeout=30, context=ssl.create_default_context()
    )
    try:
        connection.request("POST", "/reports", body=report, headers={
            "Authorization": "Basic " + credentials,
            "Content-Type": "application/octet-stream",
        })
        response = connection.getresponse()
        response.read()
        if not 200 <= response.status < 300:
            raise OSError(f"Bureau upload failed: HTTP {response.status}")
    finally:
        connection.close()


def notifyApplicant(email, status):
    message = EmailMessage()
    message["From"] = os.environ["LOAN_MAIL_FROM"]
    message["To"] = email
    message["Subject"] = "Loan " + status
    message.set_content("Your loan application status is: " + status)
    with smtplib.SMTP_SSL(
        os.environ["LOAN_SMTP_HOST"], timeout=30,
        context=ssl.create_default_context(),
    ) as client:
        client.login(os.environ["LOAN_SMTP_USER"],
                     os.environ["LOAN_SMTP_PASSWORD"])
        client.send_message(message)


def interestSaved(principal, annual_rate, years, prepayment):
    """Return interest saved by an immediate prepayment, keeping the term."""
    _loan_terms(principal, annual_rate, years)
    _nonnegative(prepayment=prepayment)
    if prepayment > principal:
        raise ValueError("prepayment cannot exceed principal")
    original = calculateEMI(principal, annual_rate, years) * years * 12
    reduced = calculateEMI(
        principal - prepayment, annual_rate, years
    ) * years * 12
    return max(0, original - reduced - prepayment)


def riskBand(credit_score):
    """Classify scores within the supported 300 to 900 range."""
    if not math.isfinite(credit_score) or not 300 <= credit_score <= 900:
        return "INVALID"
    if credit_score >= 800:
        return "LOW"
    if credit_score >= 700:
        return "MEDIUM"
    if credit_score >= 600:
        return "HIGH"
    return "VERY HIGH"


def main():
    """Run the local demo without uploading reports or sending email."""
    print("EMI for 5L @ 9% for 5 years:", calculateEMI(500000, 0.09, 5))
    print("Eligible (score 760, income 15000, EMIs 12000):",
          checkEligibility(35, 15000, 760, 12000, "personal"))
    print("Eligible (unknown loan type 'crypto'):",
          checkEligibility(30, 80000, 650, 0, "crypto"))
    print("Max loan for income 40000:",
          maxLoanAmount(40000, 5000, 0.09, 5))
    print("Last schedule row:", amortisationSchedule(100000, 0.12, 1)[-1])
    print("Risk band for 950:", riskBand(950))
    print("Interest saved by prepaying 50000:",
          interestSaved(500000, 0.09, 5, 50000))
    if os.path.exists("loans.json"):
        loadApplications()
    print("Saved as:", saveApplication("Anil", 500000))
    loadApplications()
    print("Applications on file:", len(applications))
    print("Upload to bureau skipped (no network)")


if __name__ == "__main__":
    main()
