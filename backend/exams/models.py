import re
import uuid
from urllib.parse import urlsplit
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

class Exam(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='exams')
    slug = models.SlugField(unique=True, verbose_name='Mã kỳ thi')
    title = models.CharField(max_length=200, verbose_name='Tên kỳ thi')
    form_url = models.URLField(max_length=1000, verbose_name='URL Google Form',
        help_text='Dán URL đầy đủ docs.google.com/forms/d/e/.../viewform, không dùng forms.gle.')
    browser_exam_keys = models.TextField(blank=True, verbose_name='Browser Exam Keys',
        help_text='Mỗi dòng một BEK 64 ký tự từ phiên bản SEB được duyệt. Không dùng Config Key.')
    enabled = models.BooleanField(default=True, verbose_name='Cho phép vào thi')
    opens_at = models.DateTimeField(null=True, blank=True, verbose_name='Mở lúc')
    closes_at = models.DateTimeField(null=True, blank=True, verbose_name='Đóng lúc')
    revision = models.UUIDField(default=uuid.uuid4, editable=False)

    def clean(self):
        super().clean()
        url = urlsplit(self.form_url)
        if (url.scheme != 'https' or url.netloc != 'docs.google.com' or
            not re.fullmatch(r'/forms/d/(?:e/)?[A-Za-z0-9_-]+/viewform', url.path) or url.fragment):
            raise ValidationError({'form_url': 'Cần URL HTTPS Google Forms đầy đủ kết thúc bằng /viewform.'})
        keys = self.browser_exam_keys.split()
        if (self.enabled and not keys) or len(keys) > 20 or any(not re.fullmatch('[0-9a-fA-F]{64}', key) for key in keys):
            raise ValidationError({'browser_exam_keys': 'Nhập 1–20 BEK, mỗi khóa 64 ký tự hex.'})
        self.browser_exam_keys = '\n'.join(dict.fromkeys(key.lower() for key in keys))
        if self.opens_at and self.closes_at and self.opens_at >= self.closes_at:
            raise ValidationError('Giờ đóng phải sau giờ mở.')

    def save(self, *args, **kwargs):
        self.full_clean()
        self.revision = uuid.uuid4()
        return super().save(*args, **kwargs)

    def available(self):
        now = timezone.now()
        return self.enabled and (not self.opens_at or now >= self.opens_at) and (not self.closes_at or now < self.closes_at)

    def __str__(self):
        return self.title
