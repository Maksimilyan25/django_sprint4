from django.shortcuts import redirect, get_object_or_404
from django.http import Http404
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from django.urls import reverse, reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch

from .mixin import (
    CommentMixin,
    OnlyAuthorMixin,
    PostModelMixin,
    PostFilterMixin,
    BasePostMixin
)

from .models import Post, Category, Comment

from .forms import ProfileUpdateForm, PostCreateForm, CommentForm


NUM_POST = 10


class PostListView(PostFilterMixin, PostModelMixin, ListView):
    template_name = 'blog/index.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        queryset = self.get_posts().annotate(comment_count=Count('comments'))
        return queryset


class CategoryPostsView(PostFilterMixin, BasePostMixin, ListView):
    template_name = 'blog/category.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(
            Category.objects.filter(is_published=True).prefetch_related(
                'posts', 'posts__author'), slug=category_slug)
        return self.get_posts(category).annotate(
            comment_count=Count('comments')).select_related('author')


class PostDetailView(PostModelMixin, DetailView):
    template_name = 'blog/detail.html'
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_queryset(self):
        return Post.objects.select_related(
            'author', 'category', 'location'
        ).prefetch_related(
            Prefetch(
                'comments', queryset=Comment.objects.select_related(
                    'author')
            )
        )

    def get_object(self, queryset=None):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        if (post.author == self.request.user or (post.is_published
           and post.category.is_published)):

            return post
        raise Http404('Страница не найдена')

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
            kwargs={'username': self.request.user.username}
        )


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


class PostDeleteView(OnlyAuthorMixin, PostModelMixin, DeleteView):
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    context_object_name = 'form'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PostCreateForm(instance=self.get_object())
        context['form'] = form
        return context

    def get_success_url(self):
        return reverse_lazy('blog:index')


class ProfileView(PostModelMixin, BasePostMixin, ListView):
    template_name = 'blog/profile.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        username = self.kwargs.get('username')
        user = get_object_or_404(User, username=username)
        return super().get_queryset().filter(author=user).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')

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
    model = Comment
    form_class = CommentForm

    def get_success_url(self):
        post_id = self.kwargs.get('post_id')
        return reverse('blog:post_detail', kwargs={'post_id': post_id})

    def form_valid(self, form):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        form.instance.post = post
        form.instance.author = self.request.user
        return super().form_valid(form)


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
