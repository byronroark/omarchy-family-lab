"""Parent-only Discord setup acceptance. Real decisions stay disabled.

Uses outbound Gateway connections; no public listener or privileged intents.
Token and configuration arrive through systemd credentials, never arguments.
"""
import asyncio
import json
import os
import time
import math
from pathlib import Path
import discord
from discord import app_commands
from family_discord_pending import Pending,due


def authorized(config, guild, channel, user):
    return (str(guild) == str(config['guild_id'])
            and str(channel) == str(config['channel_id'])
            and str(user) in set(config['parents'].values()))


class TestCard(discord.ui.View):
    def __init__(self, config):
        super().__init__(timeout=300)
        self.config = config
        self.decided = False

    async def interaction_check(self, interaction):
        if authorized(self.config, interaction.guild_id, interaction.channel_id, interaction.user.id):
            return True
        await interaction.response.send_message('This control is restricted to enrolled parents in the approvals channel.', ephemeral=True)
        return False

    async def finish(self, interaction, choice):
        # No await before claiming the decision: one winner in the event loop.
        if self.decided:
            await interaction.response.send_message('This test already has a decision.', ephemeral=True)
            return
        self.decided = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f'Test {choice}. No app, break or lesson was changed.', view=self)
        self.stop()

    @discord.ui.button(label='Approve test', style=discord.ButtonStyle.success)
    async def approve(self, interaction, button):
        await self.finish(interaction, 'approved')

    @discord.ui.button(label='Deny test', style=discord.ButtonStyle.danger)
    async def deny(self, interaction, button):
        await self.finish(interaction, 'denied')


class Bot(discord.Client):
    def __init__(self, config):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.config = config
        self.tree = app_commands.CommandTree(self)
        self.pending = Pending(Path(os.environ.get('STATE_DIRECTORY','/tmp'))/'cards.sqlite3')

        @self.tree.command(name='relay-test', description='Test parent-only approval buttons without changing any family settings.', guild=discord.Object(id=int(config['guild_id'])))
        async def test(interaction: discord.Interaction):
            if not authorized(config, interaction.guild_id, interaction.channel_id, interaction.user.id):
                await interaction.response.send_message('Use the private approvals channel with an enrolled parent account.', ephemeral=True)
                return
            await interaction.response.send_message('Family Lab Manager setup test. Choose one button. Real approvals are not enabled yet.', view=TestCard(config))

    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(id=int(self.config['guild_id'])))
        if self.config.get('enabled'):
            self.worker = asyncio.create_task(self.watch())

    async def rpc(self, kind, operation):
        root=Path(os.environ['CREDENTIALS_DIRECTORY'])
        user='familytopics-discord' if kind=='topics' else 'familyap-discord' if kind=='apps' else 'flpolicy-dad'
        args=['/usr/bin/ssh','-F','/dev/null','-i',str(root/'transport'),'-o','IdentityAgent=none','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(root/'hosts'),'-o','GlobalKnownHostsFile=/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-T',user+'@'+self.config['learner_host']]
        proc=await asyncio.create_subprocess_exec(*args,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL,limit=65537)
        try:
            raw,_=await asyncio.wait_for(proc.communicate((json.dumps(operation)+'\n').encode()),45)
        except BaseException:
            if proc.returncode is None:proc.kill();await proc.wait()
            raise
        if len(raw)>65536 or proc.returncode:raise ValueError('Scoped connection unavailable')
        value=json.loads(raw)
        if value.get('ok') is not True:raise ValueError('Source request unavailable')
        return value.get('result',value)

    async def source_requests(self,kind):
        if kind=='topics':return (await self.rpc(kind,{'op':'topic-pending'})).get('requests',[])
        if kind=='apps':
            value=(await self.rpc(kind,{'op':'poll'})).get('request',{})
            return [value] if value.get('software') else []
        return (await self.rpc(kind,{'op':'break-pending'})).get('help_requests' if kind=='help' else 'requests',[])

    async def watch(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for kind in ['apps','breaks','help','topics']:
                try:
                    requests=await self.source_requests(kind)
                    for request in requests:
                        identifier=request['id'];created=request['time'] if kind=='apps' else request['created']
                        seen=None
                        try:
                            heartbeat=json.loads(Path('/var/lib/family-discord-heartbeat/parent.json').read_text())
                            value=heartbeat.get('seen')
                            if type(value) in (int,float) and math.isfinite(value) and value<=time.time():seen=value
                        except (OSError,ValueError,TypeError):pass
                        if not due(created,time.time(),seen):continue
                        if self.pending.load(kind,identifier):continue
                        if kind=='apps':
                            if (await self.rpc(kind,{'op':'status','id':identifier}))['status']!='pending':continue
                            review=await self.rpc(kind,{'op':'prepare','request':request})
                            if review.get('already_decided'):continue
                            plan=review['plan'];body=plan.get('title','App request')+'\n'+ '\n'.join(plan.get('transaction',[]))
                            supported=plan.get('supported') is True and len(body)<=3500
                            payload={'request':request,'digest':review['digest'],'supported':supported,'created':created}
                        elif kind=='topics':
                            body='Learning topic: '+request['topic']+'\nApproval records a reviewed idea only. No AI request, course generation or assignment is started.'
                            payload={'request':request,'supported':True,'created':created}
                        elif kind=='breaks':
                            body=f"Break request: {request['change']} ({request['minutes']} minutes)."
                            payload={'request':request,'supported':True,'created':created}
                        else:
                            body='Bedtime or screen-time help requested. Open Family Lab Manager on a parent desktop to review. Acknowledging this card grants no extra time and does not change bedtime.'
                            payload={'request':request,'supported':False,'created':created}
                        if not self.pending.claim(kind,identifier,payload):continue
                        view=discord.ui.View(timeout=None)
                        if kind=='help':view.add_item(discord.ui.Button(label='Mark seen — no time granted',style=discord.ButtonStyle.secondary,custom_id=f'fl:{kind}:{identifier}:ack'))
                        else:
                            if payload['supported']:view.add_item(discord.ui.Button(label='Approve',style=discord.ButtonStyle.success,custom_id=f'fl:{kind}:{identifier}:approve'))
                            view.add_item(discord.ui.Button(label='Deny',style=discord.ButtonStyle.danger,custom_id=f'fl:{kind}:{identifier}:deny'))
                            if kind=='topics':view.add_item(discord.ui.Button(label='Change topic',style=discord.ButtonStyle.secondary,custom_id=f'fl:{kind}:{identifier}:edit'))
                        offline=seen is not None and time.time()-seen>60
                        embed=discord.Embed(title='Ask Dad — desktop unavailable' if offline else 'Ask Dad — unanswered for three minutes',description=body[:3500],color=0x80c7a3)
                        if kind!='help' and not payload['supported']:embed.add_field(name='Technical review required',value='This request cannot be approved through Discord.')
                        channel=await self.fetch_channel(int(self.config['channel_id']))
                        # Mention only the explicitly configured Dad identity, never roles/everyone.
                        message=await channel.send(content='<@'+self.config['parents']['dad']+'>',embed=embed,view=view,allowed_mentions=discord.AllowedMentions(users=[discord.Object(id=int(self.config['parents']['dad']))]))
                        self.pending.sent(kind,identifier,message.id)
                except (OSError,ValueError,KeyError,discord.DiscordException,asyncio.TimeoutError):
                    pass  # No raw request, credential or server error body enters logs.
            await asyncio.sleep(15)

    async def on_interaction(self,interaction):
        custom=(interaction.data or {}).get('custom_id','')
        if not custom.startswith('fl:'):return
        if not authorized(self.config,interaction.guild_id,interaction.channel_id,interaction.user.id):
            await interaction.response.send_message('Only enrolled parents may decide in the approvals channel.',ephemeral=True);return
        parts=custom.split(':')
        if len(parts)!=4 or parts[1] not in ['apps','breaks','help','topics'] or parts[3] not in ['approve','deny','ack','edit']:return
        _,kind,identifier,choice=parts
        if kind=='topics' and choice=='edit':
            row=self.pending.load(kind,identifier)
            if not row or row[1]!='sent' or time.time()-row[0]['created']>=900:
                await interaction.response.send_message('This topic request is unavailable or expired.',ephemeral=True);return
            bot=self
            class Edit(discord.ui.Modal,title='Review learning topic'):
                revised=discord.ui.TextInput(label='Topic to approve',default=row[0]['request']['topic'],min_length=3,max_length=160)
                async def on_submit(self,event):await bot.handle_decision(event,kind,identifier,'approve',str(self.revised))
            await interaction.response.send_modal(Edit());return
        if choice=='edit':return
        await self.handle_decision(interaction,kind,identifier,choice)

    async def handle_decision(self,interaction,kind,identifier,choice,replacement=None):
        if not authorized(self.config,interaction.guild_id,interaction.channel_id,interaction.user.id):return
        row=self.pending.load(kind,identifier)
        if not row or row[1]!='sent' or (interaction.message is not None and str(interaction.message.id)!=row[2]):
            await interaction.response.send_message('This request is unavailable or already handled.',ephemeral=True);return
        payload=row[0]
        if kind=='help':
            if choice!='ack':return
            self.pending.finish(kind,identifier,'acknowledged')
            await interaction.response.edit_message(content='Parent has seen this help request. No extra time or bedtime change was granted.',view=None)
            return
        if choice=='ack':return
        if time.time()-payload['created']>=900 or (choice=='approve' and not payload['supported']):
            await interaction.response.send_message('Request expired or requires technical review.',ephemeral=True);return
        self.pending.finish(kind,identifier,'deciding')
        await interaction.response.defer(ephemeral=True)
        try:
            if kind=='apps':
                status=await self.rpc(kind,{'op':'status','id':identifier})
                if status['status']!='pending':raise ValueError('Already handled')
                review=await self.rpc(kind,{'op':'prepare','request':payload['request']})
                if review.get('already_decided') or review['digest']!=payload['digest']:raise ValueError('Plan changed')
                result=await self.rpc(kind,{'op':'decide','id':identifier,'review':review['review'],'digest':review['digest'],'decision':choice})
            elif kind=='topics':
                parent=next(key for key,value in self.config['parents'].items() if str(value)==str(interaction.user.id))
                result=await self.rpc(kind,{'op':'topic-decision','id':identifier,'decision':choice,'expected_topic':payload['request']['topic'],'replacement':replacement,'parent':parent})
            else:
                current=next((r for r in await self.source_requests(kind) if r['id']==identifier),None)
                if current is None:raise ValueError('Request changed')
                result=await self.rpc(kind,{'op':'break-decision','id':identifier,'decision':choice})
            self.pending.finish(kind,identifier,'handled')
            print('Decision confirmed:',kind,identifier,choice,'parent',interaction.user.id,flush=True)
            message=interaction.message or await (await self.fetch_channel(int(self.config['channel_id']))).fetch_message(int(row[2]))
            await message.edit(content=f"Parent decision: {choice}. Source confirmed: {result.get('status','accepted')}.",view=None)
            await interaction.followup.send('Decision confirmed by the source service.',ephemeral=True)
        except (ValueError,OSError,KeyError,discord.DiscordException,asyncio.TimeoutError):
            self.pending.finish(kind,identifier,'unconfirmed')
            await interaction.followup.send('Decision could not be confirmed. Check the desktop or send a new request; do not assume it was applied.',ephemeral=True)

    async def on_ready(self):
        if str(self.user.id) != str(self.config['application_id']):
            await self.close()
            raise RuntimeError('Unexpected bot identity')
        channel = await self.fetch_channel(int(self.config['channel_id']))
        if str(channel.guild.id) != str(self.config['guild_id']):
            await self.close()
            raise RuntimeError('Unexpected channel server')
        print('READY: expected bot and private channel verified; real approvals '+('enabled' if self.config.get('enabled') else 'disabled')+'.', flush=True)


if __name__ == '__main__':
    root = Path(os.environ['CREDENTIALS_DIRECTORY'])
    config = json.loads((root/'config').read_text())
    Bot(config).run((root/'token').read_text().strip(), log_handler=None)
