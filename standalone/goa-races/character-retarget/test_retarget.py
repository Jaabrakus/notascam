import copy
import tempfile
import unittest
from pathlib import Path
import retarget

class RetargetTests(unittest.TestCase):
    def setUp(self):
        self.master = retarget.DEFAULT_MASTER
        self.profile = retarget.read(self.master/'profiles/elf-male.json')

    def test_identity_bow_mapping(self):
        self.assertEqual(retarget.fit(self.profile,self.profile)['poseTargets']['bow'],retarget.BOW)

    def test_flags_asymmetric_arm(self):
        p=copy.deepcopy(self.profile)
        p['views'][0]['arms']['right']=[[23,29],[23,32],[23,35]]
        warnings,_=retarget.audit(p,self.master/'preview/assets')
        self.assertTrue(any('South arms' in w for w in warnings))

    def test_rejects_invalid_joint(self):
        p=copy.deepcopy(self.profile);p['views'][0]['neck']=[float('nan'),25]
        with self.assertRaises(ValueError):retarget.audit(p,self.master/'preview/assets')

    def test_rejects_asset_escape(self):
        p=copy.deepcopy(self.profile);p['views'][0]['parts']['head']='../outside.png'
        with self.assertRaises(ValueError):retarget.audit(p,self.master/'preview/assets')

    def test_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'keep.txt';p.write_text('keep')
            with self.assertRaises(ValueError):retarget.build({'output':d})
            self.assertEqual(p.read_text(),'keep')

if __name__=='__main__':unittest.main()
