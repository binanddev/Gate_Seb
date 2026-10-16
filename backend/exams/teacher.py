import secrets
from functools import wraps
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError, transaction
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.cache import never_cache
from .models import Exam
from .views import reply, failure, read_body

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'form_url', 'browser_exam_keys', 'enabled', 'opens_at', 'closes_at']

def signed_in(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return failure('Vui lòng đăng nhập.', 401)
        return view(request, *args, **kwargs)
    return wrapped

def json_input(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            data = read_body(request)
        except (ValueError, TypeError):
            return failure('Dữ liệu không hợp lệ.', 400)
        return view(request, data, *args, **kwargs)
    return wrapped

def user_data(request):
    return {'username': request.user.get_username()} if request.user.is_authenticated else None

def serialize(exam):
    return {'slug': exam.slug, 'title': exam.title, 'form_url': exam.form_url,
            'browser_exam_keys': exam.browser_exam_keys, 'enabled': exam.enabled,
            'opens_at': exam.opens_at.isoformat() if exam.opens_at else '',
            'closes_at': exam.closes_at.isoformat() if exam.closes_at else '',
            'start_url': settings.FRONTEND_URL + '?exam=' + exam.slug}

@never_cache
@require_GET
def account(request):
    return reply({'user': user_data(request), 'csrf': get_token(request)})

@require_POST
@json_input
def register(request, data):
    form = UserCreationForm(data)
    if not form.is_valid():
        return reply({'error': 'Kiểm tra thông tin đăng ký.', 'fields': form.errors.get_json_data()}, 400)
    try:
        with transaction.atomic():
            user = form.save()
    except IntegrityError:
        return failure('Tên đăng nhập đã được sử dụng.', 400)
    # Registration grants only an ordinary account, never staff/admin privileges.
    login(request, user)
    return reply({'user': user_data(request), 'csrf': get_token(request)}, 201)

@require_POST
@json_input
def signin(request, data):
    username, password = data.get('username'), data.get('password')
    if not isinstance(username, str) or not isinstance(password, str):
        return failure('Nhập tên đăng nhập và mật khẩu.', 400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return failure('Tên đăng nhập hoặc mật khẩu không đúng.', 401)
    login(request, user)
    return reply({'user': user_data(request), 'csrf': get_token(request)})

@require_POST
def signout(request):
    logout(request)
    return reply({'user': None, 'csrf': get_token(request)})

@require_http_methods(['GET', 'POST'])
@signed_in
def exams(request):
    if request.method == 'GET':
        return reply({'exams': [serialize(exam) for exam in Exam.objects.filter(owner=request.user).order_by('-id')]})
    return create_exam(request)

@json_input
def create_exam(request, data):
    # Reserve a Start URL before asking for the final BEK: creation is always a draft.
    exam = Exam(owner=request.user, slug=secrets.token_hex(12), enabled=False)
    form = ExamForm({**data, 'enabled': False, 'browser_exam_keys': ''}, instance=exam)
    if not form.is_valid():
        return reply({'error': 'Kiểm tra thông tin kỳ thi.', 'fields': form.errors.get_json_data()}, 400)
    form.save()
    return reply({'exam': serialize(exam)}, 201)

@require_POST
@signed_in
@json_input
def exam_detail(request, data, slug):
    exam = Exam.objects.filter(owner=request.user, slug=slug).first()
    if not exam:
        return failure('Không tìm thấy kỳ thi.', 404)
    form = ExamForm(data, instance=exam)
    if not form.is_valid():
        return reply({'error': 'Kiểm tra thông tin kỳ thi.', 'fields': form.errors.get_json_data()}, 400)
    form.save()
    return reply({'exam': serialize(exam)})
