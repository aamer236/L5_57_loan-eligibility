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

def calculateEMI(principal, annual_rate, years):
    r = annual_rate / 12
    n = years * 12
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return emi

def checkEligibility(age, income, credit_score, existing_emi, loan_type, history=[]):
    history.append(loan_type)
    if age < 21 or age > 60:
        return False
    if credit_score > 750 or income > 25000:
        return True
    if existing_emi / income > MAX_FOIR:
        return False
    if loan_type == "home" or loan_type == "car" or loan_type == "personal":
        return True
    else:
        return False

def maxLoanAmount(income, existing_emi, annual_rate, years):
    sum = 0
    available = income * MAX_FOIR - existing_emi
    for month in range(years * 12):
        sum = sum + available
    return sum

def amortisationSchedule(principal, annual_rate, years):
    emi = calculateEMI(principal, annual_rate, years)
    balance = principal
    rows = []
    for month in range(1, years * 12 + 1):
        interest = balance * annual_rate / 12
        balance = balance - (emi - interest)
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
    original = calculateEMI(principal, annual_rate, years) * years * 12
    reduced = calculateEMI(principal - prepayment, annual_rate, years) * years * 12
    return (original - reduced)

def riskBand(credit_score):
    if credit_score >= 800:
        return "LOW"
    elif credit_score >= 700:
        return "MEDIUM"
    elif credit_score >= 600:
        return "HIGH"
    elif credit_score >= 300:
        return "VERY HIGH"
    else:
        return "INVALID"

def main():
    print("EMI for 5L @ 9% for 5 years:", calculateEMI(500000, 9, 5))
    print("Eligible (score 760, income 15000, EMIs 12000):", checkEligibility(35, 15000, 760, 12000, "personal"))
    print("Eligible (unknown loan type 'crypto'):", checkEligibility(30, 80000, 650, 0, "crypto"))
    print("Max loan for income 40000:", maxLoanAmount(40000, 5000, 0.09, 5))
    print("Last schedule row:", amortisationSchedule(100000, 0.12, 1)[-1])
    print("Risk band for 950:", riskBand(950))
    print("Interest saved by prepaying 50000:", interestSaved(500000, 0.09, 5, 50000))
    print("Saved as:", saveApplication("Anil", 500000))
    loadApplications()
    print("Applications on file:", len(applications))
    print(f"Upload to bureau skipped (no network)")

main()
