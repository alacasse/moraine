from pathlib import Path
import hashlib,json,re,subprocess
from urllib.parse import unquote,urlsplit
root=Path('/home/alacasse/projects/moraine');out=root/'pilot-results/parallel-workstreams/integration-20260920'
def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
inv=json.loads((out/'import-inventory.json').read_text())
lines=[]
for x in inv['files']:
    p=root/x['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path']
    assert ('100755' if p.stat().st_mode&0o111 else '100644')==x['mode'],x['path']
lines.append('PASS all 46 imported file contents and Git modes still match source commits; historical A/B/C evidence untouched')
allowed={'README.md','docs/plans/codex-mcp-email-pilot.md','pilots/codex_email/README.md','pilots/codex_email/INTERFACE.md',*(x['path'] for x in inv['files'])}
checked=0
for line in git('ls-tree','-r',inv['base']).splitlines():
    fields,path=line.split('\t',1);mode,kind,blob=fields.split()
    if path in allowed:continue
    p=root/path;data=p.read_bytes()
    actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert actual==blob,path
    assert ('100755' if p.stat().st_mode&0o111 else '100644')==mode,path
    checked+=1
lines.append(f'PASS {checked} pre-existing files outside allowed changes match base bytes/modes, including historical experiments, evidence and dependency locks')
assert git('rev-parse','HEAD')==inv['coordination_commit']
assert git('diff','--name-only','--diff-filter=U')==''
for lot,source in inv['source_commits'].items():
    assert git('rev-parse',source['branch'])==source['commit']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=source['worktree'],text=True)
    assert git('rev-parse',source['commit']+'^')==inv['base']
    assert git('log','-1','--format=%B',source['commit']).count('Co-authored-by: Codex <codex@openai.com>')==1
assert git('rev-parse',inv['coordination_commit']+'^')==inv['base']
assert git('log','-1','--format=%B',inv['coordination_commit']).count('Co-authored-by: Codex <codex@openai.com>')==1
lines.append('PASS 4 commits have original parent and one Codex trailer; source branches/worktrees preserved and clean; target HEAD remains coordination commit; no unresolved conflict')
for args in [('diff','HEAD','--check'),('diff','--cached','--check')]:
    proc=subprocess.run(['git',*args],cwd=root,text=True,capture_output=True);assert proc.returncode==0,proc.stdout
lines.append('PASS git diff HEAD --check and git diff --cached --check')
paths=set(git('diff','HEAD','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
paths|={'docs/prompts/integrate-parallel-workstreams.md','pilot-results/parallel-workstreams/dispatch.json'}
links=0;formatting=[]
for name in sorted(paths):
    p=root/name
    if not p.is_file():continue
    text=p.read_text()
    for n,line in enumerate(text.splitlines(),1):
        if line!=line.rstrip():
            if p.suffix=='.log':formatting.append(f'{name}:{n} (verbatim command output)')
            else:raise AssertionError(f'trailing whitespace {name}:{n}')
    if p.suffix!='.md':continue
    for dest in re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)',text):
        dest=dest.strip('<>');parsed=urlsplit(dest)
        if parsed.scheme or not parsed.path:continue
        target=p.parent/unquote(parsed.path)
        assert target.exists(),f'{name}: {dest}'
        links+=1
lines.append(f'PASS {links} local Markdown link destinations exist (fragment anchors not checked); checked imported and new untracked files')
lines.append('PASS source/docs/JSON whitespace; raw log formatting retained: '+('; '.join(formatting) or 'none'))
(out/'integrity-checks.log').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
