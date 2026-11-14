from django import forms
from django.core.exceptions import ValidationError

from .models import Discussion, Reply, Tag


class DiscussionForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        max_length=164,
        help_text='Optional. Enter up to 5 tags separated by commas (for example: python, django).',
        widget=forms.TextInput(attrs={'placeholder': 'python, django'}),
    )

    class Meta:
        model = Discussion
        fields = ('section', 'title', 'body')
        widgets = {
            'body': forms.Textarea(attrs={'rows': 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['tags'] = ', '.join(
                self.instance.tags.values_list('name', flat=True)
            )

    def clean_tags(self):
        raw_tags = self.cleaned_data.get('tags', '')
        tags = []
        seen = set()

        for raw_tag in raw_tags.split(','):
            name = raw_tag.strip().lower()
            if not name or name in seen:
                continue
            if len(name) > 30 or not name[0].isalnum() or any(
                not (character.isalnum() or character in '+#.-')
                for character in name
            ):
                raise ValidationError(
                    'Tags must start with a letter or number and contain only '
                    'letters, numbers, +, #, dots, or hyphens (up to 30 characters).'
                )
            seen.add(name)
            tags.append(name)

        if len(tags) > 5:
            raise ValidationError('Add no more than 5 tags to a discussion.')
        return tags

    def save(self, commit=True):
        discussion = super().save(commit=commit)
        if commit:
            discussion.tags.set(
                Tag.objects.get_or_create(name=name)[0]
                for name in self.cleaned_data['tags']
            )
        return discussion


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ('body',)
        labels = {'body': 'Your reply'}
        widgets = {
            'body': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share a helpful reply...'}),
        }
