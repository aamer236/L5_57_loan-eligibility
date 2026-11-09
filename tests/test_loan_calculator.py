"""Regression coverage for the lab's calculations and security fixes."""

import contextlib
import importlib
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import loan_calculator as loan


class CalculationTests(unittest.TestCase):
    """Check formulas against independent values and boundary cases."""

    def test_emi_and_maximum_amount(self):
        self.assertAlmostEqual(loan.calculate_emi(500000, .09, 5),
                               10379.177613, places=5)
        expected = 15000 * (1 - (1 + .09 / 12) ** -60) / (.09 / 12)
        self.assertAlmostEqual(loan.max_loan_amount(40000, 5000, .09, 5),
                               expected)
        self.assertAlmostEqual(loan.calculate_emi(expected, .09, 5), 15000)
        self.assertEqual(loan.max_loan_amount(10000, 6000, .09, 5), 0)

    def test_zero_interest_and_zero_principal(self):
        self.assertEqual(loan.calculate_emi(1200, 0, 1), 100)
        self.assertEqual(loan.max_loan_amount(40000, 5000, 0, 5), 900000)
        self.assertEqual(loan.calculate_emi(0, .09, 5), 0)
        self.assertEqual(loan.interest_saved(1200, 0, 1, 100), 0)

    def test_invalid_terms(self):
        for principal, rate, years in [(-1, .09, 5), (1, -.09, 5),
                                       (1, .09, 0), (1, .09, 1.5),
                                       (1, .09, True), (math.inf, .09, 5),
                                       (1, math.nan, 5)]:
            with self.subTest(terms=(principal, rate, years)):
                with self.assertRaises(ValueError):
                    loan.calculate_emi(principal, rate, years)
        for prepayment in (-1, 1001, math.nan):
            with self.assertRaises(ValueError):
                loan.interest_saved(1000, .09, 5, prepayment)

    def test_amortisation_reconciles_interest(self):
        rows = loan.amortisation_schedule(100000, .12, 1)
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0][1], 1000)
        self.assertEqual(rows[-1][2], 0)
        self.assertTrue(all(a[2] >= b[2] for a, b in zip(rows, rows[1:])))
        interest = loan.calculate_emi(100000, .12, 1) * 12 - 100000
        self.assertAlmostEqual(sum(row[1] for row in rows), interest, delta=.06)

    def test_prepayment_counts_only_interest(self):
        self.assertAlmostEqual(loan.interest_saved(500000, .09, 5, 50000),
                               12275.065679, places=5)
        self.assertEqual(loan.interest_saved(500000, .09, 5, 0), 0)
        total_interest = loan.calculate_emi(500000, .09, 5) * 60 - 500000
        self.assertAlmostEqual(loan.interest_saved(500000, .09, 5, 500000),
                               total_interest)

    def test_eligibility_requires_every_condition(self):
        self.assertFalse(loan.check_eligibility(35, 15000, 760, 12000,
                                                'personal'))
        self.assertFalse(loan.check_eligibility(30, 80000, 800, 0, 'crypto'))
        for age, income, score, emi in [(20, 25000, 750, 0),
                                        (61, 25000, 750, 0),
                                        (35, 0, 750, 0),
                                        (35, 25000, 749, 0),
                                        (35, 25000, 901, 0),
                                        (35, 25000, 750, 12501),
                                        (35, 25000, 750, -1),
                                        (35, math.nan, 750, 0)]:
            with self.subTest(values=(age, income, score, emi)):
                self.assertFalse(loan.check_eligibility(age, income, score,
                                                        emi, 'home'))
        history = []
        for age in (21, 60):
            self.assertTrue(loan.check_eligibility(age, 25000, 750, 12500,
                                                   'home', history=history))
        self.assertEqual(history, ['home', 'home'])
        loan.check_eligibility(35, 25000, 750, 0, 'car')
        self.assertEqual(history, ['home', 'home'])

    def test_risk_boundaries(self):
        cases = {299: 'INVALID', 300: 'VERY HIGH', 599: 'VERY HIGH',
                 600: 'HIGH', 699: 'HIGH', 700: 'MEDIUM', 799: 'MEDIUM',
                 800: 'LOW', 900: 'LOW', 950: 'INVALID', math.nan: 'INVALID'}
        for score, band in cases.items():
            self.assertEqual(loan.risk_band(score), band)


class StorageAndIntegrationTests(unittest.TestCase):
    """Exercise file lifecycle and mock external integrations."""

    def setUp(self):
        self.previous = dict(loan.applications)
        loan.applications.clear()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'loans.json'

    def tearDown(self):
        loan.applications.clear()
        loan.applications.update(self.previous)

    def test_json_round_trip_and_unique_ids(self):
        first = loan.save_application('Anil', 500000, self.path)
        second = loan.save_application('Mira', 100000, self.path)
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith('LN-'))
        loan.applications.clear()
        loan.load_applications(self.path)
        self.assertEqual(loan.applications[first]['name'], 'Anil')
        self.assertEqual(len(loan.applications), 2)
        self.assertEqual(json.loads(self.path.read_text()), loan.applications)

    def test_failed_load_preserves_memory(self):
        loan.applications['existing'] = {}
        for contents, error in [('broken', json.JSONDecodeError),
                                 ('[]', ValueError)]:
            self.path.write_text(contents)
            with self.assertRaises(error):
                loan.load_applications(self.path)
            self.assertEqual(loan.applications, {'existing': {}})
        with self.assertRaises(FileNotFoundError):
            loan.load_applications(self.path.parent / 'missing.json')

    @patch('loan_calculator.HTTPSConnection')
    def test_upload_checks_status_and_closes(self, connection_factory):
        self.path.write_bytes(b'report')
        connection = connection_factory.return_value
        response = connection.getresponse.return_value
        response.status = 201
        loan.upload_to_bureau(self.path, 'user', 'test-credential')
        args, kwargs = connection.request.call_args
        self.assertEqual(args, ('POST', '/reports'))
        self.assertEqual(kwargs['body'], b'report')
        self.assertTrue(kwargs['headers']['Authorization'].startswith('Basic '))
        self.assertTrue(connection_factory.call_args.kwargs['context']
                        .check_hostname)
        connection.close.assert_called_once()
        connection.close.reset_mock()
        response.status = 500
        with self.assertRaises(OSError):
            loan.upload_to_bureau(self.path, 'user', 'test-credential')
        connection.close.assert_called_once()

    @patch.dict('os.environ', {'LOAN_MAIL_FROM': 'bank@example.com',
                              'LOAN_SMTP_HOST': 'smtp.example.com',
                              'LOAN_SMTP_USER': 'loanops',
                              'LOAN_SMTP_PASSWORD': 'test-credential'})
    @patch('loan_calculator.smtplib.SMTP_SSL')
    def test_notification_uses_tls_and_structured_message(self, smtp):
        loan.notify_applicant('anil@example.com', 'approved')
        client = smtp.return_value.__enter__.return_value
        message = client.send_message.call_args.args[0]
        self.assertEqual(message['To'], 'anil@example.com')
        self.assertEqual(message['Subject'], 'Loan approved')
        self.assertTrue(smtp.call_args.kwargs['context'].check_hostname)
        with self.assertRaises(ValueError):
            loan.notify_applicant('anil@example.com\nBcc: other@example.com',
                                  'approved')

    def test_import_has_no_demo_side_effects(self):
        output = io.StringIO()
        with patch('builtins.open', MagicMock()) as opening:
            with contextlib.redirect_stdout(output):
                importlib.reload(loan)
            opening.assert_not_called()
        self.assertEqual(output.getvalue(), '')


if __name__ == '__main__':
    unittest.main()
