from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import CustomUser

from .forms import DiscussionForm, ReplyForm
from .models import CommunitySection, Discussion, Reply, Tag


def section_list(request):
    sections = CommunitySection.objects.annotate(
        discussion_count=Count('discussions', distinct=True),
        follower_count=Count('followers', distinct=True),
    )
    return render(request, 'community/section_list.html', {'sections': sections})


class SectionDetailView(DetailView):
    model = CommunitySection
    template_name = 'community/section_detail.html'
    context_object_name = 'section'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['discussions'] = self.object.discussions.select_related('author')
        context['is_following'] = (
            self.request.user.is_authenticated
            and self.object.followers.filter(pk=self.request.user.pk).exists()
        )
        return context


@login_required
def toggle_follow(request, section_slug):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    section = get_object_or_404(CommunitySection, slug=section_slug)
    if section.followers.filter(pk=request.user.pk).exists():
        section.followers.remove(request.user)
        messages.success(request, f'You unfollowed {section.name}.')
    else:
        section.followers.add(request.user)
        messages.success(request, f'You are now following {section.name}.')
    return redirect(section)


class DiscussionListView(ListView):
    model = Discussion
    template_name = 'community/discussion_list.html'
    context_object_name = 'discussions'
    queryset = Discussion.objects.select_related('section', 'author').annotate(
        reply_count=Count('replies', distinct=True)
    ).prefetch_related('tags')


class TagDiscussionListView(ListView):
    model = Discussion
    template_name = 'community/tag_detail.html'
    context_object_name = 'discussions'

    def dispatch(self, request, *args, **kwargs):
        self.tag = get_object_or_404(Tag, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Discussion.objects.filter(tags=self.tag)
            .select_related('section', 'author')
            .annotate(reply_count=Count('replies', distinct=True))
            .prefetch_related('tags')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


class DiscussionCreateView(LoginRequiredMixin, CreateView):
    model = Discussion
    form_class = DiscussionForm
    template_name = 'community/discussion_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.section = None
        section_slug = kwargs.get('section_slug')
        if section_slug:
            self.section = get_object_or_404(CommunitySection, slug=section_slug)
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.section:
            form.fields.pop('section')
        return form

    def form_valid(self, form):
        form.instance.author = self.request.user
        if self.section:
            form.instance.section = self.section
        response = super().form_valid(form)
        messages.success(self.request, 'Your discussion has been posted.')
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class DiscussionDetailView(DetailView):
    model = Discussion
    template_name = 'community/discussion_detail.html'
    context_object_name = 'discussion'
    queryset = Discussion.objects.select_related('section', 'author').prefetch_related(
        'replies__author', 'tags'
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('reply_form', ReplyForm())
        context['can_manage'] = _can_manage_discussion(
            self.request.user, self.object
        )
        return context


@login_required
def add_reply(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    discussion = get_object_or_404(Discussion, pk=pk)
    form = ReplyForm(request.POST)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.author = request.user
        reply.discussion = discussion
        reply.save()
        messages.success(request, 'Your reply has been added.')
        return redirect(discussion)

    return render(
        request,
        'community/discussion_detail.html',
        {
            'discussion': discussion,
            'reply_form': form,
            'can_manage': _can_manage_discussion(request.user, discussion),
        },
        status=400,
    )


def _can_manage_discussion(user, discussion):
    return user.is_authenticated and (
        user.pk == discussion.author_id
        or user.role in (
            CustomUser.Role.MODERATOR,
            CustomUser.Role.ADMINISTRATOR,
        )
    )


class DiscussionManagerMixin:
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not _can_manage_discussion(request.user, self.object):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class DiscussionUpdateView(LoginRequiredMixin, DiscussionManagerMixin, UpdateView):
    model = Discussion
    form_class = DiscussionForm
    template_name = 'community/discussion_form.html'
    queryset = Discussion.objects.select_related('section', 'author')

    def form_valid(self, form):
        messages.success(self.request, 'Your discussion has been updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class DiscussionDeleteView(LoginRequiredMixin, DiscussionManagerMixin, DeleteView):
    model = Discussion
    template_name = 'community/discussion_confirm_delete.html'
    queryset = Discussion.objects.select_related('section', 'author')
    success_url = reverse_lazy('community:discussion_list')

    def form_valid(self, form):
        messages.success(self.request, 'The discussion has been deleted.')
        return super().form_valid(form)
