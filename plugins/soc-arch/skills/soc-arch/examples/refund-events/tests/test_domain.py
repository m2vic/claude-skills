import unittest

from refunds.domain.refund import Refund, RefundStatus as S


class ApplyOutcome(unittest.TestCase):
    def apply(self, start, outcome):
        return Refund("r1", "a@b.c", start).apply_outcome(outcome)

    def test_pending_to_succeeded_emits_one_event(self):
        updated, events = self.apply(S.PENDING, S.SUCCEEDED)
        self.assertEqual((updated.status, len(events)), (S.SUCCEEDED, 1))

    def test_pending_to_failed_emits_nothing(self):
        updated, events = self.apply(S.PENDING, S.FAILED)
        self.assertEqual((updated.status, events), (S.FAILED, []))

    def test_failed_can_still_succeed(self):
        updated, events = self.apply(S.FAILED, S.SUCCEEDED)
        self.assertEqual((updated.status, len(events)), (S.SUCCEEDED, 1))

    def test_succeeded_ignores_late_failure_and_duplicates(self):
        for outcome in (S.FAILED, S.SUCCEEDED):
            updated, events = self.apply(S.SUCCEEDED, outcome)
            self.assertEqual((updated.status, events), (S.SUCCEEDED, []))
