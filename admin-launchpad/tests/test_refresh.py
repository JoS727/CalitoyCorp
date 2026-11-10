import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from refresh import build, collect, https_url

def repo(name='sample', **kwargs):
    return {'full_name': 'owner/'+name, 'name': name, 'owner': {'login':'owner'}, 'private': True, **kwargs}

class RefreshTests(unittest.TestCase):
    def test_pagination(self):
        pages=[[repo(str(i)) for i in range(100)], [repo('last')]]
        self.assertEqual(len(collect('not-real', {'owner'}, lambda *_: pages.pop(0))),101)
    def test_empty_is_not_published(self):
        with self.assertRaises(RuntimeError): build([],{},None)
    def test_lost_access_preserves_previous(self):
        with self.assertRaises(RuntimeError): build([repo()],{},{'repos':[{'repo':'owner/missing'}]})
    def test_explicit_shrink(self):
        self.assertEqual(len(build([repo()],{},{'repos':[{'repo':'owner/missing'}]},True)['repos']),1)
    def test_metadata_does_not_imply_live(self):
        r=build([repo(homepage='https://example.invalid')],{},None)['repos'][0]
        self.assertEqual(r['stage'],'Unknown'); self.assertEqual(r['site'],'');self.assertTrue(r['repo_homepage_unverified'])
    def test_private_overrides_survive(self):
        r=build([repo()],{'owner/sample':{'verified':True,'stage':'Live','admin':'https://example.invalid/admin'}},None)['repos'][0]
        self.assertEqual(r['stage'],'Live');self.assertTrue(r['admin'])
    def test_unverified_links_not_promoted(self):
        self.assertEqual(build([repo()],{'owner/sample':{'stage':'Live','admin':'https://example.invalid'}},None)['repos'][0]['admin'],'')
    def test_archived(self):
        self.assertEqual(build([repo(archived=True)],{},None)['repos'][0]['stage'],'Archived')
    def test_unsafe_urls(self):
        for s in ['javascript:alert(1)','http://example.invalid','https://u:p@example.invalid',None,'https://[']:
            self.assertEqual(https_url(s),'')
    def test_unknown_stage(self):
        self.assertEqual(build([repo()],{'owner/sample':{'verified':True,'stage':'Imaginary'}},None)['repos'][0]['stage'],'Unknown')

if __name__=='__main__': unittest.main()
