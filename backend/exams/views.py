import hashlib
import json
import re
import secrets
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from django.conf import settings
from django.core import signing
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from .models import Exam

def reply(data, status=200):
    response = JsonResponse(data, status=status)
    response['Cache-Control'] = 'no-store'
    return response

def failure(message, status=403):
    return reply({'error': message}, status)

def active_exam(slug):
    exam = Exam.objects.filter(slug=slug).first()
    return exam if exam and exam.available() else None

def page_url(slug, token):
    return settings.FRONTEND_URL + '?' + urlencode({'exam': slug, 'challenge': token})

def read_body(request):
    if request.content_type != 'application/json':
        raise ValueError('JSON required')
    data = json.loads(request.body)
    if not isinstance(data, dict):
        raise ValueError('Object required')
    return data

@never_cache
@require_GET
def live(request):
    # Render probes must not continuously wake the free Neon compute.
    return reply({'status': 'alive'})

@never_cache
@require_GET
def health(request):
    # Include database readiness, not merely process liveness.
    Exam.objects.exists()
    return reply({'status': 'ready'})

@require_GET
def challenge(request):
    exam = active_exam(request.GET.get('exam', ''))
    if not exam:
        return failure('Kỳ thi chưa mở, đã đóng hoặc không tồn tại.', 404)
    token = signing.dumps({'exam': exam.slug, 'revision': str(exam.revision),
                           'nonce': secrets.token_urlsafe(24)}, salt='seb-challenge')
    return reply({'page_url': page_url(exam.slug, token)})

# These public endpoints never use admin cookies: verification uses a SEB proof,
# heartbeat uses an explicit short-lived signed bearer token. Admin keeps CSRF.
@csrf_exempt
@require_POST
def verify(request):
    try:
        body = read_body(request)
        token, proof = body.get('challenge'), body.get('proof')
        if not isinstance(token, str) or len(token) > 2048 or not isinstance(proof, str) or not re.fullmatch('[0-9a-fA-F]{64}', proof):
            return failure('Không có bằng chứng SEB hợp lệ.')
        data = signing.loads(token, salt='seb-challenge', max_age=600)
        exam = active_exam(data['exam'])
        if not exam or data['revision'] != str(exam.revision):
            return failure('Kỳ thi đã đóng hoặc cấu hình đã thay đổi.')
        url = page_url(exam.slug, token)
        matched = False
        for key in exam.browser_exam_keys.split():
            expected = hashlib.sha256((url + key).encode('utf-8')).hexdigest()
            matched |= secrets.compare_digest(expected, proof.lower())
        if not matched:
            return failure('SEB hoặc cấu hình không khớp phiên bản được duyệt. Hãy báo giám thị.')
        session = signing.dumps({'exam': exam.slug, 'revision': str(exam.revision)}, salt='seb-session')
        parts = urlsplit(exam.form_url)
        query = [(k, v) for k, v in parse_qsl(parts.query) if k != 'embedded'] + [('embedded', 'true')]
        embedded = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))
        return reply({'title': exam.title, 'form_url': embedded, 'session': session, 'heartbeat_seconds': 240})
    except signing.SignatureExpired:
        return failure('Phiên xác minh đã hết hạn. Vui lòng thử lại.', 410)
    except (ValueError, TypeError, KeyError, signing.BadSignature):
        return failure('Yêu cầu xác minh không hợp lệ.', 400)

@csrf_exempt
@require_POST
def heartbeat(request):
    try:
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or len(auth) > 4096:
            return failure('Phiên không hợp lệ.', 401)
        data = signing.loads(auth[7:], salt='seb-session', max_age=43200)
        exam = active_exam(data['exam'])
        if not exam or data['revision'] != str(exam.revision):
            return failure('Kỳ thi đã đóng hoặc cấu hình đã thay đổi. Hãy báo giám thị.')
        return reply({'status': 'ok'})
    except (ValueError, TypeError, KeyError, signing.BadSignature):
        return failure('Phiên đã hết hạn. Hãy báo giám thị.', 401)
