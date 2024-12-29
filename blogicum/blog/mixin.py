from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from .models import Comment, Post


class CommentMixin(LoginRequiredMixin):
    model = Comment
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.author != request.user:
            raise PermissionDenied(
                'Вы не авторизованы для удаления этого комментария.'
            )
        return super().dispatch(request, *args, **kwargs)


class BasePostMixin:
    def get_queryset(self):
        return Post.objects.select_related(
            'author', 'category', 'location'
        ).prefetch_related('comments__author')


class OnlyAuthorMixin(UserPassesTestMixin):

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user


class PostModelMixin:
    model = Post


class PostFilterMixin:
    def get_posts(self, category=None):
        filters = {
            'pub_date__lte': timezone.now(),
            'is_published': True,
            'category__is_published': True,
        }
        if category:
            filters['category'] = category
        return Post.objects.filter(**filters).order_by(
            '-pub_date').select_related(
            'author', 'category', 'location'
        ).prefetch_related('comments__author')
