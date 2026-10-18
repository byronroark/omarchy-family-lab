"""Approval-only cards use worker plans and expose no technical-session actions."""
import ast,json,os,pathlib,sys,tempfile,time,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'assistance'))
class ApprovalWidget(unittest.TestCase):
    def test_reviewed_card_and_no_technical_actions(self):
        for supported in (True,False):
            with self.subTest(supported=supported),tempfile.TemporaryDirectory() as folder:
                home=pathlib.Path(folder);reviews=home/'.local/state/family-help/reviews';reviews.mkdir(parents=True)
                review={'id':'a'*32,'review':'b'*32,'digest':'c'*64,'expires':time.time()+60,'plan':{'supported':supported,'title':'Root reviewed app','reason':'Exact plan','transaction':['extra/jq=1.8.1-1'] if supported else []}}
                (reviews/('a'*32+'.json')).write_text(json.dumps(review));labels=[]
                class Node:
                    def __init__(self,*args,**kwargs):
                        if 'label' in kwargs:labels.append(kwargs['label'])
                    def __getattr__(self,name):return lambda *args,**kwargs:None
                code=ast.parse((ROOT/'assistance/family-help-widget').read_text());methods=next(item for item in code.body if isinstance(item,ast.ClassDef)).body
                method=next(item for item in methods if isinstance(item,ast.FunctionDef) and item.name=='build_approver')
                ns={'pathlib':pathlib,'json':json,'time':time,'bounded_file':lambda path,limit:path.read_bytes(),'Gtk':types.SimpleNamespace(ScrolledWindow=Node,Label=Node)}
                exec(compile(ast.Module(body=[method],type_ignores=[]),'<approval card>','exec'),ns)
                app=types.SimpleNamespace(label=lambda value,*args:labels.append(value) or Node(),button=lambda value,*args:labels.append(value) or Node(),choose=lambda *args:None,row=Node,box=types.SimpleNamespace(append=lambda node:None))
                with patch.object(pathlib.Path,'home',return_value=home):ns['build_approver'](app,{'id':'a'*32,'software':{}})
                self.assertIn('Deny request',labels);self.assertEqual('Approve installation' in labels,supported)
                for forbidden in ('Admin demonstration','Help together','Watch only','Review and approve'):self.assertNotIn(forbidden,labels)
                self.assertIn('Root reviewed app',labels)
    def test_nonsoftware_help_has_dismiss_only(self):
        tree=ast.parse((ROOT/'assistance/family-help-widget').read_text());method=next(n for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='build_approver')
        ns={};exec(compile(ast.Module(body=[method],type_ignores=[]),'<card>','exec'),ns)
        buttons=[];app=types.SimpleNamespace(label=lambda *args:None,button=lambda value,*args:buttons.append(value),row=lambda:None,choose=lambda *_:None)
        ns['build_approver'](app,{'message':'Please help'});self.assertEqual(buttons,['Dismiss'])
if __name__=='__main__':unittest.main()
