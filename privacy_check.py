"""Check Git's actual index, not merely files covered by .gitignore."""
import re
import subprocess

def main():
    names=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
    problems=[]
    for name in filter(None,names):
        if name.split('/')[0] in {'private','state','output'} or name.endswith(('.pdf','.png','.jpg','.log')) or name=='.env':
            problems.append(name+': forbidden private/output path'); continue
        raw=subprocess.check_output(['git','show',':'+name]).decode('utf-8',errors='replace')
        for rule,pattern in [('credential',r'(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9]{25,})'),
                             ('personal-path',r'[A-Z]:[\\/]+Users[\\/]+(?!Public|Example)[^\s\x22]+'),
                             ('private-key',r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----')]:
            if re.search(pattern,raw): problems.append(name+': '+rule)
    if problems: raise SystemExit('\n'.join(problems))
    print('Index privacy gate passed. Also manually inspect all staged content and Git history before publication.')

if __name__=='__main__': main()
