#!/usr/bin/env python3
"""Record package/input provenance and check compiled draft references.

This is a packaging check, not a scientific-readiness certificate.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parents[1]
ROOT=HERE.parent


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def main():
    originals=['sn-jnl.cls','epjds_main_draft.tex','epjds_supplementary_draft.tex','references.bib']
    inputs=[ROOT/'article/tex'/f for f in originals]
    inputs.extend([ROOT/'data/old_coils_data/_coils_table_200201-000000_200331-234500.csv',
                   ROOT/'data/coils_ave_220101-000000_221231-234500.csv',
                   ROOT/'article/results/revision/loo_coils_2020.csv'])
    for name in ['fig1.jpg','fig2.png','fig3.jpg','fig4.jpg','fig5.png','fig6.png',
                 'S_subcluster_profiles.pdf','S_loo_coils.pdf']:
        inputs.append(ROOT/'article/tex/images'/name)
    report={'date':'2026-10-27','input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in inputs},
            'package_sha256':{},'latex':{},'scientific_readiness':'NOT submission-ready'}
    for folder in ['analysis','figures','tables','supplementary']:
        for p in sorted((HERE/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                report['package_sha256'][str(p.relative_to(HERE))]=digest(p)
    for name in ['main.tex','main.pdf','supplementary.pdf','references.bib','sn-jnl.cls']:
        p=HERE/name
        if p.exists(): report['package_sha256'][name]=digest(p)
    for name in ['main','supplementary']:
        log=(HERE/f'{name}.log').read_text()
        unresolved=bool(re.search(r'(?:Reference|Citation).*undefined|There were undefined|multiply defined',log))
        overfull=bool(re.search(r'Overfull \\[hv]box',log))
        report['latex'][name]={'unresolved_references_or_citations':unresolved,'overfull_boxes':overfull}
        if unresolved or overfull:
            raise SystemExit(f'LaTeX check failed for {name}; inspect its log.')
        text=subprocess.check_output(['pdftotext',str(HERE/f'{name}.pdf'),'-'],text=True)
        if '\ufffd' in text:
            raise SystemExit(f'Replacement glyph found in extracted {name} PDF text')
    report['git_revisions']={}
    for name,p in [('parent',ROOT),('article',ROOT/'article'),('minimocas',ROOT/'minimocas')]:
        report['git_revisions'][name]=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()
    status=subprocess.check_output(['git','-C',str(ROOT/'article'),'diff','--name-only'],text=True).splitlines()
    report['original_article_tracked_modifications']=status
    if status:
        raise SystemExit('Tracked changes in original article detected: '+', '.join(status))
    (HERE/'reports/package_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Compiled drafts checked; provenance recorded. Scientific status remains NOT submission-ready.')


if __name__=='__main__':
    main()
