"""Exercise configured helper wording without displaying windows or using SSH."""
import ast,importlib.util,json,os,pathlib,sys,tempfile,types,unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'assistance'))
from family_identity import identity,helper_config
class HelperIdentity(unittest.TestCase):
    def test_legacy_fallback_and_new_helper_config(self):
        with tempfile.TemporaryDirectory() as folder:
            home=pathlib.Path(folder);config=home/'.config/family-help';config.mkdir(parents=True)
            (config/'dad.json').write_text('{"label":"Learner"}')
            self.assertEqual(identity(helper_config(home)),('Dad','dad'))
            (config/'helper.json').write_text('{"label":"Learner","helper_label":"Mom","helper_slug":"mom"}')
            self.assertEqual(identity(helper_config(home)),('Mom','mom'))
            for bad in ({'helper_label':'bad\nlabel'},{'helper_slug':'mom;id'}):
                with self.assertRaises(ValueError):identity(bad)
    def test_widget_text_and_parent_action_cards(self):
        text=(ROOT/'assistance/family-help-widget').read_text()
        for helper_name,slug in [('Mom','mom'),('Guardian Lee','parent')]:
            with self.subTest(helper=helper_name),tempfile.TemporaryDirectory() as folder:
                labels=[];placeholders=[];temp=pathlib.Path(folder)
                child=temp/'child.json';child.write_text(json.dumps({'uid':os.getuid(),'state':str(temp/'state')}))
                tree=ast.parse(text.replace('/etc/family-help/child.json',str(child)))
                methods=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='HelpApp').body
                selected=[node for node in methods if isinstance(node,ast.FunctionDef) and node.name in ('build_child','build_parent')]
                class Node:
                    def __init__(self,*args,**kwargs):
                        if 'label' in kwargs:labels.append(kwargs['label'])
                    def __getattr__(self,name):
                        if name=='set_placeholder_text':return placeholders.append
                        return lambda *args,**kwargs:Node()
                gtk=types.SimpleNamespace(**{name:Node for name in ('CheckButton','Entry','Frame','Picture','Label','EventControllerKey')},PropagationPhase=types.SimpleNamespace(CAPTURE=1))
                request={'id':'a'*32,'message':'Please help','topic':'help'}
                ns={'Gtk':gtk,'GLib':types.SimpleNamespace(timeout_add=lambda *args:None),'os':os,'json':json,'pathlib':pathlib,'time':__import__('time'),'re':__import__('re'),'sys':types.SimpleNamespace(argv=['widget','helper','a'*32]),'read':lambda path:request,'HELPER':helper_name,'HELPER_SLUG':slug,'IDENTITY_CONFIG':{'label':'Learner'}}
                exec(compile(ast.Module(body=selected,type_ignores=[]),'<widget methods>','exec'),ns)
                app=types.SimpleNamespace(label=lambda value,*args:labels.append(value) or Node(),button=lambda value,*args:labels.append(value) or Node(),row=Node,box=Node(),win=Node(),refresh=lambda:True,key=lambda *args:None,send=lambda:None,capture=lambda:None,paste=lambda:None,clear_image=lambda:None,action=lambda *args,**kwargs:None)
                ns['build_child'](app)
                self.assertEqual(placeholders,[f"What would you like {helper_name}'s help with?"])
                for label in (f'Ask {helper_name}  [Ctrl+Enter]',f'Let {helper_name} type',f'Stop {helper_name} typing',f'Watch {helper_name}'):self.assertIn(label,labels)
                self.assertFalse(any('Dad' in value for value in labels))
                app.choose=lambda *args:None;ns['build_parent'](app)
                for label in ('Help together','Admin demonstration','Watch only','Dismiss'):self.assertIn(label,labels)
                ns['IDENTITY_CONFIG']['quick_approval']=True
                labels.clear();ns['build_parent'](app)
                for label in ('Help together','Admin demonstration','Watch only','Dismiss'):self.assertIn(label,labels)
                ns['IDENTITY_CONFIG'].pop('quick_approval')
                request.update(topic='admin',time=__import__('time').time(),software={'action':'install','packages':['extra/jq']})
                ns['build_parent'](app)
                for label in ('Review and approve','Deny request'):self.assertIn(label,labels)
if __name__=='__main__':unittest.main()
