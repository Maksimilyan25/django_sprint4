from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Category, Location, Post, Comment


admin.site.site_header = _('Управление Блогикум')
admin.site.site_title = _('Админка')
admin.site.index_title = _('Добро пожаловать в управление сайтом Блогикум')
admin.site.register(Category)
admin.site.register(Location)
admin.site.register(Post)
admin.site.register(Comment)
