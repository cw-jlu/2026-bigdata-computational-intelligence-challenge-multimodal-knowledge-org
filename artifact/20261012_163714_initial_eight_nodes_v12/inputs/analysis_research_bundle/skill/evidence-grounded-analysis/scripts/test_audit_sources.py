import copy
import unittest
from audit_sources import audit

BASE = {'schema_version': 1, 'sources': [{
    'id': 'A', 'title': 'Example historical report', 'publisher': 'Example',
    'url': 'https://example.org/report', 'published_by': '2025-04-01',
    'role': 'published_statistics', 'independence_group': 'one',
    'locator': 'p.1', 'content_verified': True, 'version_status': 'fixed_edition'}]}

class AuditTests(unittest.TestCase):
    def test_past(self):
        self.assertEqual(audit(BASE, '2025-05-10', ['A'], ['A'])['status'], 'PASS')
    def test_future(self):
        self.assertEqual(audit(BASE, '2025-03-01', ['A'])['status'], 'FAIL')
    def test_same_day(self):
        self.assertEqual(audit(BASE, '2025-04-01', ['A'])['status'], 'PASS')
    def test_unknown_id(self):
        self.assertEqual(audit(BASE, '2025-05-10', ['X'])['status'], 'FAIL')
    def test_later_retrieval_allowed(self):
        x=copy.deepcopy(BASE); x['sources'][0]['retrieved_at']='2026-10-10'
        self.assertEqual(audit(x, '2025-05-10', ['A'])['status'], 'PASS')
    def test_later_version_blocked(self):
        x=copy.deepcopy(BASE); x['sources'][0]['version_date']='2025-06-01'
        self.assertEqual(audit(x, '2025-05-10', ['A'])['status'], 'FAIL')
    def test_dynamic_version_blocked(self):
        x=copy.deepcopy(BASE); x['sources'][0]['version_status']='live_revised'
        self.assertEqual(audit(x, '2025-05-10', ['A'])['status'], 'FAIL')
    def test_unknown_publication_blocked(self):
        x=copy.deepcopy(BASE); x['sources'][0]['published_by']=None
        self.assertEqual(audit(x, '2025-05-10', ['A'])['status'], 'FAIL')
    def test_duplicate_id(self):
        x=copy.deepcopy(BASE); x['sources'].append(x['sources'][0].copy())
        with self.assertRaises(ValueError): audit(x, '2025-05-10', [])
    def test_unread(self):
        x=copy.deepcopy(BASE); x['sources'][0]['content_verified']=False
        self.assertEqual(audit(x, '2025-05-10', ['A'])['status'], 'FAIL')
    def test_method_not_data(self):
        x=copy.deepcopy(BASE); x['sources'][0]['role']='method'
        self.assertEqual(audit(x, '2025-05-10', ['A'], ['A'])['status'], 'FAIL')
    def test_invalid_url(self):
        x=copy.deepcopy(BASE); x['sources'][0]['url']='file:///etc/passwd'
        self.assertEqual(audit(x, '2025-05-10', ['A'])['status'], 'FAIL')
    def test_shared_upstream(self):
        x=copy.deepcopy(BASE); b=x['sources'][0].copy(); b['id']='B'; x['sources'].append(b)
        self.assertEqual(audit(x, '2025-05-10', ['A','B'])['shared_independence_groups'], {'one':['A','B']})
    def test_month_only_is_not_day(self):
        with self.assertRaises(ValueError): audit(BASE, '2025-05', ['A'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
