"""Publica o vídeo v2 (explicavideos) de uma das produções da trilogia em inematds/<id>.
Release video-v2.0.0 (MP4 + SRT) + Pages: videos/index.html com player, capítulos e legendas VTT.
Uso: python3 publica.py <id>   (gestor-de-agentes | gerente-de-agentes | consultor-ia-2027)
Idempotente: sobe só o que mudou de tamanho; commit só se houver diff. Adaptado de claude-mods-video/scripts/publica.py."""
import html, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

META = {
    'gestor-de-agentes': dict(
        h1='O fim de uma fase da automação: <b>do técnico ao gestor de agentes.</b>',
        title='Do técnico ao gestor de agentes',
        lead='Se o seu cliente consegue usar os mesmos agentes que você, por que ele vai continuar pagando você? '
             'Neste vídeo, o Nei mostra as duas vantagens que estão acabando, o piso que sobe, a troca de "construir" por "decidir" '
             'e por que gestão de pessoas, processos e agentes vira a habilidade central — com um exercício para começar esta semana.'),
    'gerente-de-agentes': dict(
        h1='Gerente que não domina agentes <b>é o novo gerente que não sabe lidar com pessoas.</b>',
        title='Gerente que não domina agentes',
        lead='A gestão ganhou um terceiro objeto: além de pessoas e processos, agentes. Um vídeo provocativo para gerentes, '
             'com o caminho para começar: OSWork, os 7 princípios da gestão de agentes e a área Gestão de IA do eventos INEMA.'),
    'consultor-ia-2027': dict(
        h1='O que aprender para faturar em 2027: <b>de construtor a consultor.</b>',
        title='De construtor a consultor',
        lead='Para profissionais de IA e devs: quando construir vira commodity, o valor está em quatro papéis — consultor, '
             'quem acompanha, mentor e auditor — e em cinco coisas para aprender, nenhuma delas uma ferramenta.'),
    'empresas-2027': dict(
        h1='Anthropic e as empresas de sucesso em 2027: <b>pessoas, processos e agentes.</b>',
        title='Anthropic e as empresas de 2027',
        lead='Em 2025, um engenheiro da OpenAI tinha oito vezes mais chance de ir para a Anthropic do que o contrário. '
             'O vídeo mostra o que a Anthropic faz com as pessoas e com a própria IA — a constituição do Claude — e o que isso '
             'ensina sobre gerir pessoas, processos e agentes em 2027, com a constituição do seu agente e o ciclo que o melhora.',
        curso=('https://inematds.github.io/empresas-2027-v62/', 'Empresas de 2027 v6.2 (curso, 9 aulas)')),
    'consultoria-ia-na-pratica': dict(
        h1='Consultoria de IA na prática: <b>como atuar em 2027 como consultor e mentor.</b>',
        title='Consultoria de IA na prática',
        lead='O seu próximo cliente não vai pedir um agente: vai perguntar por onde começar. O vídeo mostra o que é (e o que não é) '
             'consultoria de IA, os dois chapéus de consultor e mentor, uma consultoria em cinco passos com um exemplo de clínica, '
             'como se preparar a partir de agora e os três erros que derrubam.',
        curso=('https://eventos.inema.pro/consultoria-ia/', 'área Consultoria de IA (cursos, kits e vídeos)')),
    'consultoria-ia-caminhos': dict(
        h1='Consultoria de IA: <b>24 cursos e 10 kits, e como usar no trabalho e no cliente.</b>',
        title='Consultoria de IA: cursos e kits',
        lead='O seu cliente já tem o mesmo agente que você: em 2027 cobra quem sabe o que fazer com ele. O vídeo mostra os três grupos '
             'de cursos da área Consultoria de IA (tornar-se consultor, vender, entregar e auditar), onde aplicar cada um, o que são os '
             'kits abertos e como usá-los no seu negócio, no cliente e dentro da empresa, e termina com o primeiro entregável: '
             'um diagnóstico de uma página.',
        curso=('https://eventos.inema.pro/consultoria-ia/', 'área Consultoria de IA (cursos, kits e vídeos)')),
}

ID = sys.argv[1]
M = META[ID]
OUT = Path.home() / f'projetos/output/{ID}'
REPO = Path.home() / f'projetos/{ID}'
GH = f'inematds/{ID}'
TAG = 'video-v2.0.0'
BASE = f'https://github.com/{GH}/releases/download/{TAG}/'
PAGES = f'https://inematds.github.io/{ID}/'
V2 = OUT / 'v2'


def sh(*a, **kw):
    return subprocess.run(a, check=True, text=True, capture_output=True, **kw).stdout


def dur(p):
    return float(sh('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)))


def main():
    rec = json.loads((V2 / 'verification/assembled-pt.json').read_text())
    full = Path(rec['file'])
    assert full.stat().st_size == rec['bytes'] and (V2 / 'verification/decode-full-pt.log').read_text() == ''
    for b in rec['blocks']:
        assert json.loads((V2 / f'final/{b}/alignment.json').read_text())['ratio'] > .90, b
    scenes = json.loads((V2 / 'docs/lesson-pt.json').read_text())
    assert len(rec['chapters']) == len(scenes)
    v = dict(file=full, srt=full.with_suffix('.srt'), name=f'{ID}-completo-16x9',
             chapters=[(int(c['time']), scenes[c['scene'] - 1]['title']) for c in rec['chapters']])
    gancho = V2 / f'final/{ID}-pt-gancho.json'  # 08/10/2026: versão com abertura de gancho (output/gestor-de-agentes/gancho/)
    if gancho.exists():
        gk = json.loads(gancho.read_text())
        assert Path(gk['file']).stat().st_size == gk['bytes'] and gk['decode_errors'] == '' and len(gk['chapters']) == len(scenes)
        v.update(file=Path(gk['file']), srt=Path(gk['srt']),
                 chapters=[(int(c['time']), scenes[c['scene'] - 1]['title']) for c in gk['chapters']])
    v['duration'] = dur(v['file'])
    d = f"{int(v['duration'] // 60)}min{int(v['duration'] % 60):02d}s"
    stage = OUT / 'release'; stage.mkdir(exist_ok=True)
    assets = []
    for src, ext in ((v['file'], 'mp4'), (v['srt'], 'srt')):
        dst = stage / f"{v['name']}.{ext}"
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            dst.write_bytes(src.read_bytes())
        assets.append(dst)
    if subprocess.run(['gh', 'release', 'view', TAG, '--repo', GH], capture_output=True).returncode:
        notes = stage / 'RELEASE.md'
        notes.write_text(f'{M["title"]} — vídeo com avatar e voz do Nei, animações sincronizadas à fala e legendas.\n\n'
                         f'Assistir: {PAGES}videos/\n\n'
                         'Produção: https://inematds.github.io/explicavideos/guia/ (Explicavideos v2)\n\n'
                         f'- Completo: {d}')
        sh('gh', 'release', 'create', TAG, '--repo', GH, '--draft', '--title', f'{M["title"]} (vídeo v2)', '--notes-file', str(notes))
    have = {a['name']: a['size'] for a in json.loads(sh('gh', 'release', 'view', TAG, '--repo', GH, '--json', 'assets'))['assets']}
    for f in assets:
        if have.get(f.name) != f.stat().st_size:
            print('upload', f.name, flush=True); sh('gh', 'release', 'upload', TAG, str(f), '--repo', GH, '--clobber')
    folder = REPO / 'videos'; folder.mkdir(exist_ok=True)
    (folder / 'completo.vtt').write_text('WEBVTT\n\n' + re.sub(r'(\d\d:\d\d:\d\d),(\d{3})', r'\1.\2', v['srt'].read_text()))
    caps = ''.join(f'<button type="button" data-time="{s}">{s // 60:02d}:{s % 60:02d} · {html.escape(c)}</button>' for s, c in v['chapters'])
    curso = f'Curso do mesmo tema: <a href="{M["curso"][0]}">{html.escape(M["curso"][1])}</a>. ' if 'curso' in M else ''
    page = f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(M["title"])} · INEMA.CLUB</title><meta name="description" content="{html.escape(M["lead"])}">
<style>:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0D1321;color:#F0EBD8;font:18px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:32px 16px}}
a{{color:#FFC300}}h1{{font-size:clamp(1.8rem,5vw,2.8rem);line-height:1.15;margin:.4em 0}}h1 b{{color:#FFC300}}.lead{{color:#b9c3d0;max-width:780px}}
.card{{background:#1D2D44;border:1px solid #3E5C76;border-radius:16px;padding:20px;margin:28px 0}}.card h2{{margin:0 0 4px;font-size:1.3rem}}.card h2 span{{color:#748CAB;font-size:1rem;font-weight:500}}
video{{width:100%;aspect-ratio:16/9;background:#0a0f19;border-radius:12px}}
summary{{cursor:pointer;color:#FFC300;margin-top:8px}}button{{display:block;background:#0D1321;color:#F0EBD8;border:1px solid #3E5C76;border-radius:8px;padding:10px 12px;margin:6px 0;text-align:left;cursor:pointer;width:100%;font:inherit}}
:focus-visible{{outline:3px solid #FFC300;outline-offset:3px}}footer{{color:#748CAB;font-size:15px;margin-top:40px}}</style></head>
<body><main><nav><a href="https://inema.club">INEMA.CLUB</a> · <a href="https://github.com/{GH}">GitHub</a></nav>
<h1>{M["h1"]}</h1>
<p class="lead">{html.escape(M["lead"])}</p>
<section class="card" id="completo"><h2>Completo <span>{d}</span></h2>
<video controls preload="metadata" playsinline><source src="{BASE}{v["name"]}.mp4" type="video/mp4"><track default kind="subtitles" src="completo.vtt" srclang="pt" label="Português"></video>
<p><a href="{BASE}{v["name"]}.mp4">Baixar MP4</a> · <a href="{BASE}{v["name"]}.srt">Baixar legendas</a></p>
<details open><summary>Capítulos</summary>{caps}</details></section>
<footer>Produzido com o <a href="https://inematds.github.io/explicavideos/guia/">Explicavideos v2</a>. {curso}Para começar: <a href="https://inematds.github.io/oswork/">OSWork</a> · <a href="https://inematds.github.io/curso-7pa/">Gestão de Agentes — os 7 princípios</a> · <a href="https://eventos.inema.pro/gestao-ia/">Gestão de IA e Agentes</a>. Conteúdo aberto e gratuito do <a href="https://inema.club">INEMA.CLUB</a>.</footer></main>
<script>document.querySelectorAll('[data-time]').forEach(b=>b.addEventListener('click',()=>{{const v=b.closest('.card').querySelector('video');v.currentTime=Number(b.dataset.time);v.play();}}));</script></body></html>
'''
    (folder / 'index.html').write_text(page)
    (REPO / 'index.html').write_text(f'<!doctype html><meta charset="utf-8"><title>{html.escape(M["title"])}</title><meta http-equiv="refresh" content="0; url=videos/"><a href="videos/">Assistir</a>\n')
    (folder / 'delivery.json').write_text(json.dumps({'completo': {'url': BASE + v['name'] + '.mp4', 'srt': BASE + v['name'] + '.srt', 'duration': round(v['duration'], 2)}}, indent=2) + '\n')
    g = lambda *a: sh('git', '-c', 'user.name=inematds', '-c', 'user.email=inematds@gmail.com', *a, cwd=REPO)
    g('add', '-A')
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=REPO).returncode:
        msg = f'feat: abertura com gancho (thumb + imagem + frase de impacto) em {M["title"]}' if gancho.exists() else f'feat: {M["title"]} em vídeo (v2)'
        g('commit', '-m', f'{msg}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>')
        g('push', '-q', 'origin', 'HEAD:main')
    sh('gh', 'release', 'edit', TAG, '--repo', GH, '--draft=false')
    with urllib.request.urlopen(urllib.request.Request(BASE + v['name'] + '.mp4', method='HEAD'), timeout=60) as r:
        assert r.status == 200
    for _ in range(40):
        try:
            with urllib.request.urlopen(PAGES + 'videos/delivery.json?v=' + str(int(time.time())), timeout=30) as f:
                if 'completo' in f.read().decode():
                    break
        except Exception:
            pass
        time.sleep(30)
    else:
        sys.exit('push e release feitos; Pages ainda não respondeu')
    print('OK', PAGES + 'videos/')


if __name__ == '__main__':
    main()
