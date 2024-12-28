from django.shortcuts import redirect, get_object_or_404
from django.http import Http404
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count

from .models import Post, Category, Comment

from .forms import ProfileUpdateForm, PostCreateForm, CommentForm


NUM_POST = 10


class PostModelMixin:
    model = Post


class OnlyAuthorMixin(UserPassesTestMixin):

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user


class PostFilterMixin:
    def get_posts(self, category=None):
        filters = {
            'pub_date__lte': timezone.now(),
            'is_published': True,
            'category__is_published': True,
        }
        if category:
            filters['category'] = category
        return Post.objects.filter(**filters).order_by('-pub_date')


class PostListView(PostFilterMixin, PostModelMixin, ListView):
    template_name = 'blog/index.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        queryset = self.get_posts() \
            .select_related('author', 'location', 'category') \
            .annotate(comment_count=Count('comments'))
        return queryset


class CategoryPostsView(PostModelMixin, PostFilterMixin, ListView):
    template_name = 'blog/category.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(
            Category.objects.filter(is_published=True).prefetch_related(
                'posts'), slug=category_slug)
        return self.get_posts(category).prefetch_related('author', 'location')


class PostDetailView(PostModelMixin, DetailView):
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return Post.objects.prefetch_related(
            'comments__author').select_related(
                'author', 'category', 'location')

    def get_object(self, queryset=None):
        post_id = self.kwargs.get(self.pk_url_kwarg)
        post = get_object_or_404(self.get_queryset(), id=post_id)
        if not (post.author == self.request.user
                or (post.is_published and post.category.is_published)):
            raise Http404('Пост не найден')
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        comments = post.comments.all().order_by('created_at')
        context['form'] = CommentForm()
        context['comments'] = comments
        return context


class PostCreateView(LoginRequiredMixin, PostModelMixin, CreateView):
    form_class = PostCreateForm
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:profile')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user.username})


class PostUpdateView(OnlyAuthorMixin, PostModelMixin, UpdateView):
    form_class = PostCreateForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def handle_no_permission(self):
        if not self.test_func():
            return redirect(reverse(
                'blog:post_detail', kwargs={'post_id': self.kwargs['post_id']}
            ))

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail', kwargs={'post_id': self.kwargs['post_id']}
        )


class PostDeleteView(OnlyAuthorMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    context_object_name = 'form'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PostCreateForm(instance=self.get_object())
        context['form'] = form
        return context

    def get_success_url(self):
        return reverse_lazy(
            'blog:index'
        )


class ProfileView(PostModelMixin, ListView):
    template_name = 'blog/profile.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        username = self.kwargs.get('username')
        user = get_object_or_404(
            User.objects.select_related(),
            username=username)
        return Post.objects.filter(author=user).order_by(
            '-pub_date').select_related(
                'author', 'location', 'category').annotate(
                    comment_count=Count('comments'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        context['profile'] = user
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileUpdateForm
    template_name = 'blog/user.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.object.username}
        )

    def get_object(self):
        return self.request.user


class CommentCreateView(LoginRequiredMixin, CreateView):
    comments = None
    model = Comment
    form_class = CommentForm
    template_name = 'blog/create.html'

    def dispatch(self, request, *args, **kwargs):
        self.comments = get_object_or_404(Post, id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.comments
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.comments.id})


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


class CommentUpdateView(CommentMixin, UpdateView):
    form_class = CommentForm
    success_url = reverse_lazy('blog:index')

    def get_object(self, queryset=None):
        comment_id = self.kwargs.get('comment_id')
        return get_object_or_404(Comment, id=comment_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_id'] = self.kwargs.get('post_id')
        return context


class CommentDeleteView(CommentMixin, DeleteView):
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        post_id = self.kwargs.get('post_id')
        return reverse_lazy('blog:post_detail', kwargs={'post_id': post_id})
