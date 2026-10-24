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
        ns={'themed_css':lambda css,home=None:css};exec(compile(ast.Module(body=[method],type_ignores=[]),'<popup theme>','exec'),ns)
        css=ns['theme_css']()
        for color in (b'#101820',b'#74e0c3',b'#70d5ff',b'#183f3a'):self.assertIn(color,css)
        source=(ROOT/'assistance/family-time-widget').read_text()
        self.assertIn('layout.append(scroll);layout.append(self.feedback);layout.append(self.footer)',source)
        self.assertIn("self.apply,self.footer",source)
    def test_feedback_is_mirrored_in_a_fixed_top_banner(self):
        source=(ROOT/'assistance/family-time-widget').read_text()
        self.assertIn("self.feedback.bind_property('label',self.top_feedback,'label',GObject.BindingFlags.SYNC_CREATE)",source)
        self.assertLess(source.index('layout.append(self.top_feedback)'),source.index('layout.append(scroll)'))

    def test_schedule_save_reads_fresh_state_and_confirms(self):
        tree=ast.parse((ROOT/'assistance/family-time-widget').read_text())
        method=next(n for cls in tree.body if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='operation')
        packets=[];labels=[];data={'revision':8,'policy':{'subjects':{'child':{'mode':'off'}}}}
        def send(packet):packets.append(packet);return data if packet['op']=='get' else {'revision':8}
        ns={'request':send};exec(compile(ast.Module(body=[method],type_ignores=[]),'<time save>','exec'),ns)
        app=types.SimpleNamespace(config={'policy_peer':'child'},render=lambda value:labels.append(value),feedback=types.SimpleNamespace(set_text=labels.append),run_task=lambda work,done:done(work()))
        operation={'op':'apply','base_revision':7,'policy':data['policy']}
        ns['operation'](app,operation)
        self.assertEqual(packets,[operation,{'op':'get'}]);self.assertIs(labels[0],data);self.assertIn('Confirmed: mode off',labels[1])
    def time_method(self,name,namespace):
        tree=ast.parse((ROOT/'assistance/family-time-widget').read_text())
        method=next(n for cls in tree.body if isinstance(cls,ast.ClassDef) for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
        exec(compile(ast.Module(body=[method],type_ignores=[]),'<time widget>','exec'),namespace)
        return namespace[name]
    def test_each_selected_mode_is_sent_without_changing_other_fields(self):
        import copy
        for selected in ('off','monitor','enforce'):
            packets=[]
            policy={'timezone':'UTC','subjects':{'child':{'mode':'enforce','hours':{'mon':[['07:00','22:30']]},'daily_minutes':{'mon':90},'browser':{'enabled':False}}}}
            app=types.SimpleNamespace(snapshot={'revision':13,'policy':policy},config={'policy_peer':'child'},
                mode_buttons={mode:types.SimpleNamespace(get_active=lambda mode=mode:mode==selected) for mode in ('off','monitor','enforce')},
                use=types.SimpleNamespace(get_value_as_int=lambda:70),rest=types.SimpleNamespace(get_value_as_int=lambda:15),
                timezone=types.SimpleNamespace(get_text=lambda:'UTC'),fields={'mon':(None,types.SimpleNamespace(get_text=lambda:'07:00-22:30'))},
                operation=packets.append,feedback=types.SimpleNamespace(set_text=self.fail))
            self.time_method('apply',{'copy':copy})(app)
            self.assertEqual(packets[0]['policy']['subjects']['child']['mode'],selected)
            self.assertEqual(policy['subjects']['child']['mode'],'enforce')
            self.assertEqual(packets[0]['base_revision'],13)
    def test_save_mismatch_never_claims_success_or_discards_edits(self):
        data={'revision':14,'policy':{'subjects':{'child':{'mode':'enforce'}}}}
        labels=[]
        app=types.SimpleNamespace(config={'policy_peer':'child'},render=lambda _:self.fail('Must retain edits'),feedback=types.SimpleNamespace(set_text=labels.append),run_task=lambda work,done:done(work()))
        operation=self.time_method('operation',{'request':lambda packet:data if packet['op']=='get' else {'revision':14}})
        with self.assertRaisesRegex(ValueError,'do not match'):
            operation(app,{'op':'apply','policy':{'subjects':{'child':{'mode':'off'}}}})
        self.assertFalse(labels)
    def test_bedtime_confirmation_uses_receipt_not_stale_status(self):
        from zoneinfo import ZoneInfo
        for enabled in (True,False):
            labels=[]
            data={'revision':13,'policy':{'timezone':'UTC','subjects':{'child':{'mode':'enforce'}}},'status':{}}
            def send(packet):
                return data if packet['op']=='get' else {'accepted':True,'enabled':enabled,'expires':1792800000}
            app=types.SimpleNamespace(config={'policy_peer':'child'},render=lambda _:None,feedback=types.SimpleNamespace(set_text=labels.append),run_task=lambda work,done:done(work()))
            self.time_method('operation',{'request':send,'dt':dt,'ZoneInfo':ZoneInfo})(app,{'op':'bedtime-today','enabled':enabled})
            self.assertIn('Bedtime skipped until' if enabled else 'Normal bedtime hours restored',labels[-1])
    def test_busy_requests_disable_controls_instead_of_silently_losing_clicks(self):
        changes=[];labels=[]
        app=types.SimpleNamespace(busy=False,controls=[types.SimpleNamespace(set_sensitive=changes.append)],feedback=types.SimpleNamespace(set_text=labels.append))
        thread=types.SimpleNamespace(Thread=lambda target,daemon:types.SimpleNamespace(start=target))
        method=self.time_method('run_task',{'threading':thread,'GLib':types.SimpleNamespace(idle_add=lambda callback:callback())})
        method(app,lambda:42,lambda value:labels.append(value))
        self.assertEqual(changes,[False,True]);self.assertEqual(labels[-1],42)
        app.busy=True;method(app,lambda:self.fail('Busy request must not run'),lambda _:None)
        self.assertIn('still running',labels[-1])

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
