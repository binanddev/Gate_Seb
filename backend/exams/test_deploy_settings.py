import os
import runpy
from pathlib import Path
from unittest.mock import patch
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

class DeploymentSettingsTests(SimpleTestCase):
    def settings(self, **overrides):
        env = {'DJANGO_SECRET_KEY': 'test-only-key', 'DATABASE_URL': 'postgresql://user:pass@localhost/db',
               'FRONTEND_URL': ' school.netlify.app ', 'RENDER_EXTERNAL_HOSTNAME': 'actual-service.onrender.com'}
        env.update(overrides)
        with patch.dict(os.environ, env, clear=True):
            return runpy.run_path(str(Path(__file__).resolve().parents[1] / 'config' / 'settings.py'))

    def test_render_hostname_and_frontend_defaults(self):
        config = self.settings()
        self.assertFalse(config['DEBUG'])
        self.assertIn('actual-service.onrender.com', config['ALLOWED_HOSTS'])
        self.assertEqual(config['FRONTEND_URL'], 'https://school.netlify.app/')
        self.assertEqual(config['CSRF_TRUSTED_ORIGINS'], ['https://school.netlify.app'])

    def test_manual_custom_domain_is_preserved(self):
        config = self.settings(ALLOWED_HOSTS=' exam.example.com, ')
        self.assertIn('exam.example.com', config['ALLOWED_HOSTS'])
        self.assertIn('actual-service.onrender.com', config['ALLOWED_HOSTS'])

    def test_invalid_frontend_urls_are_rejected(self):
        for url in ('', 'http://school.example/', 'https:///missing', 'https://school.example/?exam=1',
                    'https://school.example/teacher.html', 'https://user:password@school.example/'):
            with self.subTest(url=url), self.assertRaises(ImproperlyConfigured):
                self.settings(FRONTEND_URL=url)

    def test_no_insecure_production_secret_fallback(self):
        with self.assertRaises(ImproperlyConfigured):
            self.settings(DJANGO_SECRET_KEY='')

    def test_neon_pooled_connection(self):
        config = self.settings(DATABASE_URL='postgresql://user:pass@sample-pooler.example/neondb?sslmode=require&channel_binding=require')
        db = config['DATABASES']['default']
        self.assertEqual(db['CONN_MAX_AGE'], 0)
        self.assertTrue(db['DISABLE_SERVER_SIDE_CURSORS'])
        self.assertEqual(db['OPTIONS']['sslmode'], 'require')
        self.assertEqual(db['OPTIONS']['channel_binding'], 'require')
        self.assertEqual(db['OPTIONS']['connect_timeout'], 10)

    def test_production_requires_database(self):
        with self.assertRaises(ImproperlyConfigured):
            self.settings(DATABASE_URL='')

    def test_render_liveness_does_not_query_database(self):
        from django.test import override_settings
        with override_settings(ALLOWED_HOSTS=['testserver'], SECURE_SSL_REDIRECT=False):
            response = self.client.get('/api/live')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'alive')
