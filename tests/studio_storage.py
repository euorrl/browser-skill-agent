"""统一 skills 路径、旧目录迁移、原地修改及默认参数同步。"""
import json
from pathlib import Path
import tempfile
import unittest
from studio import fixture
from browser_skill_agent.studio.store import Store

class Tests(unittest.TestCase):
    def test_new_flow_uses_skills_file_directly(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);_,source=fixture(root);store=Store(root);item=store.items[0]
            self.assertEqual(store.path(item['id']),source.resolve())
            self.assertFalse((root/'data/flows'/item['id']/'SKILL.md').exists())
            self.assertEqual(store.add(source)['id'],item['id'])
            store.update(item['id'],{'defaults':{'query':'机器学习'},'definition':source.read_text(encoding='utf-8').replace('查询指定资料','查询新资料')})
            self.assertIn('查询新资料',source.read_text(encoding='utf-8'))
            self.assertEqual(json.loads((source.parent/'example_params.json').read_text(encoding='utf-8')),{'query':'机器学习'})
            self.assertEqual(Store(root).path(item['id']),source.resolve())
    def test_old_library_migration_preserves_latest_copy_and_deleted_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);_,source=fixture(root);folder=root/'data/flows';folder.mkdir(parents=True)
            old=folder/'active';old.mkdir();latest=source.read_text(encoding='utf-8').replace('查询指定资料','用户已修改的目标')
            (old/'SKILL.md').write_text(latest,encoding='utf-8')
            gone=folder/'deleted';gone.mkdir();(gone/'SKILL.md').write_text(latest,encoding='utf-8')
            (folder/'index.json').write_text(json.dumps([{'id':'active','name':'我的查询','description':'说明','defaults':{'query':'默认值'},'status':'passed','issues':[],'last_result':None}]),encoding='utf-8')
            store=Store(root)
            self.assertEqual(len(store.items),1)
            self.assertEqual(store.path('active'),source.resolve())
            self.assertEqual(source.read_text(encoding='utf-8'),latest)
            self.assertTrue((old/'SKILL.md').exists())
            self.assertEqual(Store(root).items[0]['name'],'我的查询')
            store.delete('active');self.assertEqual(Store(root).items,[])
            self.assertTrue(source.exists())
    def test_import_external_flow_copies_into_skills(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);_,source=fixture(root/'other');store=Store(root)
            item=store.add(source)
            self.assertTrue(store.path(item['id']).is_relative_to(root/'skills'))
            self.assertEqual(item['defaults'],{'query':'人工智能'})
            original=source.read_text(encoding='utf-8')
            store.update(item['id'],{'definition':original.replace('查询指定资料','新目标')})
            self.assertEqual(source.read_text(encoding='utf-8'),original)

if __name__=='__main__':unittest.main()
