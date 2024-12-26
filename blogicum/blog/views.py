from django.shortcuts import redirect, get_object_or_404
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count

from .models import Post, Category, Comment

from .forms import ProfileUpdateForm, PostCreateForm, CommentForm


NUM_POST = 10


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


class PostListView(PostFilterMixin, ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        queryset = self.get_posts() \
            .select_related('author', 'location', 'category') \
            .annotate(comment_count=Count('comments')) \
            .order_by('-created_at')
        return queryset


class CategoryPostsView(PostFilterMixin, ListView):
    model = Post
    template_name = 'blog/category.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(Category.objects.filter(is_published=True), slug=category_slug)
        return self.get_posts(category)


class PostDetailView(PostFilterMixin, DetailView):
    model = Post
    template_name = 'blog/detail.html'
    context_object_name = 'post'

    def form_valid(self, form):
        if not self.test_func():
            post_id = self.get_object().id
            return redirect('blog:post_detail', post_id=post_id)
        return super().form_valid(form)

    def get_object(self, queryset=None):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(self.get_posts(), id=post_id)
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = Comment.objects.filter(post=self.object)
        return context

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostCreateForm
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:profile')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user.username})


class PostUpdateView(UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostCreateForm
    template_name = 'blog/create.html'

    def get_object(self, queryset=None):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, id=post_id)
        return post

    def test_func(self):
        post = self.get_object()
        return self.request.user.is_authenticated and post.author == self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        if not Post.objects.filter(id=self.object.id).exists():
            return redirect('blog:post_detail', post_id=self.object.id)
        return response

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.id})

    def get(self, request, *args, **kwargs):
        if not self.test_func():
            return redirect(reverse('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']}))
        return super().get(request, *args, **kwargs)


class PostDeleteView(UserPassesTestMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'

    def get_object(self, queryset=None):
        post_id = self.kwargs.get('post_id')
        return get_object_or_404(Post, id=post_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = PostCreateForm(instance=self.get_object())
        context['form'] = form
        return context

    def test_func(self):
        object = self.get_object()
        return object.author == self.request.user or self.request.user.is_staff

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user.username})


class ProfileView(LoginRequiredMixin, ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        username = self.kwargs.get('username')
        user = get_object_or_404(User.objects.select_related(), username=username)
        return Post.objects.filter(author=user).annotate(comment_count=Count('comments')).select_related('author', 'location', 'category').order_by('-created_at')

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
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        self.comments = get_object_or_404(Post, id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.comments
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.comments.id})


class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_object(self):
        return get_object_or_404(Comment, pk=self.kwargs['comment_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment'] = self.get_object()
        return context

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.id})


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'

    def get_object(self):
        return get_object_or_404(Comment, pk=self.kwargs['comment_id'])

    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.author

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment'] = self.get_object()
        return context

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.id})
