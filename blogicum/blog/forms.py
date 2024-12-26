from django import forms

from .models import Post, Comment, User


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email',)


class PostCreateForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = '__all__'
        exclude = ('author',)
        widgets = {
            'pub_date': forms.DateInput(
                attrs={'type': 'datetime-local'})}
