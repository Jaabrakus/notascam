"""Make BYOND's same-indent else binding explicit for compact control heads."""
import re


def split_outer_if(body):
    m=re.match(r'if\s*\(',body)
    if not m:return None
    depth=1;quote=None;escaped=False
    for i in range(m.end(),len(body)):
        c=body[i]
        if quote:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c==quote:quote=None
        elif c in ('"',"'"):quote=c
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:
                tail=body[i+1:].lstrip()
                if re.match(r'(if|for|while|switch)\s*\(',tail):return body[:i+1],tail
                return None
    return None


def compact_else_heads(lines):
    heads=set()
    for i,line in enumerate(lines):
        if not re.match(r'else\b',line.lstrip()):continue
        indent=len(line)-len(line.lstrip('\t'))
        for n in range(i-1,-1,-1):
            previous=lines[n]
            if not previous.strip() or previous.lstrip().startswith('//'):continue
            depth=len(previous)-len(previous.lstrip('\t'))
            if depth>indent:continue
            if depth==indent and split_outer_if(previous.lstrip('\t')):heads.add(n+1)
            break
    return heads


def normalize(text):
    lines=text.splitlines();heads=compact_else_heads(lines);scopes=[];out=[]
    for n,line in enumerate(lines,1):
        indent=len(line)-len(line.lstrip('\t'))
        if line.strip():scopes=[d for d in scopes if indent>d]
        extra=len(scopes)
        if n in heads:
            first,tail=split_outer_if(line.lstrip('\t'))
            out.extend(['\t'*(indent+extra)+first,'\t'*(indent+extra+1)+tail])
            scopes.append(indent)
        else:out.append('\t'*extra+line)
    return '\n'.join(out)+'\n'
