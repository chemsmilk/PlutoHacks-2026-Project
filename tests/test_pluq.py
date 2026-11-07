import json
import os
import unittest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient
from main import app
from core.analyzer import analyze
from core.explanations import explain

class AnalyzerTests(unittest.TestCase):
    def test_fictional_normal(self):
        self.assertEqual(analyze('https://example.test/menu')['status'],'clear')
    def test_credentials(self):
        r=analyze('http://paypal.com@account-check.test/login')
        self.assertEqual(r['domain'],'account-check.test')
        self.assertEqual({f['id'] for f in r['findings']},{'http','credentials'})
    def test_brand(self):
        self.assertIn('brand',[f['id'] for f in analyze('https://paypal.account-check.test')['findings']])
    def test_ip(self):
        for url in ('https://127.0.0.1','https://[::1]'):
            self.assertIn('local',[f['id'] for f in analyze(url)['findings']])
    def test_invalid(self):
        for value in ('javascript:alert(1)','WIFI:S:demo;P:secret;;','hello','https://','https://a.test:bad','https://a.test\\@b.test','https://a.test\npath','https://2130706433','https://a..test'):
            with self.subTest(value=value): self.assertEqual(analyze(value)['status'],'unknown')
    def test_idna(self):
        self.assertIn('unicode',[f['id'] for f in analyze('https://tést.test')['findings']])
    def test_no_network(self):
        with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
            r=analyze('https://paypal.check.test/path?next=https%3A%2F%2Fexample.test')
        self.assertFalse(r['destination_contacted'])
    def test_private_suffix(self):
        # Fixture only: never contacted.
        self.assertEqual(analyze('https://sample.github.io')['domain'],'sample.github.io')

class APITests(unittest.TestCase):
    def setUp(self): self.client=TestClient(app)
    def test_end_to_end(self):
        with patch('socket.create_connection',side_effect=AssertionError('No outbound connections')):
            r=self.client.post('/api/analyze',json={'text':'http://trusted.test@other.test'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['host'],'other.test')
        self.assertIn("connect-src 'self'",r.headers['content-security-policy'])
    def test_input_limits(self):
        self.assertEqual(self.client.post('/api/analyze',json={'text':'x'*4097}).status_code,422)
    def test_cross_origin(self):
        self.assertEqual(self.client.post('/api/analyze',json={'text':'https://example.test'},headers={'Origin':'https://other.test'}).status_code,403)
    def test_shell_assets(self):
        for path in ('/','/app.js','/style.css','/vendor/jsQR.js','/manifest.webmanifest','/icon-192.png','/demo-ordinary.png'):
            self.assertEqual(self.client.get(path).status_code,200,path)

class AITests(unittest.TestCase):
    def setUp(self): self.result=analyze('http://example.test')
    def test_disabled_never_calls(self):
        with patch.dict(os.environ,{'PLUQ_AI_ENABLED':'false'}),patch('httpx.Client') as client:
            self.assertEqual(explain(self.result)['source'],'rules');client.assert_not_called()
    def mocked(self,output=None,error=None):
        env={'PLUQ_AI_ENABLED':'true','OPENAI_API_KEY':'mock-not-a-key','OPENAI_MODEL':'mock-model'}
        with patch.dict(os.environ,env),patch('httpx.Client') as client:
            response=MagicMock()
            response.json.return_value={'output':[{'content':[{'type':'output_text','text':json.dumps(output)}]}]}
            client.return_value.__enter__.return_value.post.return_value=response
            if error: client.return_value.__enter__.return_value.post.side_effect=error
            result=explain(self.result)
            if not error:
                sent=client.return_value.__enter__.return_value.post.call_args.kwargs['json']
                self.assertNotIn('example.test',json.dumps(sent))
            return result
    def test_mock_ai(self): self.assertEqual(self.mocked({'order':['http'],'intro':'verify_sender'})['source'],'ai')
    def test_hallucinated_finding_rejected(self): self.assertEqual(self.mocked({'order':['malware'],'intro':'verify_sender'})['source'],'rules')
    def test_timeout(self): self.assertEqual(self.mocked(error=httpx.ReadTimeout('mock timeout'))['source'],'rules')
    def test_unsafe_intro_rejected(self): self.assertEqual(self.mocked({'order':['http'],'intro':'This site is safe'})['source'],'rules')

if __name__=='__main__': unittest.main()
