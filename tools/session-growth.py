#!/usr/bin/env python3
"""How did your biggest Claude Code sessions grow?

Ranks the transcripts in ~/.claude/projects by cache-read volume over the last N days, then for the
top K: context milestones, share of tokens read above 200k, what entered the context per tool, and a
what-if simulation of a context ceiling with handoffs. Token sizes of content are chars/4 estimates;
request totals come from the API usage recorded in the transcript.

usage: session-growth.py [--days 7] [--top 6]
"""
import argparse,json,os,glob,collections,time
ap=argparse.ArgumentParser();ap.add_argument('--days',type=int,default=7);ap.add_argument('--top',type=int,default=6);A=ap.parse_args()
P=os.path.expanduser('~/.claude/projects/')
cut=time.time()-A.days*86400
CUT_ISO=time.strftime('%Y-%m-%dT%H:%M:%S',time.gmtime(cut))
def _read(t):
    seen=set();cr=0
    for l in open(t):
        if '"assistant"' not in l:continue
        try:e=json.loads(l)
        except:continue
        m=e.get('message') or {}
        if e.get('type')!='assistant' or m.get('id') in seen or e.get('timestamp','')<CUT_ISO:continue
        seen.add(m.get('id'));cr+=(m.get('usage') or {}).get('cache_read_input_tokens',0)
    return cr
ranked=sorted(((_read(t),t) for t in glob.glob(P+'*/*.jsonl') if os.path.getmtime(t)>cut),reverse=True)
total=sum(r for r,_ in ranked) or 1
print(f'{len(ranked)} sessions touched in the last {A.days} days, {total/1e6:.0f}M cache-read tokens; top {A.top} = {sum(r for r,_ in ranked[:A.top])/total:.0%}')
FILES=[t for _,t in ranked[:A.top]]
print('(per-session figures below cover each session\'s whole life, not only the window)')
def size(c):
    if isinstance(c,str):return len(c)
    if isinstance(c,list):return sum(size(x.get('text') or x.get('content') or '') if isinstance(x,dict) else len(str(x)) for x in c)
    return len(str(c))
ALL=collections.Counter()
for idx,f in enumerate(FILES):
    s='session '+chr(65+idx)
    seen=set();ctx=[];names={};bytool=collections.Counter();cnt=collections.Counter();bigs=[];compacts=0;first=last=None;usertext=0;asst=0
    for l in open(f):
        try:e=json.loads(l)
        except:continue
        ty=e.get('type');ts=e.get('timestamp')
        if ts:first=first or ts;last=ts
        if e.get('subtype')=='compact_boundary' or e.get('isCompactSummary'):compacts+=1
        m=e.get('message') or {}
        c=m.get('content')
        if ty=='assistant':
            if isinstance(c,list):
                for b in c:
                    if b.get('type')=='tool_use':
                        n=b['name'];names[b['id']]=n;asst+=len(json.dumps(b.get('input',{})))
                    elif b.get('type') in('text','thinking'):asst+=len(b.get('text') or b.get('thinking') or '')
            if m.get('id') in seen:continue
            seen.add(m.get('id'));u=m.get('usage',{})
            ctx.append(u.get('cache_read_input_tokens',0)+u.get('cache_creation_input_tokens',0)+u.get('input_tokens',0))
        elif ty=='user':
            if isinstance(c,list):
                for b in c:
                    if isinstance(b,dict) and b.get('type')=='tool_result':
                        n=names.get(b.get('tool_use_id'),'?');z=size(b.get('content'))
                        n='mcp:'+n.split('__')[1] if n.startswith('mcp__') else n
                        bytool[n]+=z;cnt[n]+=1;bigs.append((z,n))
                    elif isinstance(b,dict) and b.get('type')=='text':usertext+=len(b.get('text',''))
            elif isinstance(c,str):usertext+=len(c)
    tot=sum(bytool.values());read=sum(ctx)
    print(f'\n##### {s}  {first[:10]}→{last[:10]}  reqs={len(ctx)}  peak={max(ctx)/1e3:.0f}k  compactions={compacts}  read={read/1e6:.0f}M')
    # growth milestones
    marks=[];
    for th in (100,200,400,600,800):
        i=next((k for k,v in enumerate(ctx) if v>=th*1000),None)
        marks.append(f'{th}k@req{i}' if i is not None else f'{th}k:-')
    print('  milestones:',' '.join(marks))
    above=sum(v for v in ctx if v>200_000);print(f'  read with ctx>200k: {above/read:.0%} of tokens, in {sum(1 for v in ctx if v>200_000)/len(ctx):.0%} of requests')
    print(f'  what entered the context (chars/4): tool_results={tot/4e3:.0f}k  assistant={asst/4e3:.0f}k  user={usertext/4e3:.0f}k')
    for n,z in bytool.most_common(5):print(f'    {n:<22}{z/4e3:>7.0f}k tok {z/tot:>4.0%}  {cnt[n]:>4} calls  avg {z/cnt[n]/4:>6.0f} tok')
    bigs.sort(reverse=True);print('  5 largest results:',', '.join(f'{n} {z/4e3:.0f}k' for z,n in bigs[:5]))
    ALL.update(bytool)
    # handoff what-if: same per-request delta, restart at 40k when the ceiling is hit
    for cap in (150_000,300_000):
        sim=0;cur=ctx[0];n=0
        for a,b in zip(ctx,ctx[1:]):
            sim+=cur;d=max(b-a,0);cur+=d
            if cur>=cap:cur=40_000;n+=1
        print(f'  ceiling {cap//1000}k: would read {sim/1e6:.0f}M ({1-sim/read:.0%} less) with {n} handoffs')
T=sum(ALL.values());print('\n##### TOTAL by tool');[print(f'  {n:<22}{z/4e3:>7.0f}k tok {z/T:>4.0%}') for n,z in ALL.most_common(8)]
