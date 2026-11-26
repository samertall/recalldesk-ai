import asyncio, unittest
from app import run
class TestWorkflow(unittest.TestCase):
    def test_baseline(self):
        s=asyncio.run(run('baseline'))['summary']; self.assertEqual((s['tickets'],s['reused'],s['correct']),(36,0,36))
    def test_shared(self):
        r=asyncio.run(run('local')); s=r['summary']; self.assertEqual((s['tickets'],s['reused'],s['correct']),(36,24,36)); self.assertTrue(all(t['repeat'] for t in r['traces'] if t['reused'])); self.assertEqual(s['total_steps'],144)
if __name__=='__main__': unittest.main()
