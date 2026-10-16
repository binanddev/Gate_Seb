from django.contrib import admin
from django.urls import path
from exams import views
from exams import teacher
from django.conf import settings
from django.http import FileResponse

urlpatterns = [path('admin/', admin.site.urls), path('api/health', views.health),
               path('api/live', views.live),
               path('api/challenge', views.challenge), path('api/verify', views.verify),
               path('api/heartbeat', views.heartbeat),
               path('api/teacher/account', teacher.account),
               path('api/teacher/register', teacher.register),
               path('api/teacher/login', teacher.signin),
               path('api/teacher/logout', teacher.signout),
               path('api/teacher/exams', teacher.exams),
               path('api/teacher/exams/<slug:slug>', teacher.exam_detail)]

# Local preview only: production frontend remains static HTML on Netlify.
if settings.DEBUG:
    urlpatterns += [
        path('', lambda request: FileResponse((settings.BASE_DIR.parent / 'frontend' / 'index.html').open('rb'), content_type='text/html')),
        path('teacher.html', lambda request: FileResponse((settings.BASE_DIR.parent / 'frontend' / 'teacher.html').open('rb'), content_type='text/html')),
    ]
