"""Both parent capabilities get scoped break cards, never automatic approvals."""
import tempfile,tomllib
import ast,datetime as dt,pathlib,re,sys,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'assistance'))
import family_policy_client as client
class WidgetTests(unittest.TestCase):
    def methods(self):
        tree=ast.parse((ROOT/'assistance/family-help-widget').read_text())
        return [node for cls in tree.body if isinstance(cls,ast.ClassDef) for node in cls.body if isinstance(node,ast.FunctionDef) and node.name in ('build_parent','build_break','decide_break')]
    def test_popup_matches_ask_dad_palette_and_keeps_fixed_footer(self):
        tree=ast.parse((ROOT/'assistance/family-time-widget').read_text());method=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='theme_css')
        ns={};exec(compile(ast.Module(body=[method],type_ignores=[]),'<popup theme>','exec'),ns)
        css=ns['theme_css']()
        for color in (b'#101820',b'#74e0c3',b'#70d5ff',b'#183f3a'):self.assertIn(color,css)
        source=(ROOT/'assistance/family-time-widget').read_text()
        self.assertIn('layout.append(scroll);layout.append(self.footer)',source)
        self.assertIn("self.apply,self.footer",source)
    def test_schedule_save_reads_fresh_state_and_confirms(self):
        tree=ast.parse((ROOT/'assistance/family-time-widget').read_text())
        method=next(n for cls in tree.body if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='operation')
        packets=[];labels=[];data={'revision':8,'policy':{'subjects':{'child':{'mode':'off'}}}}
        def send(packet):packets.append(packet);return data if packet['op']=='get' else {'revision':8}
        ns={'request':send};exec(compile(ast.Module(body=[method],type_ignores=[]),'<time save>','exec'),ns)
        app=types.SimpleNamespace(config={'policy_peer':'child'},render=lambda value:labels.append(value),feedback=types.SimpleNamespace(set_text=labels.append),run_task=lambda work,done:done(work()))
        ns['operation'](app,{'op':'apply','base_revision':7})
        self.assertEqual(packets,[{'op':'apply','base_revision':7},{'op':'get'}]);self.assertIs(labels[0],data);self.assertIn('Saved successfully',labels[1])
    def test_break_cards_for_both_roles(self):
        for capability in ('technical','approver'):
            labels=[]
            class Node:
                def set_sensitive(self,*_):pass
            request={'id':'a'*32,'time':dt.datetime.now(dt.timezone.utc).timestamp(),'topic':'break','message':'Skip this break','break_request':{'peer':'child','episode':'b'*32,'revision':0,'change':'skip','minutes':0}}
            ns={'IDENTITY_CONFIG':{'capability':capability,'label':'Learner'},'pathlib':pathlib,'sys':types.SimpleNamespace(argv=['widget','helper','a'*32]),'re':re,'read':lambda _:request}
            exec(compile(ast.Module(body=self.methods(),type_ignores=[]),'<parent break>','exec'),ns)
            app=types.SimpleNamespace(label=lambda text,*_:labels.append(text) or Node(),button=lambda text,*args:labels.append(text) or Node(),row=lambda:None,choose=lambda _:None,busy=False,win=types.SimpleNamespace(close=lambda:None))
            for name in ('build_break','decide_break'):setattr(app,name,types.MethodType(ns[name],app))
            ns['build_parent'](app)
            self.assertIn('Approve break change',labels);self.assertIn('Deny request',labels)
            self.assertNotIn('Admin demonstration',labels);self.assertNotIn('Approve installation',labels)
            packets=[]
            def send(packet):packets.append(packet);return {'status':'approved'}
            app.background=lambda work,done:done(work(),None)
            app.break_feedback=types.SimpleNamespace(set_text=lambda text:labels.append(text))
            with patch.object(client,'request',side_effect=send):app.decide_break('approve')
            self.assertEqual(packets,[{'op':'break-decision','id':'a'*32,'decision':'approve'}])
            self.assertIn('Break request: approved',labels)
if __name__=='__main__':unittest.main()
