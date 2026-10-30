"""Explicit live Groq audit using sample prompts and user-approved lemh202.pdf.
Records results without writing test quiz scores/questions to the user's memory.
"""
import json,time,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
from datetime import date,timedelta
import config,study_chat,rag,quiz,study_plan,memory

out=Path('test_results/deep-live.json')
out.parent.mkdir(exist_ok=True)
records=[]
def check(name,fn):
    started=time.monotonic()
    try: details=fn();status='PASS'
    except Exception as e: details={'error':str(e)};status='FAIL'
    records.append({'name':name,'status':status,'seconds':round(time.monotonic()-started,2),'details':details})
    out.write_text(json.dumps(records,indent=2,ensure_ascii=False))
    print(name,status,flush=True)
def chat(q,history=None):
    r=study_chat.reply(q,history=history)
    assert r['origin']=='conversation',f"Unexpected origin: {r['origin']}; {r['answer'][:200]}"
    return r

def pdf_answer():
    r=rag.answer_question('Find the area enclosed by the ellipse',file_name='lemh202.pdf')
    assert r['sources'] and all(s['file_name']=='lemh202.pdf' for s in r['sources'])
    assert 'model error' not in r['answer'].lower()
    assert any(t in r['answer'] for t in ['\\pi','π'])
    return r

def quiz_check(n,difficulty):
    context='Cloud elasticity automatically scales computing resources with demand. IaaS supplies virtual machines; PaaS supplies managed application platforms; SaaS supplies ready-to-use applications. A public cloud is shared across organizations. A private cloud is dedicated to one organization.'
    qs=quiz.generate_quiz_questions('Cloud Computing',n,difficulty,context)
    assert len(qs)==n
    assert len({q['question'] for q in qs})==n
    assert all(len(set(q['options'].values()))==4 for q in qs)
    correct={q['id']:q['correct_answer'] for q in qs}
    score=quiz.calculate_quiz_score(qs,correct,'Audit Cloud')
    assert score['percentage']==100
    return {'questions':qs,'answer_key_score':score['percentage'],'note':'Scoring checked against returned key; semantic answers require separate review.'}

def plan_check():
    p=study_plan.generate_study_plan('Cloud Computing',str(date.today()+timedelta(days=3)),2,'Beginner',['Elasticity'])
    days=study_plan.parse_study_plan_to_days(p['plan_markdown'],p['weak_topics'])
    assert [d['day_number'] for d in days]==[1,2,3]
    assert 'elasticity' in p['plan_markdown'].lower()
    return {'plan':p,'parsed_days':days}

def internet_check():
    r=config.generate_completion('Search the official Python documentation: does list.sort() return the sorted list or None?',system_instruction='Search official documentation before answering. Cite the exact supporting page.',web_search=True)
    assert r['searched'] and r['web_sources']
    assert 'none' in r['answer'].lower()
    return r

with tempfile.TemporaryDirectory() as temp,patch.object(memory,'MEMORY_FILE',Path(temp)/'memory.json'):
    check('Original normal-chat regression',lambda:chat('Hello! Can we chat normally?'))
    check('Conversation follow-up',lambda:chat('What subject did I say I prefer?',[
        {'role':'user','content':'My favourite subject is biology.'},
        {'role':'assistant','content':'We can study biology together.'}]))
    check('Capabilities question routing',lambda:chat('What can you help me with?'))
    check('Actual approved PDF ellipse answer',pdf_answer)
    check('Five easy quiz questions and scoring',lambda:quiz_check(5,'Easy'))
    check('Ten hard quiz questions and scoring',lambda:quiz_check(10,'Hard'))
    check('Three-day plan and weak-topic priority',plan_check)
    check('Internet search with independently known fact',internet_check)
print('Saved',out,flush=True)
