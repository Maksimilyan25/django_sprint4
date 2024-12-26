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


class CommentMixin(LoginRequiredMixin):
    model = Comment
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.author != request.user:
            raise PermissionError('Для удаления комментария требуется авторизация.')
        return super().dispatch(request, *args, **kwargs)


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


class PostListView(PostFilterMixin, ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        queryset = self.get_posts() \
            .select_related('author', 'location', 'category') \
            .annotate(comment_count=Count('comments')) \
            .order_by('-pub_date')
        return queryset


class CategoryPostsView(PostFilterMixin, ListView):
    model = Post
    template_name = 'blog/category.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        category = get_object_or_404(Category.objects.filter(is_published=True).prefetch_related('post_set'), slug=category_slug)
        return self.get_posts(category).prefetch_related('author', 'location')


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


class PostUpdateView(OnlyAuthorMixin, UpdateView):
    model = Post
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


class ProfileView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = NUM_POST

    def get_queryset(self):
        username = self.kwargs.get('username')
        user = get_object_or_404(User.objects.select_related(), username=username)
        return Post.objects.filter(author=user).order_by('-pub_date').select_related('author', 'location', 'category').annotate(comment_count=Count('comments'))

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


class CommentUpdateView(CommentMixin, UpdateView):
    form_class = CommentForm
    success_url = reverse_lazy('blog:index')

    def get_object(self):
        comment_id = self.kwargs.get('comment_id')
        return get_object_or_404(Comment, id=comment_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_id'] = self.kwargs.get('post_id')
        return context



class CommentDeleteView(CommentMixin, DeleteView):

    def get_object(self):
        return get_object_or_404(Comment, id=self.kwargs.get('comment_id'))

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.id})
