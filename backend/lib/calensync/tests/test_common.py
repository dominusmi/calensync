from calensync.database.model import SyncRule
from calensync.queries.common import get_sync_rules_from_source
from calensync.tests.fixtures import *
from calensync.utils import utcnow


class TestGetSyncRulesFromSource:
    def test_normal(self, calendar1_1, calendar1_2, calendar1_2_2, calendar1_1_2):
        sr1 = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        sr2 = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2_2.id).save_new()
        sr3 = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_1_2.id).save_new()
        sr4 = SyncRule(source_id=calendar1_2.id, destination_id=calendar1_2_2.id).save_new()

        rules = get_sync_rules_from_source(calendar1_1)
        assert len(rules) == 3
        assert {r.id for r in rules} == {sr1.id, sr2.id, sr3.id}

    def test_deleted_paused(self, calendar1_1, calendar1_2, calendar1_2_2, calendar1_1_2):
        calendar1_1_2.paused = utcnow()
        calendar1_1_2.save()

        sr1 = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2.id).save_new()
        sr2 = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_2_2.id, deleted=True).save_new()
        sr3 = SyncRule(source_id=calendar1_1.id, destination_id=calendar1_1_2.id).save_new()
        sr4 = SyncRule(source_id=calendar1_2.id, destination_id=calendar1_2_2.id).save_new()

        rules = get_sync_rules_from_source(calendar1_1)
        assert len(rules) == 1
        assert {r.id for r in rules} == {sr1.id}
