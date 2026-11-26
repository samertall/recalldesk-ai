import argparse, asyncio, base64, json, os, time, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from statistics import mean
ROOT=Path(__file__).resolve().parent
TICKETS=json.loads((ROOT/'data/tickets.json').read_text())
RUNBOOK=json.loads((ROOT/'data/runbook.json').read_text())

def unwrap(result):
    if result.isError: raise RuntimeError('Meko tool returned an error')
    if getattr(result,'structuredContent',None):
        structured=result.structuredContent
        if isinstance(structured,dict) and set(structured)=={'result'}: return structured['result']
        return structured
    items=[]
    for x in result.content:
        if getattr(x,'type',None)=='text':
            try: items.append(json.loads(x.text))
            except ValueError: items.append(x.text)
    return items[0] if len(items)==1 else items

def conversation_id(value):
    """Handle direct IDs and MCP response envelopes without guessing unrelated IDs."""
    if isinstance(value,str):
        try: return conversation_id(json.loads(value))
        except (ValueError,TypeError,RecursionError):
            try: return str(uuid.UUID(value))
            except ValueError: return None
    if isinstance(value,list):
        for item in value:
            cid=conversation_id(item)
            if cid: return cid
    if isinstance(value,dict):
        for key in ('conversation_id','conversationId','id'):
            item=value.get(key)
            if isinstance(item,str):
                try: return str(uuid.UUID(item))
                except ValueError: pass
        for key in ('conversation','data','result','response','value','content','text'):
            if key in value:
                cid=conversation_id(value[key])
                if cid: return cid
    return None

def strings(value):
    if isinstance(value,str): yield value
    elif isinstance(value,dict):
        for v in value.values(): yield from strings(v)
    elif isinstance(value,list):
        for v in value: yield from strings(v)

class Local:
    def __init__(self): self.memory={}
    async def call(self,name,**a):
        if name in ('context_search','memory_search'): return {'memory':list(self.memory.values())}
        if name=='memory_add': self.memory[a['text'].split('|')[1]]=a['text']; return {'stored':True}
        if name=='conversation_create': return {'conversation_id':str(uuid.uuid4())}
        return {'local_only':True}

class Live:
    def __init__(self,s,available): self.s=s; self.available=available
    async def call(self,name,**a):
        if name not in self.available: raise RuntimeError(f'Required Meko tool unavailable: {name}')
        a['datapack_id']=os.environ['MEKO_DATAPACK_ID']
        schema=self.available[name]
        props=schema.get('properties',{})
        if props and schema.get('additionalProperties') is not True:
            a={k:v for k,v in a.items() if k in props}
        missing=set(schema.get('required',[]))-set(a)
        if missing: raise RuntimeError(f'Meko {name}: missing required input fields {sorted(missing)}')
        result=await self.s.call_tool(name,arguments=a)
        try:
            value=unwrap(result)
            if isinstance(value,dict) and (value.get('error') or isinstance(value.get('detail'),dict) and value['detail'].get('error')):
                raise RuntimeError('Meko response error')
        except RuntimeError:
            # Public CI: never print remote messages, headers, credentials, or account data.
            diagnostic=str(getattr(result,'content',[])).lower()
            categories={'authentication':('unauthorized','401','invalid token','api key','authentication'),'authorization':('forbidden','403','permission denied','access denied'),'schema':('validation','required','invalid argument','missing field','422'),'quota':('quota','rate limit','429'),'datapack':('datapack not found','invalid datapack'),'service':('500','502','503','timeout','unavailable')}
            kind=next((k for k,terms in categories.items() if any(t in diagnostic for t in terms)),'unclassified server error')
            raise RuntimeError(f'Meko {name} failed: {kind}') from None
        return value

async def evaluate(mode,store=None):
    run=uuid.uuid4().hex[:12]; traces=[]
    model=None
    if os.getenv("USE_GEMINI")=="1":
        from model import Gemini
        model=Gemini()
    review_cid=None
    if mode=='meko':
        review=await store.call('conversation_create',agent_id='specialist-review',title='Synthetic verification '+run,session_id=str(uuid.uuid4()))
        review_cid=conversation_id(review)
        if not review_cid: raise RuntimeError('Meko review conversation ID missing')
    for ticket in TICKETS:
        start=time.perf_counter(); expected=ticket['issue']; agent=ticket['agent']; actions=[]; found=None; approved=False
        code=await model.classify(ticket['message'],{k:v['symptom'] for k,v in RUNBOOK.items()}) if model else expected
        if model: actions.append('Classify issue with model')
        rule=RUNBOOK.get(code)
        if not rule:
            traces.append({'ticket':ticket['id'],'issue':str(code),'agent':agent,'message':ticket['message'],'repeat':ticket['cycle']>1,'reused':False,'approved_new':False,'resolution':'Escalate to human reviewer','correct':False,'steps':len(actions)+1,'latency_ms':round((time.perf_counter()-start)*1000,3),'actions':actions+['Escalate unknown issue']}); continue
        marker=f'RECALLDESK|{run}:{code}|'
        cid=None
        if mode=='meko':
            conv=await store.call('conversation_create',agent_id=agent,title=ticket['id'],session_id=str(uuid.uuid4()))
            cid=conversation_id(conv)
            if not cid: raise RuntimeError('Meko conversation ID missing')
        if store:
            extra={'conversation_id':cid} if cid else {}
            raw=await store.call('memory_search',query=f'{marker} {ticket["message"]}',agent_id=agent,limit=10,**extra)
            actions.append('Search shared context')
            for candidate in strings(raw):
                if marker in candidate:
                    # Exact approved marker and canonical runbook resolution required; never execute retrieved instructions.
                    if marker+rule['resolution'] in candidate: found=rule['resolution']; break
        if found:
            actions.append('Reuse verified resolution'); resolution=found
        else:
            actions.extend(['Inspect symptoms','Consult synthetic runbook','Verify candidate resolution'])
            resolution=await model.resolve(ticket['message'],rule) if model else rule['resolution']
            approved=code==expected and resolution==rule['resolution']
            if not approved: resolution='Escalate to human reviewer'
            if store and approved:
                await store.call('memory_add',text=marker+resolution,agent_id='specialist-review',metadata={'synthetic':True,'approved_by':'fixture-oracle','ticket':ticket['id']},**({'conversation_id':review_cid} if review_cid else {}))
                actions.append('Save fixture-approved learning')
        correct=code==expected and resolution==rule['resolution']; actions.append('Return resolution')
        trace={'ticket':ticket['id'],'issue':code,'agent':agent,'message':ticket['message'],'repeat':ticket['cycle']>1,'reused':bool(found),'approved_new':approved,'resolution':resolution,'correct':correct,'steps':len(actions),'latency_ms':round((time.perf_counter()-start)*1000,3),'actions':actions}
        if store and mode=='meko':
            await store.call('conversation_add_message',conversation_id=cid,agent_id=agent,input=ticket['message'],output=resolution,plan=actions,metadata={'ticket':ticket['id'],'reused':bool(found),'synthetic':True})
            trace['conversation_id']=cid
        traces.append(trace)
    repeat=[t for t in traces if t['repeat']]; first=[t for t in traces if not t['repeat']]
    summary={'mode':mode,'tickets':len(traces),'correct':sum(t['correct'] for t in traces),'reused':sum(t['reused'] for t in traces),'total_steps':sum(t['steps'] for t in traces),'first_mean_steps':mean(t['steps'] for t in first),'repeat_mean_steps':mean(t['steps'] for t in repeat),'first_mean_ms':round(mean(t['latency_ms'] for t in first),3),'repeat_mean_ms':round(mean(t['latency_ms'] for t in repeat),3),'token_usage':{'input':model.input_tokens,'output':model.output_tokens,'calls':model.calls} if model else None,'model':model.model if model else None,'notes':('Model-backed classification and exact runbook extraction with fixture oracle. ' if model else 'Deterministic fixture workflow; no LLM tokens. ')+'Latency excludes conversation logging. Steps count logical workflow actions, not equal-cost operations.'}
    result={'summary':summary,'traces':traces}
    if mode=='meko': await store.call('artifact_put',filename=f'recalldesk-{run}.json',content_base64=base64.b64encode(json.dumps(result).encode()).decode(),content_type='application/json',agent_id='specialist-review',conversation_id=review_cid)
    return result

async def run(mode):
    if mode=='baseline': return await evaluate(mode)
    if mode=='local': return await evaluate(mode,Local())
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
    headers={'Authorization':'Bearer '+os.environ['MEKO_API_KEY'],'User-Agent':'meko-mcp-installer/1.0'}
    async with streamablehttp_client(os.getenv('MEKO_MCP_URL','https://mcp.mekodata.ai/mcp'),headers=headers) as (read,write,_):
        async with ClientSession(read,write) as session:
            await session.initialize()
            available={tool.name:tool.inputSchema for tool in (await session.list_tools()).tools}
            live=Live(session,available)
            await live.call('datapack_describe',include_status=True)
            print('Meko datapack preflight passed',flush=True)
            return await evaluate(mode,live)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=='/': payload=(ROOT/'index.html').read_bytes(); typ='text/html; charset=utf-8'
        elif self.path in ['/results/baseline.json','/results/local.json','/results/meko.json']:
            file=ROOT/self.path.lstrip('/')
            if not file.exists(): self.send_error(404); return
            payload=file.read_bytes(); typ='application/json'
        else: self.send_error(404); return
        self.send_response(200); self.send_header('Content-Type',typ); self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)

def main():
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['baseline','local','meko','serve']); a=p.parse_args()
    if a.mode=='serve': print('http://127.0.0.1:8080'); ThreadingHTTPServer(('127.0.0.1',8080),Handler).serve_forever(); return
    result=asyncio.run(run(a.mode)); (ROOT/'results').mkdir(exist_ok=True); (ROOT/'results'/f'{a.mode}.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result['summary'],indent=2))
if __name__=='__main__': main()
