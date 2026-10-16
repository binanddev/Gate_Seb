import hashlib
import json
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from django.core import signing
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import Exam

@override_settings(FRONTEND_URL='https://school.netlify.app/', ALLOWED_HOSTS=['testserver'],
                   SECURE_SSL_REDIRECT=False, CORS_ALLOWED_ORIGINS=['https://school.netlify.app'])
class GatewayTests(TestCase):
    def setUp(self):
        self.key = 'a' * 64
        self.exam = Exam.objects.create(slug='math', title='Toán', browser_exam_keys=self.key,
            form_url='https://docs.google.com/forms/d/e/demo/viewform')

    def challenge(self):
        url = self.client.get('/api/challenge?exam=math').json()['page_url']
        token = parse_qs(urlsplit(url).query)['challenge'][0]
        return url, token

    def verify(self, url=None, token=None, proof=None):
        if token is None:
            url, token = self.challenge()
        proof = proof or hashlib.sha256((url + self.key).encode()).hexdigest()
        return self.client.post('/api/verify', data=json.dumps({'challenge': token, 'proof': proof}), content_type='application/json')

    def test_valid_proof_releases_embedded_form_and_session(self):
        response = self.verify()
        self.assertEqual(response.status_code, 200)
        self.assertIn('embedded=true', response.json()['form_url'])
        self.assertNotIn(self.key, response.content.decode())
        self.assertEqual(response['Cache-Control'], 'no-store')
        token = response.json()['session']
        self.assertEqual(self.client.post('/api/heartbeat', HTTP_AUTHORIZATION='Bearer ' + token).status_code, 200)

    def test_wrong_key_does_not_release_form(self):
        response = self.verify(proof='0' * 64)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('form_url', response.json())

    def test_proof_cannot_be_replayed_on_another_challenge(self):
        url1, token1 = self.challenge()
        url2, token2 = self.challenge()
        proof = hashlib.sha256((url1 + self.key).encode()).hexdigest()
        self.assertNotEqual(token1, token2)
        self.assertEqual(self.verify(url2, token2, proof).status_code, 403)

    def test_frontend_page_hash_not_backend_url_hash(self):
        url, token = self.challenge()
        proof = hashlib.sha256(('https://backend.test/api/verify' + self.key).encode()).hexdigest()
        self.assertEqual(self.verify(url, token, proof).status_code, 403)

    def test_expired_challenge(self):
        with patch('django.core.signing.time.time', return_value=1000):
            url, token = self.challenge()
        self.assertEqual(self.verify(url, token).status_code, 410)

    def test_tampered_challenge(self):
        url, token = self.challenge()
        self.assertEqual(self.verify(url, token + 'x').status_code, 400)

    def test_disabled_or_closed_exam(self):
        self.exam.enabled = False
        self.exam.save()
        self.assertEqual(self.client.get('/api/challenge?exam=math').status_code, 404)
        self.exam.enabled = True
        self.exam.closes_at = timezone.now() - timedelta(seconds=1)
        self.exam.save()
        self.assertEqual(self.client.get('/api/challenge?exam=math').status_code, 404)

    def test_future_exam_is_closed(self):
        self.exam.opens_at = timezone.now() + timedelta(hours=1)
        self.exam.save()
        self.assertEqual(self.client.get('/api/challenge?exam=math').status_code, 404)

    def test_configuration_change_revokes_session(self):
        token = self.verify().json()['session']
        self.exam.title = 'Changed'
        self.exam.save()
        self.assertEqual(self.client.post('/api/heartbeat', HTTP_AUTHORIZATION='Bearer ' + token).status_code, 403)

    def test_missing_and_expired_session(self):
        self.assertEqual(self.client.post('/api/heartbeat').status_code, 401)
        with patch('django.core.signing.time.time', return_value=1000):
            token = signing.dumps({'exam': 'math', 'revision': str(self.exam.revision)}, salt='seb-session')
        self.assertEqual(self.client.post('/api/heartbeat', HTTP_AUTHORIZATION='Bearer ' + token).status_code, 401)

    def test_malformed_requests_fail_closed(self):
        for payload in ('[]', 'null', '{', '{"challenge":42,"proof":[]}'):
            response = self.client.post('/api/verify', data=payload, content_type='application/json')
            self.assertIn(response.status_code, (400, 403))

    def test_multiple_approved_keys(self):
        self.exam.browser_exam_keys = 'b' * 64 + '\n' + self.key
        self.exam.save()
        self.assertEqual(self.verify().status_code, 200)

    def test_reject_non_google_or_edit_url(self):
        for url in ('https://evil.test/viewform', 'https://docs.google.com.evil.test/forms/d/x/viewform',
                    'https://docs.google.com/forms/d/x/edit', 'https://forms.gle/abc'):
            self.exam.form_url = url
            with self.assertRaises(ValidationError):
                self.exam.full_clean()

    def test_admin_requires_login_and_legacy_update_is_removed(self):
        self.assertEqual(self.client.get('/admin/exams/exam/').status_code, 302)
        self.assertEqual(self.client.post('/api/update-config').status_code, 404)

    def test_cors_restricts_origin(self):
        accepted = self.client.get('/api/health', HTTP_ORIGIN='https://school.netlify.app')
        self.assertEqual(accepted['Access-Control-Allow-Origin'], 'https://school.netlify.app')
        rejected = self.client.get('/api/health', HTTP_ORIGIN='https://evil.test')
        self.assertNotIn('Access-Control-Allow-Origin', rejected)
