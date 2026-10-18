import json,pathlib,re,unittest
BASE=pathlib.Path(__file__).resolve().parents[1]/'browser/google-home-redirect'
class RedirectTests(unittest.TestCase):
 def test_homepage_only_and_minimal_permissions(self):
  manifest=json.loads((BASE/'manifest.json').read_text());rules=json.loads((BASE/'rules.json').read_text());self.assertEqual(len(rules),1)
  self.assertEqual(manifest['permissions'],['declarativeNetRequestWithHostAccess']);self.assertEqual(set(manifest['host_permissions']),{'*://google.com/*','*://www.google.com/*'})
  self.assertNotIn('background',manifest);self.assertNotIn('content_scripts',manifest)
  r=rules[0];self.assertEqual(r['condition']['resourceTypes'],['main_frame']);self.assertEqual(r['action']['redirect']['url'],'https://www.google.com/safesearch')
  pattern=r['condition']['regexFilter']
  for url in ('https://google.com/','https://www.google.com/','http://google.com/'):self.assertRegex(url,pattern)
  for url in ('https://www.google.com/search?q=dinosaurs','https://www.google.com/?q=dinosaurs','https://www.google.com/safesearch','https://accounts.google.com/','https://google.com.evil.example/'):self.assertNotRegex(url,pattern)
if __name__=='__main__':unittest.main()
