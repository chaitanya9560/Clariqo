"""Persistent learning history for the local Clariqo profile."""
import copy
import json
import math
import os
import tempfile
import threading
import uuid
from datetime import datetime, date
from urllib.parse import urlsplit
from functools import wraps
from typing import Dict, Any, List
from config import MEMORY_FILE

DEFAULT_MEMORY_STRUCTURE = {
    'topics_studied': [], 'quiz_history': [], 'weak_topics': [],
    'recent_questions': [], 'total_questions_asked': 0,
    'chat_history': [], 'generated_plan': None, 'completed_study_days': [],
}
_LOCK = threading.RLock()

def _locked(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        with _LOCK:
            return fn(*args, **kwargs)
    return call

def _fresh_default_memory():
    return copy.deepcopy(DEFAULT_MEMORY_STRUCTURE)

def _pdf_sources(value):
    sources = []
    for source in value if isinstance(value, list) else []:
        if not isinstance(source, dict) or not isinstance(source.get('file_name'), str):
            continue
        page = source.get('page', 1)
        score = source.get('score', 0.0)
        sources.append({'file_name': source['file_name'], 'page': page if type(page) is int and page > 0 else 1,
                        'score': score if type(score) in (int, float) and math.isfinite(score) else 0.0,
                        'snippet': source.get('snippet') if isinstance(source.get('snippet'), str) else ''})
    return sources

def _web_sources(value):
    sources = []
    for source in value if isinstance(value, list) else []:
        if not isinstance(source, dict) or not isinstance(source.get('url'), str):
            continue
        url = source['url']
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or any(c in url for c in '<>\r\n'):
                continue
        except ValueError:
            continue
        title = source.get('title')
        sources.append({'url': url, 'title': title if isinstance(title, str) and title.strip() else parsed.hostname})
    return sources

def _normalize_plan(plan):
    if not isinstance(plan, dict):
        return None
    for key in ('subject', 'exam_date', 'knowledge_level', 'plan_markdown'):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            return None
    try:
        date.fromisoformat(plan['exam_date'])
    except ValueError:
        return None
    hours = plan.get('daily_hours')
    if type(hours) not in (int, float) or not math.isfinite(hours) or not 0 < hours <= 24:
        return None
    remaining = plan.get('days_remaining')
    if type(remaining) is not int or remaining < 0:
        return None
    cleaned = dict(plan)
    weak = plan.get('weak_topics')
    cleaned['weak_topics'] = [w for w in weak if isinstance(w, str) and w.strip()] if isinstance(weak, list) else []
    cleaned['syllabus_sources'] = _pdf_sources(plan.get('syllabus_sources'))
    if not isinstance(plan.get('plan_id'), str) or not plan['plan_id']:
        cleaned['plan_id'] = uuid.uuid4().hex
    return cleaned

def _normalize(data):
    if not isinstance(data, dict):
        return _fresh_default_memory()
    result = dict(data)
    for key in ('topics_studied', 'weak_topics'):
        items = data.get(key)
        result[key] = list(dict.fromkeys(x.strip() for x in items if isinstance(x, str) and x.strip())) if isinstance(items, list) else []
    recent = data.get('recent_questions')
    result['recent_questions'] = [q for q in recent if isinstance(q, dict) and isinstance(q.get('question'), str)] if isinstance(recent, list) else []
    total = data.get('total_questions_asked')
    result['total_questions_asked'] = max(total if type(total) is int and total >= 0 else 0, len(result['recent_questions']))
    result['recent_questions'] = result['recent_questions'][:30]
    quizzes = data.get('quiz_history')
    result['quiz_history'] = []
    for q in quizzes if isinstance(quizzes, list) else []:
        if not isinstance(q, dict):
            continue
        score, total = q.get('score'), q.get('total')
        if type(score) is not int or type(total) is not int or total <= 0 or not 0 <= score <= total:
            continue
        entry = dict(q, percentage=round(score / total * 100, 1))
        entry['weak_areas'] = [w for w in q.get('weak_areas', []) if isinstance(w, str)] if isinstance(q.get('weak_areas', []), list) else []
        result['quiz_history'].append(entry)
    history = data.get('chat_history')
    result['chat_history'] = []
    for message in history if isinstance(history, list) else []:
        if not isinstance(message, dict) or message.get('role') not in {'user', 'assistant'} or not isinstance(message.get('content'), str):
            continue
        cleaned = dict(message, sources=_pdf_sources(message.get('sources')), web_sources=_web_sources(message.get('web_sources')))
        flow = message.get('rag_flow')
        if flow:
            score = flow.get('top_score') if isinstance(flow, dict) else None
            count = flow.get('chunk_count') if isinstance(flow, dict) else None
            if not isinstance(flow, dict) or not isinstance(flow.get('query'), str) or type(count) is not int or type(score) not in (int, float) or not math.isfinite(score):
                cleaned['rag_flow'] = None
        result['chat_history'].append(cleaned)
    plan = _normalize_plan(data.get('generated_plan'))
    result['generated_plan'] = plan
    completed = data.get('completed_study_days')
    result['completed_study_days'] = sorted({d for d in completed if type(d) is int and d > 0}) if plan and isinstance(completed, list) else []
    return result

@_locked
def save_memory(data):
    """Replace the JSON atomically; a failed write leaves the previous file intact."""
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=MEMORY_FILE.parent, prefix='.memory-', suffix='.tmp', delete=False) as f:
            staged = f.name
            json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(staged, MEMORY_FILE)
    finally:
        if staged is not None:
            try: os.unlink(staged)
            except FileNotFoundError: pass

@_locked
def load_memory():
    raw = None
    if MEMORY_FILE.exists():
        try:
            raw = json.loads(MEMORY_FILE.read_text(encoding='utf-8'), parse_constant=lambda _: None)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Preserve the unreadable file for recovery instead of silently losing it.
            backup = MEMORY_FILE.with_name(f'{MEMORY_FILE.name}.invalid-{uuid.uuid4().hex[:8]}')
            backup.write_bytes(MEMORY_FILE.read_bytes())
    normalized = _normalize(raw)
    if raw != normalized:
        save_memory(normalized)
    return normalized

@_locked
def add_topic_studied(topic):
    if not isinstance(topic, str) or not topic.strip(): return
    data = load_memory()
    if topic.strip() not in data['topics_studied']:
        data['topics_studied'].append(topic.strip())
        save_memory(data)

@_locked
def add_question(question, topic='General'):
    if not isinstance(question, str) or not question.strip(): return
    data = load_memory()
    data['recent_questions'].insert(0, {'question': question.strip(), 'topic': topic.strip() if topic else 'General', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    data['recent_questions'] = data['recent_questions'][:30]
    data['total_questions_asked'] += 1
    save_memory(data)

@_locked
def add_quiz_result(topic, score, total, percentage, weak_areas=None, assessed_areas=None, concept_scores=None):
    if type(score) is not int or type(total) is not int or total <= 0 or not 0 <= score <= total:
        raise ValueError('A quiz result needs a valid score and question count.')
    data = load_memory()
    percentage = round(score / total * 100, 1)
    weak_areas = [a.strip() for a in (weak_areas or []) if isinstance(a, str) and a.strip()]
    assessed_areas = [a.strip() for a in (assessed_areas or []) if isinstance(a, str) and a.strip()]
    entry = {'topic': topic.strip() if topic else 'General Study Material', 'score': score, 'total': total, 'percentage': percentage, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'weak_areas': weak_areas}
    entry['concept_scores'] = concept_scores or {}
    data['quiz_history'].insert(0, entry)
    if entry['topic'] not in data['topics_studied']: data['topics_studied'].append(entry['topic'])
    weak = set(data['weak_topics'])
    weak.difference_update(set(assessed_areas) - set(weak_areas))
    if percentage < 70: weak.add(entry['topic'])
    elif percentage >= 85: weak.discard(entry['topic'])
    weak.update(weak_areas)
    data['weak_topics'] = sorted(weak)
    save_memory(data)

@_locked
def save_chat_history(history):
    data = load_memory()
    data['chat_history'] = copy.deepcopy(history)
    save_memory(data)

@_locked
def save_study_plan(plan):
    data = load_memory()
    stored = copy.deepcopy(plan)
    stored['plan_id'] = uuid.uuid4().hex
    data['generated_plan'] = stored
    data['completed_study_days'] = []
    save_memory(data)
    return stored

@_locked
def save_completed_study_days(days, plan_id):
    data = load_memory()
    plan = data['generated_plan']
    if not plan or plan.get('plan_id') != plan_id:
        raise ValueError('Your study plan changed in another tab. Refresh to use the saved plan.')
    from study_plan import parse_study_plan_to_days
    allowed = {d['day_number'] for d in parse_study_plan_to_days(plan['plan_markdown'])}
    data['completed_study_days'] = sorted(set(days) & allowed)
    save_memory(data)

def get_student_memory():
    return load_memory()

def get_progress_summary():
    data = load_memory()
    history = data['quiz_history']
    # Score is weighted by answered question count, not by quiz size.
    total = sum(q['total'] for q in history)
    average = round(sum(q['score'] for q in history) / total * 100, 1) if total else 0.0
    focus_scores = {}
    for topic in data['weak_topics']:
        focus_scores[topic] = None
        for attempt in history:
            concept = attempt.get('concept_scores', {}).get(topic) if isinstance(attempt.get('concept_scores'), dict) else None
            if isinstance(concept, dict) and type(concept.get('score')) is int and type(concept.get('total')) is int and 0 <= concept['score'] <= concept['total'] and concept['total'] > 0:
                focus_scores[topic] = round(concept['score'] / concept['total'] * 100, 1)
                break
            if attempt.get('topic') == topic:
                focus_scores[topic] = attempt['percentage']
                break
            if topic in attempt.get('weak_areas', []):
                break  # Older records have no per-concept score; don't invent one.
    return {'total_topics_studied': len(data['topics_studied']), 'total_questions_asked': data['total_questions_asked'],
            'total_quizzes_taken': len(history), 'average_quiz_score': average,
            'topics_studied': data['topics_studied'], 'weak_topics': data['weak_topics'],
            'quiz_history': history, 'recent_questions': data['recent_questions'], 'focus_scores': focus_scores}

@_locked
def clear_memory():
    """Reset progress; saved chat and the current study plan have separate controls."""
    old = load_memory()
    fresh = _fresh_default_memory()
    for key in ('chat_history', 'generated_plan', 'completed_study_days'):
        fresh[key] = old[key]
    save_memory(fresh)
