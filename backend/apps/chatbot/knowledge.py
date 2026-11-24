"""
Base de conocimiento: indexación, búsqueda y respuestas.

  index_article(article)            → divide el texto en fragmentos y los indexa (español)
  search(question, kb_ids, limit)   → fragmentos más relevantes (búsqueda de texto completo)
  answer(question, kb_ids, provider, ...) → respuesta redactada por IA SOLO con esos fragmentos
                                     (sin proveedor: devuelve el fragmento más relevante)
  import_file(kb, path, name, user) → crea un artículo a partir de un PDF/Word/Excel/TXT
  sync_glpi(kb)                     → importa la base de conocimiento de GLPI

No usa GPU ni extensiones extra: PostgreSQL ya trae búsqueda de texto completo
con diccionario español (raíces de palabras, sin tildes ni mayúsculas).
"""
import json
import logging
import re
import time
import unicodedata

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import transaction
from django.db.models import F, Value
from django.utils import timezone

logger = logging.getLogger(__name__)

CHUNK_CHARS = 900
FTS_CONFIG = 'spanish'
STOPWORDS = {
    'que', 'como', 'para', 'por', 'con', 'una', 'uno', 'los', 'las', 'del', 'mis', 'mi', 'tengo', 'hola',
    'buenas', 'buenos', 'dias', 'tardes', 'noches', 'quiero', 'necesito', 'puedo', 'favor', 'gracias',
    'esta', 'este', 'esto', 'pero', 'cual', 'cuales', 'donde', 'cuando', 'hay', 'tiene', 'sobre', 'hacer',
}


def _strip_html(text):
    text = re.sub(r'<(br|/p|/li|/h\d)\s*/?>', '\n', text or '', flags=re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    return re.sub(r'[ \t]+', ' ', text)


def split_chunks(title, body):
    """Fragmentos de ~900 caracteres respetando párrafos. Cada uno lleva el título como contexto."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n', body or '') if p.strip()]
    chunks, cur = [], ''
    for p in paragraphs:
        if len(cur) + len(p) + 1 > CHUNK_CHARS and cur:
            chunks.append(cur)
            cur = ''
        while len(p) > CHUNK_CHARS:
            chunks.append(p[:CHUNK_CHARS])
            p = p[CHUNK_CHARS:]
        cur = f'{cur}\n{p}'.strip()
    if cur:
        chunks.append(cur)
    return chunks or [title]


def index_article(article):
    from .models import KnowledgeChunk
    text_title = f'{article.title}. {article.keywords}'.strip()
    with transaction.atomic():
        article.chunks.all().delete()
        KnowledgeChunk.objects.bulk_create([
            KnowledgeChunk(article=article, order=i, text=c) for i, c in enumerate(split_chunks(article.title, article.body))
        ])
        # Título y palabras clave pesan más (A) que el cuerpo (B)
        article.chunks.update(search_vector=(
            SearchVector(Value(text_title), weight='A', config=FTS_CONFIG)
            + SearchVector('text', weight='B', config=FTS_CONFIG)
        ))


def _terms(question):
    norm = unicodedata.normalize('NFD', question or '').encode('ascii', 'ignore').decode().lower()
    words = [w for w in re.findall(r'[a-z0-9]{3,}', norm) if w not in STOPWORDS]
    return list(dict.fromkeys(words))[:12]


def search(question, kb_ids=None, limit=4):
    """[{chunk_id, article_id, title, text, rank}] ordenados por relevancia."""
    from .models import KnowledgeChunk
    terms = _terms(question)
    if not terms:
        return []
    # OR entre palabras (una pregunta suele tener palabras que no están en el artículo)
    query = SearchQuery(' | '.join(terms), search_type='raw', config=FTS_CONFIG)
    qs = KnowledgeChunk.objects.filter(
        search_vector=query, article__is_published=True, article__knowledge_base__is_active=True)
    if kb_ids:
        qs = qs.filter(article__knowledge_base_id__in=kb_ids)
    qs = qs.annotate(rank=SearchRank(F('search_vector'), query, cover_density=False)).select_related(
        'article').order_by('-rank')[:limit * 3]
    out, seen = [], {}
    for c in qs:
        # Máximo 2 fragmentos por artículo para variar las fuentes
        if seen.get(c.article_id, 0) >= 2:
            continue
        seen[c.article_id] = seen.get(c.article_id, 0) + 1
        out.append({'chunk_id': c.id, 'article_id': c.article_id, 'title': c.article.title,
                    'text': c.text, 'rank': round(float(c.rank), 4)})
        if len(out) >= limit:
            break
    return out


ANSWER_PROMPT = """Eres el asistente de atención al cliente de {company}. Responde en español, {tone}.
Usa ÚNICAMENTE la información de los ARTÍCULOS. Si los artículos no contienen la respuesta, no la inventes.
{instructions}
Responde SOLO un objeto JSON:
{{"found": true|false, "answer": "<respuesta para el cliente, máximo {max_chars} caracteres, sin mencionar 'artículos'>", "sources": [<números de los artículos usados>]}}

ARTÍCULOS:
{articles}"""


def answer(question, kb_ids=None, provider=None, *, min_rank=0.01, max_chars=700, tone='amable y breve',
           instructions='', company='la empresa', source='bot', conversation_id=None):
    """
    Devuelve (status, result). status: answered | not_found | error.
    result = {"answer", "sources": [{"article_id","title"}], "articles": [...]}
    """
    from .ai import AIError, chat_json, mask, _check_budget, _log
    from .models import KnowledgeQuery

    masked_q, mapping = mask(question or '')
    hits = [h for h in search(masked_q, kb_ids) if h['rank'] >= (min_rank or 0)]

    def log(found, ids):
        try:
            KnowledgeQuery.objects.create(knowledge_base_id=(kb_ids or [None])[0] if kb_ids and len(kb_ids) == 1 else None,
                                          question=masked_q[:1000], found=found, article_ids=ids, source=source,
                                          conversation_id=conversation_id)
        except Exception:
            logger.exception('[KB] No se pudo registrar la consulta')

    if not hits:
        log(False, [])
        return 'not_found', {'answer': '', 'sources': []}

    if provider is None:
        # Sin IA: el fragmento más relevante, tal cual
        top = hits[0]
        log(True, [top['article_id']])
        text = top['text'][:max_chars].rsplit(' ', 1)[0] if len(top['text']) > max_chars else top['text']
        return 'answered', {'answer': f"*{top['title']}*\n{text}", 'sources': [{'article_id': top['article_id'], 'title': top['title']}]}

    _check_budget(provider)
    t0 = time.monotonic()
    articles = '\n\n'.join(f"[{i + 1}] {h['title']}\n{h['text']}" for i, h in enumerate(hits))
    system = ANSWER_PROMPT.format(company=company, tone=tone, instructions=(instructions or '')[:500],
                                  max_chars=max_chars, articles=articles)
    usage = {}
    try:
        out, usage = chat_json(provider, system, f'Pregunta del cliente: """{masked_q[:1500]}"""')
        found = bool(out.get('found')) and bool((out.get('answer') or '').strip())
        idx = [int(s) for s in (out.get('sources') or []) if str(s).isdigit() and 1 <= int(s) <= len(hits)]
        sources = []
        for i in idx or ([1] if found else []):
            h = hits[i - 1]
            if all(s['article_id'] != h['article_id'] for s in sources):
                sources.append({'article_id': h['article_id'], 'title': h['title']})
        _log(provider, 'kb_answer', 'success', usage, t0, result='respondida' if found else 'sin respuesta',
             conversation_id=conversation_id)
        log(found, [s['article_id'] for s in sources])
        if not found:
            return 'not_found', {'answer': '', 'sources': []}
        from .ai import unmask
        return 'answered', {'answer': unmask(out['answer'].strip()[:max_chars + 100], mapping), 'sources': sources}
    except AIError as e:
        _log(provider, 'kb_answer', 'error', usage, t0, error=str(e), conversation_id=conversation_id)
        return 'error', {'error': str(e)[:200]}
    except Exception as e:
        _log(provider, 'kb_answer', 'error', usage, t0, error=f'{type(e).__name__}: {e}', conversation_id=conversation_id)
        return 'error', {'error': str(e)[:200]}


def import_file(kb, path, original_name, user=None):
    """Crea (o actualiza) un artículo con el texto de un documento. Lee el archivo en el servidor."""
    import os
    import requests
    from .models import KnowledgeArticle
    base = os.getenv('TRANSCRIBER_URL', '').rstrip('/')
    if not base:
        raise RuntimeError('El servicio de lectura de archivos (transcriber) está desactivado')
    resp = requests.post(f'{base}/extract', json={'path': path}, timeout=600)
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        raise RuntimeError(data.get('error') or f'HTTP {resp.status_code}')
    text = (data.get('text') or '').strip()
    if len(text) < 20:
        raise RuntimeError('El documento no tiene texto legible')
    title = os.path.splitext(original_name)[0].replace('_', ' ').strip()[:250] or 'Documento'
    article, _ = KnowledgeArticle.objects.update_or_create(
        knowledge_base=kb, source='file', file_name=original_name[:255],
        defaults={'title': title, 'body': text, 'created_by': user})
    index_article(article)
    return article


def sync_glpi(kb):
    """Importa/actualiza los artículos de la base de conocimiento de GLPI (KnowbaseItem)."""
    from .connectors import get_connector
    from .models import KnowledgeArticle
    if not kb.glpi_connector or kb.glpi_connector.connector_type != 'glpi':
        raise RuntimeError('La base no tiene un conector GLPI')
    conn = get_connector(kb.glpi_connector)
    items = conn.knowledge_items()
    seen = set()
    created = updated = 0
    for it in items:
        ext = str(it.get('id'))
        seen.add(ext)
        body = _strip_html(it.get('answer') or '').strip()
        if not body:
            continue
        art, was_created = KnowledgeArticle.objects.update_or_create(
            knowledge_base=kb, source='glpi', external_id=ext,
            defaults={'title': (it.get('name') or f'Artículo {ext}')[:250], 'body': body,
                      'category': str(it.get('category') or '')[:100], 'is_published': True})
        index_article(art)
        created += was_created
        updated += not was_created
    removed, _ = KnowledgeArticle.objects.filter(knowledge_base=kb, source='glpi').exclude(external_id__in=seen).delete()
    kb.last_synced_at = timezone.now()
    kb.save(update_fields=['last_synced_at'])
    return {'created': created, 'updated': updated, 'removed': removed, 'total': len(items)}
