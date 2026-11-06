"""正式事实登记回归：真实样本、前视阻断、摘要、追加约束及计算桥接；禁止网络。"""
import copy,json,socket,sqlite3,sys,unittest,uuid
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
def deny(*a,**kw):raise AssertionError('正式事实测试禁止网络')
socket.socket.connect=deny;socket.create_connection=deny
from financial_reporting.registry import read_as_of,verify_payload,registered_metric_batch,initialize,register
from financial_reporting.pipeline import digest
from data_store import LocalStore,canonical
from validate_research import structural,load
from finance_tools.metric_pipeline import run_batch

class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=read_as_of('JP:7974','2026-10-11T23:59:59+09:00')
    def test_real_registered_counts(self):
        self.assertEqual(len(self.rows),30)
        self.assertEqual(len(read_as_of('US:INTU:CIK896878','2026-10-11T23:59:59+09:00')),42)
        self.assertEqual(len(read_as_of('JP:6758:CIK313838','2026-10-11T23:59:59+09:00')),44)
    def test_before_observation_returns_no_facts(self):
        self.assertEqual(read_as_of('JP:7974','2026-07-07T00:00:00+09:00'),[])
    def test_future_payload_blocks(self):
        with LocalCatalog() as c:
            with self.assertRaisesRegex(ValueError,'早于'):verify_payload(c,self.rows[0],'2026-01-01T00:00:00Z')
    def test_modified_value_blocks(self):
        payload=copy.deepcopy(self.rows[0]);payload['fact']['value']='0'
        with LocalCatalog() as c:
            with self.assertRaisesRegex(ValueError,'登记摘要'):verify_payload(c,payload)
    def test_wrong_original_hash_blocks(self):
        payload=copy.deepcopy(self.rows[0]);payload['original_source']['sha256']='0'*64
        payload['registration_id']=digest(canonical({k:v for k,v in payload.items() if k!='registration_id'}))
        with LocalCatalog() as c:
            with self.assertRaisesRegex(ValueError,'归档摘要'):verify_payload(c,payload)
    def test_append_only(self):
        # 独立项目内目录，绝不尝试修改真实历史。
        c=LocalStore('.cache/registry-test-'+uuid.uuid4().hex)
        try:
            initialize(c)
            payload=self.rows[0]
            with LocalCatalog() as original:
                for key in ['original_source','evidence_source']:
                    link=payload[key]
                    manifest=json.loads(original.db.execute('SELECT manifest_json FROM sources WHERE source_id=? AND revision=?',
                                                           (link['source_id'],link['revision'])).fetchone()[0])
                    c.register_source(manifest)
                row=original.db.execute('SELECT * FROM financial_facts WHERE registration_id=?',(payload['registration_id'],)).fetchone()
            c.db.execute('INSERT INTO financial_facts VALUES(?,?,?,?,?,?,?,?,?,?,?)',tuple(row))
            for query in ["UPDATE financial_facts SET available_at='x'",'DELETE FROM financial_facts']:
                with self.assertRaises(sqlite3.IntegrityError):c.db.execute(query)
            self.assertEqual(c.db.execute('SELECT COUNT(*) FROM financial_facts').fetchone()[0],1)
        finally:c.close()
    def test_source_precision_legacy(self):
        schema=load(ROOT/'schemas/source-manifest.schema.json')
        with LocalCatalog() as c:
            source=json.loads(c.db.execute('SELECT manifest_json FROM sources WHERE source_id=?',(self.rows[0]['original_source']['source_id'],)).fetchone()[0])
        structural(source,schema,schema)
        source['schema_version']='1.0.0'
        with self.assertRaises(ValueError):structural(source,schema,schema)
    def test_registered_calculation_bridge(self):
        batch=registered_metric_batch('US:INTU:CIK896878','2026-07-31','2026-10-11T23:59:59+09:00')
        result=run_batch(batch)
        self.assertFalse(batch['is_synthetic'])
        self.assertEqual(len(batch['facts']),2)
        self.assertIn('operating_margin',json.dumps(result))
    def test_repeated_registration_is_idempotent(self):
        r=register('examples/financial/nintendo-2026.json')
        self.assertTrue(r['idempotent'])
        self.assertEqual(r['registered_fact_count'],30)
    def test_failed_dts_blocks_registration(self):
        rows=read_as_of('US:INTU:CIK896878','2026-10-11T23:59:59+09:00')
        report=json.loads((ROOT/rows[0]['report_ref']['path']).read_text(encoding='utf-8'))
        report['report_id']='test-failed-dts'
        with patch('financial_reporting.registry.run',return_value=report),\
             patch('financial_reporting.taxonomy.validation_fingerprint',return_value='mock-fingerprint'),\
             patch('financial_reporting.taxonomy.validate_dts',return_value=({}, {'status':'blocked'})):
            with self.assertRaisesRegex(ValueError,'DTS'):
                register('examples/financial/intu-2026.json','.cache/blocked-dts-'+uuid.uuid4().hex)
    def test_taxonomy_path_traversal_rejected(self):
        from financial_reporting.taxonomy import safe_member
        for path in ['../schema.xsd','C:/schema.xsd','/schema.xsd','..\\schema.xsd']:
            with self.assertRaises(ValueError):safe_member(path)

class LocalCatalog:
    def __enter__(self):self.catalog=LocalStore();return self.catalog
    def __exit__(self,*a):self.catalog.close()

if __name__=='__main__':unittest.main()
