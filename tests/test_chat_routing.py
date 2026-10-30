"""Conversation/PDF/web routing boundaries; all external calls mocked here."""
import json
import unittest
from unittest.mock import patch, Mock
import config, rag, study_chat

class ChatRoutingTests(unittest.TestCase):
    def test_capabilities_and_identity_never_use_pdf_or_web(self):
        for q in ['What can you help me with?', 'What can you do?', 'Hi, how can you help me?', 'Who are you?', "What's your name?", 'Introduce yourself', 'What are your features?', 'How do I use Clariqo?', 'Can you help me?', 'What is Clariqo?']:
            with self.subTest(q=q),patch.object(config,'generate_text',return_value='I am Clariqo.') as answer,patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion') as web:
                r=study_chat.reply(q)
                self.assertEqual(r['origin'],'conversation')
                answer.assert_called_once()
                pdf.assert_not_called();web.assert_not_called()
                self.assertIn('Quiz',answer.call_args.kwargs['system_instruction'])

    def test_subject_questions_are_not_swallowed_by_capability_rules(self):
        for q in ['Hello, what is integration?', 'Can you explain integration?', 'What can you tell me about photosynthesis?', 'Who are you? Also explain integration.']:
            with self.subTest(q=q),patch.object(config,'generate_text',return_value=json.dumps({'intent':'question','query':q})) as classify:
                result=study_chat.plan_turn(q,[])
                self.assertEqual(result['intent'],'question')
                classify.assert_called_once()

    def test_routing_uses_strict_schema_without_search(self):
        with patch.object(config,'AI_PROVIDER','groq'),patch.object(config,'generate_text',return_value='{"intent":"conversation","query":"How are things?"}') as classify:
            plan=study_chat.plan_turn('How are things?',[])
        self.assertEqual(plan['intent'],'conversation')
        fmt=classify.call_args.kwargs['response_format']
        self.assertTrue(fmt['json_schema']['strict'])
        self.assertEqual(fmt['json_schema']['schema']['properties']['intent']['enum'],['conversation','question','web'])
        self.assertNotIn('web_search',classify.call_args.kwargs)

    def test_json_fence_variations_are_accepted(self):
        for label in ['json','JSON','Json','']:
            with self.subTest(label=label),patch.object(config,'generate_text',return_value=f'```{label}\n'+json.dumps({'intent':'conversation','query':'How are things?'})+'\n```'):
                self.assertEqual(study_chat.plan_turn('How are things?',[])['intent'],'conversation')

    def test_invalid_classifier_output_asks_for_clarification_without_search(self):
        for raw in ['not json','[]','null','{"intent":"web","query":""}','{"intent":"unknown","query":"study"}']:
            with self.subTest(raw=raw),patch.object(config,'generate_text',return_value=raw) as classify,patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion') as web:
                r=study_chat.reply('A message that needs routing')
                self.assertIn('rephrase',r['answer'])
                classify.assert_called_once();pdf.assert_not_called();web.assert_not_called()

    def test_resolved_followup_keeps_selected_pdf_and_action(self):
        history=[{'role':'user','content':'Explain integration.'},{'role':'assistant','content':'Integration finds accumulated quantities.'}]
        with patch.object(config,'generate_text',return_value='{"intent":"question","query":"Explain integration using a simpler example"}'),patch.object(rag,'answer_question',return_value={'answer':'A simpler example','sources':[{'file_name':'math.pdf','page':1}]}) as pdf,patch.object(config,'generate_completion') as web:
            r=study_chat.reply('Can you give a simpler example?',history=history,file_name='math.pdf')
        self.assertEqual(r['origin'],'pdf')
        pdf.assert_called_once_with('Explain integration using a simpler example',file_name='math.pdf',history=history)
        web.assert_not_called()

    def test_explicit_online_request_bypasses_pdf(self):
        q='Search online for integration tutorials'
        with patch.object(config,'generate_text',return_value=json.dumps({'intent':'web','query':q})),patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion',return_value={'answer':'Tutorials','searched':True,'web_sources':[{'url':'https://example.org','title':'Source'}]}) as web:
            r=study_chat.reply(q,history=[{'role':'assistant','content':'Private context'}])
        self.assertEqual(r['origin'],'web');pdf.assert_not_called()
        self.assertTrue(web.call_args.kwargs['web_search'])
        self.assertNotIn('history',web.call_args.kwargs)
        self.assertNotIn('Private context',str(web.call_args))

    def test_current_information_uses_verified_search(self):
        q='What is the latest stable Python release?'
        with patch.object(config,'generate_text',return_value=json.dumps({'intent':'web','query':q})),patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion',return_value={'answer':'Ungrounded guess','searched':False,'web_sources':[]}):
            r=study_chat.reply(q)
        pdf.assert_not_called()
        self.assertEqual(r['origin'],'error')
        self.assertNotIn('Ungrounded guess',r['answer'])

    def test_provider_errors_do_not_trigger_another_route(self):
        with patch.object(config,'generate_text',side_effect=RuntimeError('Usage limit')),patch.object(rag,'answer_question') as pdf,patch.object(config,'generate_completion') as web:
            with self.assertRaisesRegex(RuntimeError,'Usage limit'):
                study_chat.reply('Can we discuss my learning preferences?')
        pdf.assert_not_called();web.assert_not_called()

    def test_schema_sent_to_groq_only_on_routing_request(self):
        response=Mock(status_code=200,ok=True)
        response.json.return_value={'choices':[{'finish_reason':'stop','message':{'content':'{"intent":"question","query":"Integration"}'}}]}
        with patch.object(config,'AI_PROVIDER','groq'),patch.dict('os.environ',{'GROQ_API_KEY':'test-only-key'}),patch('requests.post',return_value=response) as post:
            config.generate_text('Integration',response_format=study_chat.ROUTING_FORMAT)
            payload=post.call_args.kwargs['json']
        self.assertEqual(payload['response_format'],study_chat.ROUTING_FORMAT)
        self.assertNotIn('tools',payload)
        self.assertNotIn('tool_choice',payload)

    def test_search_cannot_be_combined_with_schema(self):
        with patch.object(config,'AI_PROVIDER','groq'),patch.dict('os.environ',{'GROQ_API_KEY':'test-only-key'}),patch('requests.post') as post:
            with self.assertRaises(ValueError):config.generate_completion('Search',web_search=True,response_format=study_chat.ROUTING_FORMAT)
        post.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
