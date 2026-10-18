import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'assistance'))
from family_theme import themed_css
class ThemeTests(unittest.TestCase):
    def test_theme_changes_and_invalid_values(self):
        css=b'.x { background:#101820; color:#d9e5ee; border:1px solid #74e0c3; }'
        with tempfile.TemporaryDirectory() as root:
            path=pathlib.Path(root)/'.local/state/omarchy/current/theme/colors.toml';path.parent.mkdir(parents=True)
            self.assertEqual(themed_css(css,root),css)
            for bg,fg,accent in [('#ffffff','#111111','#123456'),('#111111','#eeeeee','#abcdef')]:
                path.write_text(f'background="{bg}"\nforeground="{fg}"\naccent="{accent}"\n')
                value=themed_css(css,root)
                for color in (bg,fg,accent):self.assertIn(color.encode(),value)
            path.write_text('accent="red; padding:999px"\n');self.assertEqual(themed_css(css,root),css)
            path.write_text('not valid toml');self.assertEqual(themed_css(css,root),css)
if __name__=='__main__':unittest.main()
