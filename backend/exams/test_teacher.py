import hashlib
import json
from urllib.parse import urlsplit, parse_qs
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from .models import Exam

@override_settings(FRONTEND_URL='https://school.netlify.app/', ALLOWED_HOSTS=['testserver'],
                   CSRF_TRUSTED_ORIGINS=['https://school.netlify.app'], SECURE_SSL_REDIRECT=False)
class TeacherFlowTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.csrf = self.client.get('/api/teacher/account').json()['csrf']

    def post(self, path, data):
        response = self.client.post('/api/teacher/'+path, json.dumps(data), content_type='application/json',
            HTTP_X_CSRFTOKEN=self.csrf, HTTP_ORIGIN='https://school.netlify.app')
        if response.headers.get('Content-Type', '').startswith('application/json'):
            self.csrf = response.json().get('csrf', self.csrf)
        return response

    def register(self, username='teacher_one'):
        return self.post('register', {'username':username,'password1':'Distinct!Apricot8362','password2':'Distinct!Apricot8362',
                                     'is_staff':True,'is_superuser':True})

    def draft(self):
        response = self.post('exams', {'title':'Toán học', 'form_url':'https://docs.google.com/forms/d/e/demo/viewform',
                                      'enabled':True})
        self.assertEqual(response.status_code,201,response.content)
        return response.json()['exam']

    def test_complete_teacher_to_student_flow(self):
        self.assertEqual(self.register().status_code,201)
        user=get_user_model().objects.get(username='teacher_one')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        exam=self.draft()
        self.assertFalse(exam['enabled'])
        self.assertEqual(self.client.get('/api/challenge', {'exam':exam['slug']}).status_code,404)
        self.assertEqual(Exam.objects.get(slug=exam['slug']).owner,user)
        # Stable Start URL is issued before saving final SEB configuration / BEK.
        start_url=exam['start_url']
        exam['browser_exam_keys']='c'*64
        exam['enabled']=True
        updated=self.post('exams/'+exam['slug'],exam)
        self.assertEqual(updated.status_code,200,updated.content)
        self.assertEqual(updated.json()['exam']['start_url'],start_url)
        self.assertEqual(self.post('logout',{}).status_code,200)
        self.assertEqual(self.client.get('/api/teacher/exams').status_code,401)
        # Student does not need a teacher account.
        student=Client()
        page=student.get('/api/challenge',{'exam':exam['slug']}).json()['page_url']
        challenge=parse_qs(urlsplit(page).query)['challenge'][0]
        proof=hashlib.sha256((page+'c'*64).encode()).hexdigest()
        verified=student.post('/api/verify',json.dumps({'challenge':challenge,'proof':proof}),content_type='application/json')
        self.assertEqual(verified.status_code,200)
        self.assertEqual(verified.json()['form_url'],exam['form_url'])
        self.assertEqual(student.post('/api/heartbeat',HTTP_AUTHORIZATION='Bearer '+verified.json()['session']).status_code,200)

    def test_other_teacher_cannot_read_or_change_exam(self):
        self.register();exam=self.draft();self.post('logout',{})
        self.register('teacher_two')
        self.assertEqual(self.client.get('/api/teacher/exams').json()['exams'],[])
        self.assertEqual(self.post('exams/'+exam['slug'],exam).status_code,404)
        self.assertEqual(Exam.objects.get(slug=exam['slug']).title,'Toán học')

    def test_cannot_publish_without_bek(self):
        self.register();exam=self.draft();exam['enabled']=True
        self.assertEqual(self.post('exams/'+exam['slug'],exam).status_code,400)
        self.assertFalse(Exam.objects.get(slug=exam['slug']).enabled)

    def test_csrf_required_for_registration_and_login(self):
        for path in ('register','login','logout','exams'):
            self.assertEqual(self.client.post('/api/teacher/'+path,'{}',content_type='application/json').status_code,403)

    def test_password_validation_and_duplicate_account(self):
        self.assertEqual(self.post('register',{'username':'teacher','password1':'123','password2':'123'}).status_code,400)
        self.assertEqual(self.register().status_code,201)
        self.assertEqual(self.register().status_code,400)

    def test_login_logout_and_session_restoration(self):
        self.register();self.post('logout',{})
        self.assertIsNone(self.client.get('/api/teacher/account').json()['user'])
        self.assertEqual(self.post('login',{'username':'teacher_one','password':'wrong'}).status_code,401)
        self.assertEqual(self.post('login',{'username':'teacher_one','password':'Distinct!Apricot8362'}).status_code,200)
        self.assertEqual(self.client.get('/api/teacher/account').json()['user']['username'],'teacher_one')

    def test_ownership_and_slug_cannot_be_changed(self):
        self.register();exam=self.draft()
        original=Exam.objects.get(slug=exam['slug'])
        payload={**exam,'owner':99999,'slug':'overwritten'}
        self.assertEqual(self.post('exams/'+exam['slug'],payload).status_code,200)
        original.refresh_from_db()
        self.assertEqual(original.slug,exam['slug'])
        self.assertEqual(original.owner.username,'teacher_one')
