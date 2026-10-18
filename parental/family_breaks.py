"""Persistent break episodes and parent decisions. No display or power operations."""
import copy,json,math,re,uuid

def number(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('Break setting outside permitted range')
    return value

def settings(value):
    if not isinstance(value,dict) or set(value)!={'enabled','use_minutes','break_minutes'} or type(value['enabled']) is not bool:raise ValueError('Invalid break settings')
    number(value['use_minutes'],1,240);number(value['break_minutes'],1,120)
    return value

class Breaks:
    def __init__(self,path,read,write):
        self.path,self.write=path,write
        self.state=read(path) if path.exists() else {'version':1,'learners':{},'requests':{}}
        state=self.state
        if not isinstance(state,dict) or set(state)!={'version','learners','requests'} or state['version']!=1 or not isinstance(state['learners'],dict) or len(state['learners'])>8 or not isinstance(state['requests'],dict) or len(state['requests'])>128:raise ValueError('Invalid persisted break state')
        for peer,row in state['learners'].items():
            if not isinstance(peer,str) or not isinstance(row,dict) or set(row)!={'used','rest'} or type(row['used']) not in (int,float) or not math.isfinite(row['used']) or not 0<=row['used']<=86400:raise ValueError('Invalid break usage')
            if row['rest'] is not None:
                rest=row['rest']
                if not isinstance(rest,dict) or set(rest)!={'episode','revision','expires','deadline','boot','protected','seconds'} or not re.fullmatch('[a-f0-9]{32}',str(rest['episode'])) or type(rest['revision']) is not int or rest['revision']<0 or not isinstance(rest['boot'],str):raise ValueError('Invalid break episode')
                if type(rest['protected']) is not bool:raise ValueError('Invalid guard state')
                number(rest['seconds'],0,7200)
                for field in ('expires','deadline'):
                    if type(rest[field]) not in (int,float) or not math.isfinite(rest[field]) or not 0<=rest[field]<=10**12:raise ValueError('Invalid break deadline')
        for identifier,item in state['requests'].items():
            if not re.fullmatch('[a-f0-9]{32}',identifier) or not isinstance(item,dict) or set(item)!={'id','peer','episode','revision','parent','change','minutes','created','status'} or item['id']!=identifier or item['peer'] not in state['learners'] or item['status'] not in ('pending','approved','denied','expired'):raise ValueError('Invalid break request')
            if not re.fullmatch('[a-f0-9]{32}',str(item['episode'])) or type(item['parent']) is not int or item['parent']<=0 or type(item['revision']) is not int or item['revision']<0 or item['change'] not in ('skip','shorten','extend'):raise ValueError('Invalid break request identity')
            number(item['minutes'],0,120)
            if type(item['created']) not in (int,float) or not math.isfinite(item['created']):raise ValueError('Invalid break request time')
    def commit(self,value):
        self.write(self.path,value);self.state=value
    @staticmethod
    def remaining(rest,now,boot,elapsed):
        # Within a boot, use the kernel clock that includes suspend. Wall-clock
        # changes cannot shorten a break. Across boots, use the saved wall deadline.
        if not rest['protected']:return rest['seconds']
        if rest['boot']==boot:return max(0,rest['deadline']-elapsed)
        return max(0,rest['expires']-now)
    def view(self,peer,now,boot,elapsed):
        row=self.state['learners'].get(peer,{'used':0,'rest':None});rest=row['rest']
        return {'used_seconds':round(row['used']),'episode':rest['episode'] if rest else None,'revision':rest['revision'] if rest else 0,'remaining_seconds':math.ceil(self.remaining(rest,now,boot,elapsed)) if rest else 0,'phase':('break' if rest['protected'] else 'due') if rest else 'use'}
    def tick(self,policies,active,delta,now,boot,elapsed):
        state=copy.deepcopy(self.state);result={}
        for peer,config in policies.items():
            settings(config);row=state['learners'].setdefault(peer,{'used':0,'rest':None})
            if not config['enabled']:continue
            rest=row['rest'];was_rest=rest is not None
            if rest and self.remaining(rest,now,boot,elapsed)<=0:row.update(used=0,rest=None)
            elif rest and rest['boot']!=boot:
                left=self.remaining(rest,now,boot,elapsed);rest.update(boot=boot,deadline=elapsed+left,expires=now+left)
            if row['rest'] is None:
                if peer in active and not was_rest:row['used']=min(86400,row['used']+max(0,min(10,delta)))
                if row['used']>=config['use_minutes']*60:
                    seconds=config['break_minutes']*60
                    row['rest']={'episode':uuid.uuid4().hex,'revision':0,'expires':now+seconds,'deadline':elapsed+seconds,'boot':boot,'protected':False,'seconds':seconds}
        for request in state['requests'].values():
            rest=state['learners'][request['peer']]['rest']
            if request['status']=='pending' and (not rest or request['episode']!=rest['episode'] or request['revision']!=rest['revision'] or now-request['created']>900):request['status']='expired'
        # Bounded history. Never prune a live request to permit replay.
        expired=[key for key,item in state['requests'].items() if item['status']!='pending']
        for key in expired[:-64]:del state['requests'][key]
        if state!=self.state:self.commit(state)
        for peer,config in policies.items():
            if config['enabled']:result[peer]=dict(self.view(peer,now,boot,elapsed),use_minutes=config['use_minutes'],break_minutes=config['break_minutes'])
        return result
    def protected(self,peer,episode,now,boot,elapsed):
        state=copy.deepcopy(self.state);row=state['learners'].get(peer);rest=row['rest'] if row else None
        if not rest or rest['episode']!=episode:raise ValueError('Break episode changed')
        if not rest['protected']:
            rest.update(protected=True,expires=now+rest['seconds'],deadline=elapsed+rest['seconds'],boot=boot)
            self.commit(state)
        return self.view(peer,now,boot,elapsed)
    def ask(self,peer,parent,episode,revision,change,minutes,now,boot,elapsed):
        number(parent,1,2**31-1);number(minutes,0,120);number(revision,0,2**31-1)
        if change not in ('skip','shorten','extend') or (change=='skip' and minutes!=0) or (change!='skip' and minutes==0):raise ValueError('Invalid requested break change')
        current=self.view(peer,now,boot,elapsed)
        if current['episode']!=episode or not episode or current['revision']!=revision or current['remaining_seconds']<=0:raise ValueError('Break changed; refresh before asking')
        pending=[row for row in self.state['requests'].values() if row['peer']==peer and row['status']=='pending']
        if len(pending)>=4:raise ValueError('Wait for a parent to answer the current break requests')
        for item in pending:
            if (item['parent'],item['change'],item['minutes'])==(parent,change,minutes):return copy.deepcopy(item)
        state=copy.deepcopy(self.state);identifier=uuid.uuid4().hex
        item={'id':identifier,'peer':peer,'episode':episode,'revision':revision,'parent':parent,'change':change,'minutes':minutes,'created':now,'status':'pending'}
        state['requests'][identifier]=item;self.commit(state);return copy.deepcopy(item)
    def pending(self,parent):return [copy.deepcopy(item) for item in self.state['requests'].values() if item['parent']==parent and item['status']=='pending']
    def decide(self,parent,identifier,choice,now,boot,elapsed):
        if choice not in ('approve','deny'):raise ValueError('Choose approve or deny')
        state=copy.deepcopy(self.state);item=state['requests'].get(identifier)
        if not item or item['parent']!=parent or item['status']!='pending':raise ValueError('Break request is unavailable for this parent')
        rest=state['learners'][item['peer']]['rest']
        if not rest or rest['episode']!=item['episode'] or rest['revision']!=item['revision'] or self.remaining(rest,now,boot,elapsed)<=0 or not 0<=now-item['created']<=900:raise ValueError('Break request expired or changed')
        if choice=='approve':
            remaining=self.remaining(rest,now,boot,elapsed)
            seconds=0 if item['change']=='skip' else max(0,remaining-item['minutes']*60) if item['change']=='shorten' else min(7200,remaining+item['minutes']*60)
            rest.update(revision=rest['revision']+1,boot=boot,expires=now+seconds,deadline=elapsed+seconds,seconds=math.ceil(seconds))
            if seconds==0:state['learners'][item['peer']].update(used=0,rest=None)
        item['status']='approved' if choice=='approve' else 'denied'
        self.commit(state);return {'id':identifier,'status':item['status']}
