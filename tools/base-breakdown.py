#!/usr/bin/env python3
"""Breaks down a captured Claude Code opening request (see base-breakdown.sh). chars/4 estimates."""
import json,glob,re,sys,collections
bodies=[json.load(open(f)) for f in glob.glob(sys.argv[1]+'/req-*.json')]
if not bodies: sys.exit('no request captured')
b=max(bodies,key=lambda x:len(x.get('tools') or []))
rows=collections.Counter()
sysb=b.get('system');sysb=sysb if isinstance(sysb,list) else [{'text':sysb or ''}]
rows['Claude Code system prompt']=sum(len(x.get('text','')) for x in sysb)
for t in b.get('tools') or []:
    n=t.get('name','');g='MCP '+n.split('__')[1] if n.startswith('mcp__') else 'native tools'
    rows[f'tool schemas: {g}']+=len(json.dumps(t))
SECTION=re.compile(r'(?m)^(SessionStart:\S+ hook \w+:|The following skills are available|Available agent types|The following MCP servers|# Environment|# Language)')
for m in b.get('messages') or []:
    c=m.get('content');text=c if isinstance(c,str) else ''.join(x.get('text','') for x in c if isinstance(x,dict))
    for mm in re.finditer(r'Contents of (\S+?)( \([^)]*\))?:\n([\s\S]*?)(?=\nContents of |</system-reminder>)',text):
        rows['instructions: '+mm.group(1).split('/')[-1]]+=len(mm.group(3))
    if m.get('role')=='system':
        cuts=[(x.start(),x.group(1)) for x in SECTION.finditer(text)]+[(len(text),'')]
        for (a,h),(z,_) in zip(cuts,cuts[1:]): rows['session start: '+h.rstrip(':')]+=z-a
tot=sum(rows.values())
print(f'~{tot/4e3:.1f}k tokens estimated | {len(b.get("tools") or [])} tools | model {b.get("model")}')
for k,z in rows.most_common():
    if z>400: print(f'  {z/4e3:>6.1f}k {z/tot:>4.0%}  {k}')
print('largest tool schemas:',', '.join(f"{t['name']} {len(json.dumps(t))/4e3:.1f}k" for t in sorted(b.get('tools') or [],key=lambda t:-len(json.dumps(t)))[:6]))
