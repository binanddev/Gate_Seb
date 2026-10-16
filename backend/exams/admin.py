from django.contrib import admin
from django.conf import settings
from .models import Exam

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'enabled', 'opens_at', 'closes_at')
    search_fields = ('title', 'slug')
    readonly_fields = ('start_url',)
    def start_url(self, obj):
        return f'{settings.FRONTEND_URL}?exam={obj.slug}' if obj and obj.pk else 'Lưu kỳ thi để xem Start URL.'
    start_url.short_description = 'Start URL cho SEB'

admin.site.site_header = 'Quản trị cổng SEB'
