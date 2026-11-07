import unittest
from unittest.mock import patch, MagicMock
import os
from fastapi.testclient import TestClient
from main import app
from core.analyzer import analyze
from core.explanations import explain


class URLReviewTests(unittest.TestCase):
    def ids(self,url): return {x['id'] for x in analyze(url)['findings']}

    def test_browser_compatible_idna(self):
        self.assertEqual(analyze('https://faß.test')['host'],'xn--fa-hia.test')
        self.assertEqual(analyze('https://example。test')['host'],'example.test')

    def test_invalid_punycode_and_brackets(self):
        for value in ('https://xn--.test','https://[::1]extra','https://[::1]:','https://example.test..'):
            with self.subTest(value=value): self.assertEqual(analyze(value)['status'],'unknown')

    def test_browser_numeric_aliases(self):
        for host in ('0177.0.0.1','0x7f.0.0.1','127.1','2130706433','example.123','0x7f000001'):
            with self.subTest(host=host): self.assertEqual(analyze('https://'+host)['status'],'unknown')

    def test_root_dot_and_ipv6(self):
        self.assertEqual(analyze('https://example.test.')['host'],'example.test')
        self.assertEqual(analyze('https://[2001:db8::1]:8080')['host'],'2001:db8::1')

    def test_brand_false_positive_and_boundaries(self):
        self.assertNotIn('brand',self.ids('https://pineapple.test'))
        self.assertIn('brand',self.ids('https://paypal-login.test'))
        self.assertIn('brand',self.ids('https://paypal.com.other.test'))

    def test_ordinary_encoding_is_not_a_warning(self):
        self.assertNotIn('encoding',self.ids('https://example.test/hello%20world'))
        self.assertIn('encoding',self.ids('https://example.test/?next=https%3A%2F%2Fother.test'))

    def test_unknown_suffix_does_not_guess_ownership(self):
        result=analyze('https://one.two.example.test')
        self.assertEqual(result['domain'],'one.two.example.test')
        self.assertIn('not established',result['domain_basis'])

    def test_trailing_root_dot_local_host(self):
        self.assertIn('local',self.ids('https://device.local.'))

    def test_only_fictional_inputs_and_no_network(self):
        with patch('socket.socket',side_effect=AssertionError('network forbidden')):
            for value in ('https://faß.test','https://example.test','https://paypal-login.test','https://[2001:db8::1]'):
                self.assertFalse(analyze(value)['destination_contacted'])


class MalformedAITests(unittest.TestCase):
    def test_unexpected_provider_shapes_fall_back(self):
        for payload in (None, [], {'output':None}, {'output':[None]}, {'output':[{'content':[None]}]}, {'output':[{'content':[{'type':'output_text','text':'null'}]}]}):
            with self.subTest(payload=payload), patch.dict(os.environ,{'PLUQ_AI_ENABLED':'true','OPENAI_API_KEY':'mock','OPENAI_MODEL':'mock'}), patch('httpx.Client') as client:
                response=MagicMock();response.json.return_value=payload
                client.return_value.__enter__.return_value.post.return_value=response
                self.assertEqual(explain(analyze('http://example.test'))['source'],'rules')


class BodyLimitTests(unittest.TestCase):
    def test_large_chunked_body_without_content_length(self):
        with TestClient(app) as client:
            response=client.post('/api/analyze',content=iter([b'x'*9000,b'y'*9000]),headers={'Content-Type':'application/json'})
        self.assertEqual(response.status_code,413)

    def test_declared_oversize(self):
        with TestClient(app) as client:
            response=client.post('/api/analyze',content=b'{}',headers={'Content-Length':'17000'})
        self.assertEqual(response.status_code,413)

    def test_valid_unicode_request(self):
        with TestClient(app) as client:
            response=client.post('/api/analyze',json={'text':'https://faß.test'})
        self.assertEqual(response.status_code,200)

if __name__=='__main__': unittest.main()
