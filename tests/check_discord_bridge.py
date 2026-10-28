import ast
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('bridge',Path(__file__).resolve().parents[1]/'integrations/family_discord_bridge.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Tests(unittest.TestCase):
 def test_actual_bot_allowlist_without_loading_network_library(self):
  path=Path(__file__).resolve().parents[1]/'integrations/family_discord_bot.py'
  function=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='authorized')
  scope={};exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),scope)
  allowed=scope['authorized'];config={'guild_id':'1','channel_id':'2','parents':{'dad':'3','mom':'4'}}
  self.assertTrue(allowed(config,1,2,3));self.assertTrue(allowed(config,1,2,4))
  for where in [(9,2,3),(1,9,3),(1,2,9),(None,None,3)]:self.assertFalse(allowed(config,*where))
 def test_permitted(self):
  self.assertTrue(m.permitted('apps',{'op':'poll'}))
  self.assertTrue(m.permitted('breaks',{'op':'break-decision','id':'a'*32,'decision':'deny'}))
 def test_schedule_shell_and_wrong_protocol_denied(self):
  for value in [{'op':'apply','policy':{}},{'op':'pause','peer':'son','minutes':15},{'op':'shell','command':'true'},{'op':'poll','extra':True},{'op':'break-decision','id':'../../x','decision':'approve'}]:
   for kind in ['apps','breaks']:self.assertFalse(m.permitted(kind,value))
  self.assertFalse(m.permitted('apps',{'op':'break-pending'}))
  self.assertFalse(m.permitted('breaks',{'op':'poll'}))

if __name__=='__main__':unittest.main()
