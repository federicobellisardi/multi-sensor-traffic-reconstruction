#!/usr/bin/env python3
"""Save authoritative Crossref metadata and BibTeX for the selected bibliography.

An API failure is recorded and never replaced by invented metadata. The original
bibliography is untouched. Run before compiling article1/main.tex.
"""
import json
from pathlib import Path
import urllib.request
import urllib.parse
import time

HERE = Path(__file__).resolve().parents[1]
DOIS = {
    'toole2015': '10.1016/j.trc.2015.04.022',
    'colak2016': '10.1038/ncomms10793',
    'cascetta1984': '10.1016/0191-2615(84)90012-2',
    'work2010': '10.1093/amrx/abq002',
    'seo2017': '10.1016/j.arcontrol.2017.03.005',
    'herrera2010': '10.1016/j.trc.2009.10.006',
    'boeing2017': '10.1016/j.compenvurbsys.2017.05.004',
    'dijkstra1959': '10.1007/BF01386390',
    'horni2016': '10.5334/baw',
    'lopez2018': '10.1109/ITSC.2018.8569938',
    'treiber2013': '10.1007/978-3-642-32460-4',
    'ward1963': '10.1080/01621459.1963.10500845',
    'murtagh2014': '10.1007/s00357-014-9161-z',
    'castillo2015': '10.1155/2015/903563',
    'lei2024': '10.1016/j.trc.2024.104798',
    'maiti2025': '10.1016/j.trc.2025.105213',
    'lin2024': '10.1145/3589335.3651442',
    # Added 2026-10-27: broader positioning, each checked against Crossref.
    'gonzalez2008': '10.1038/nature06958',
    'calabrese2011': '10.1109/MPRV.2011.41',
    'iqbal2014': '10.1016/j.trc.2014.01.002',
    'alexander2015': '10.1016/j.trc.2015.02.018',
    'wang2012': '10.1038/srep01001',
    'wesolowski2013': '10.1098/rsif.2012.0986',
    'chen2016': '10.1016/j.trc.2016.04.005',
    'anda2017': '10.1080/12265934.2017.1281150',
    'zheng2014': '10.1145/2629592',
    'bazzani2010': '10.1088/1742-5468/2010/05/P05001',
    'gallotti2016': '10.1038/ncomms12600',
    'mizzi2018': '10.1140/epjds/s13688-018-0168-2',
    'mizzi2022': '10.1088/1742-5468/ac4c40',
    'mizzi2023': '10.1140/epjds/s13688-023-00431-4',
    'wardrop1952': '10.1680/ipeds.1952.11259',
    'yang1992': '10.1016/0191-2615(92)90008-k',
    'antoniou2016': '10.1016/j.trc.2015.08.009',
    'flotterod2011': '10.1287/trsc.1100.0367',
    'patire2015': '10.1016/j.trc.2015.02.011',
    'jenelius2013': '10.1016/j.trb.2013.03.008',
    'seo2015': '10.1016/j.trc.2015.05.019',
    'wang2005': '10.1016/j.trb.2004.03.003',
    'elfaouzi2011': '10.1016/j.inffus.2010.06.001',
    'bachmann2013': '10.1016/j.trc.2012.07.003',
    'nantes2016': '10.1016/j.trc.2015.07.005',
    'yang1998': '10.1016/S0191-2615(97)00016-7',
    'castillo2008': '10.1111/j.1467-8667.2008.00531.x',
    'gentili2012': '10.1016/j.trc.2012.01.004',
    'zhao2002': '10.1007/s001680200072',
    'rasouli2012': '10.3328/TL.2012.04.01.55-73',
    'toledo2004': '10.3141/1876-15',
    'hollander2008': '10.1007/s11116-007-9156-2',
    'lippi2013': '10.1109/TITS.2013.2247040',
    'vlahogianni2014': '10.1016/j.trc.2014.01.005',
    'barrington2017': '10.1371/journal.pone.0180698',
    'pepe2020': '10.1038/s41597-020-00575-2',
    'bonaccorsi2020': '10.1073/pnas.2007658117',
}


def get(key_doi):
    key, doi = key_doi
    url = 'https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Article1LocalBibliographyAudit/1.0'})
        with urllib.request.urlopen(req, timeout=35) as response:
            message = json.load(response)['message']
        return key, {'doi': doi, 'status': 'verified', 'crossref': message}, render(key, message)
    except Exception as exc:
        return key, {'doi': doi, 'status': 'failed', 'error': str(exc)}, ''


def render(key, message):
    def esc(value):
        # Crossref metadata is plain text; escape TeX-special characters.
        return str(value).replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')
    kind = 'book' if message.get('type') in ['book','edited-book','monograph'] else (
        'inproceedings' if message.get('type') == 'proceedings-article' else 'article')
    fields = {'title': '{'+esc(message['title'][0])+'}', 'doi': message['DOI']}
    for role in ['author','editor']:
        names = message.get(role, [])
        if names:
            fields[role] = ' and '.join(esc(n.get('family',n.get('name',''))) +
                                       (', '+esc(n['given']) if n.get('given') else '') for n in names)
    fields['year'] = str(message.get('published',message.get('issued'))['date-parts'][0][0])
    if kind != 'book' and message.get('container-title'):
        fields['booktitle' if kind == 'inproceedings' else 'journal'] = esc(message['container-title'][0])
    for api, bib in [('volume','volume'),('issue','number'),('page','pages'),('publisher','publisher')]:
        if message.get(api):
            fields[bib] = esc(message[api])
    if not message.get('page') and message.get('article-number'):
        fields['pages'] = esc(message['article-number'])
    return '@'+kind+'{'+key+',\n'+',\n'.join('  '+k+' = {'+v+'}' for k,v in fields.items())+'\n}'


if __name__ == '__main__':
    cached_path = HERE/'reports/reference_metadata.json'
    cached = json.loads(cached_path.read_text()) if cached_path.exists() else {}
    results = []
    for key, doi in DOIS.items():
        if cached.get(key, {}).get('status') == 'verified':
            results.append((key, cached[key], render(key,cached[key]['crossref'])))
            continue
        for attempt in range(3):
            time.sleep(2*(attempt+1))
            result = get((key,doi))
            if result[1]['status'] == 'verified':
                break
        results.append(result)
    report = {key: meta for key, meta, _ in results}
    (HERE/'reports/reference_metadata.json').write_text(json.dumps(report, indent=2)+'\n')
    if any(meta['status'] != 'verified' for _, meta, _ in results):
        print({k: m for k, m, _ in results if m['status'] != 'verified'})
        raise SystemExit('Verification incomplete; bibliography was not replaced.')
    osm = ('@misc{osm, author={{OpenStreetMap contributors}}, '
           'title={{OpenStreetMap}}, url={https://www.openstreetmap.org/}, '
           'note={Road-network source; accessed 27 October 2026}}')
    # DataCite DOI (not in Crossref); metadata checked via doi.org content negotiation, 2026-10-27.
    thesis = ('@phdthesis{bellisardi2025, author={Bellisardi, Federico}, '
              'title={Data analytics and predictive models for sustainable multimodal mobility in future smart cities}, '
              'school={Alma Mater Studiorum Universit{\\`a} di Bologna}, year={2025}, '
              'doi={10.48676/unibo/amsdottorato/12316}}')
    (HERE/'references.bib').write_text('\n\n'.join(bib for _, _, bib in results)+'\n\n'+osm+'\n\n'+thesis+'\n')
    for key, meta, _ in results:
        print(key, meta['crossref'].get('title'))
