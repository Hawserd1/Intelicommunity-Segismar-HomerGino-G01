from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import CharField, Count, OuterRef, Prefetch, Q, Subquery, Value
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.models import CustomUser

from .forms import ContentReportForm, DiscussionForm, ReplyForm
from .models import CommunitySection, ContentReport, Discussion, Reply, Tag, Vote


DISCUSSION_SORTS = {
    'newest': ('-created_at', '-pk'),
    'oldest': ('created_at', 'pk'),
    'discussed': ('-reply_count', '-created_at', '-pk'),
}

SECTION_SORTS = {
    'name': ('name',),
    'newest': ('-created_at', '-pk'),
    'oldest': ('created_at', 'pk'),
    'popular': ('-follower_count', '-discussion_count', 'name'),
}


def _annotate_discussion_votes(request, queryset):
    queryset = queryset.annotate(
        upvote_count=Count(
            'votes',
            filter=Q(votes__value=Vote.Value.UP),
            distinct=True,
        ),
        downvote_count=Count(
            'votes',
            filter=Q(votes__value=Vote.Value.DOWN),
            distinct=True,
        ),
    )
    if request.user.is_authenticated:
        user_vote = Subquery(
            Vote.objects.filter(
                discussion_id=OuterRef('pk'),
                user_id=request.user.pk,
            ).values('value')[:1]
        )
    else:
        user_vote = Value('', output_field=CharField())
    return queryset.annotate(user_vote=user_vote)


def _annotate_reply_votes(request, queryset):
    queryset = queryset.annotate(
        upvote_count=Count(
            'votes',
            filter=Q(votes__value=Vote.Value.UP),
            distinct=True,
        ),
        downvote_count=Count(
            'votes',
            filter=Q(votes__value=Vote.Value.DOWN),
            distinct=True,
        ),
    )
    if request.user.is_authenticated:
        user_vote = Subquery(
            Vote.objects.filter(
                reply_id=OuterRef('pk'),
                user_id=request.user.pk,
            ).values('value')[:1]
        )
    else:
        user_vote = Value('', output_field=CharField())
    return queryset.annotate(user_vote=user_vote)


def _filter_discussions(request, queryset):
    query = request.GET.get('q', '').strip()[:100]
    section_id = request.GET.get('section', '').strip()
    tag_id = request.GET.get('tag', '').strip()
    sort = request.GET.get('sort', 'newest')

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(body__icontains=query)
            | Q(section__name__icontains=query)
            | Q(author__username__icontains=query)
            | Q(tags__name__icontains=query)
        )
    if section_id.isdigit():
        queryset = queryset.filter(section_id=int(section_id))
    if tag_id.isdigit():
        queryset = queryset.filter(tags__pk=int(tag_id))

    sort = sort if sort in DISCUSSION_SORTS else 'newest'
    queryset = queryset.annotate(reply_count=Count('replies', distinct=True))
    queryset = _annotate_discussion_votes(request, queryset)
    return (
        queryset
        .distinct()
        .order_by(*DISCUSSION_SORTS[sort])
        .prefetch_related('tags')
    ), {
        'search_query': query,
        'selected_section': section_id,
        'selected_tag': tag_id,
        'selected_sort': sort,
    }


def section_list(request):
    query = request.GET.get('q', '').strip()[:100]
    sort = request.GET.get('sort', 'name')
    if sort not in SECTION_SORTS:
        sort = 'name'

    sections = CommunitySection.objects.all()
    if query:
        sections = sections.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    sections = sections.annotate(
        discussion_count=Count('discussions', distinct=True),
        follower_count=Count('followers', distinct=True),
    ).order_by(*SECTION_SORTS[sort])
    return render(
        request,
        'community/section_list.html',
        {
            'sections': sections,
            'search_query': query,
            'selected_sort': sort,
        },
    )


class SectionDetailView(DetailView):
    model = CommunitySection
    template_name = 'community/section_detail.html'
    context_object_name = 'section'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        discussions, filters = _filter_discussions(
            self.request,
            self.object.discussions.select_related('author', 'section'),
        )
        context['discussions'] = discussions
        context['tags'] = Tag.objects.filter(discussions__section=self.object).distinct()
        context['selected_tag'] = filters['selected_tag']
        context['selected_sort'] = filters['selected_sort']
        context['search_query'] = filters['search_query']
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

    def get_queryset(self):
        queryset, filters = _filter_discussions(
            self.request,
            Discussion.objects.select_related('section', 'author'),
        )
        self.filter_values = filters
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.filter_values)
        context['sections'] = CommunitySection.objects.order_by('name')
        context['tags'] = Tag.objects.order_by('name')
        return context


class TagDiscussionListView(ListView):
    model = Discussion
    template_name = 'community/tag_detail.html'
    context_object_name = 'discussions'

    def dispatch(self, request, *args, **kwargs):
        self.tag = get_object_or_404(Tag, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset, filters = _filter_discussions(
            self.request,
            Discussion.objects.filter(tags=self.tag).select_related(
                'section', 'author'
            ),
        )
        self.filter_values = filters
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        context.update(self.filter_values)
        context['sections'] = CommunitySection.objects.order_by('name')
        context['tags'] = Tag.objects.order_by('name')
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

    def get_queryset(self):
        replies = _annotate_reply_votes(
            self.request,
            Reply.objects.select_related('author'),
        )
        queryset = Discussion.objects.select_related(
            'section', 'author'
        ).prefetch_related(Prefetch('replies', queryset=replies), 'tags')
        return _annotate_discussion_votes(self.request, queryset)

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

    discussion = get_object_or_404(
        _annotate_discussion_votes(
            request,
            Discussion.objects.select_related('section', 'author').prefetch_related(
                Prefetch(
                    'replies',
                    queryset=_annotate_reply_votes(
                        request,
                        Reply.objects.select_related('author'),
                    ),
                ),
                'tags',
            ),
        ),
        pk=pk,
    )
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


class ReplyUpdateView(LoginRequiredMixin, UpdateView):
    model = Reply
    form_class = ReplyForm
    template_name = 'community/reply_form.html'

    def get_queryset(self):
        return Reply.objects.select_related('discussion', 'author')

    def get_object(self, queryset=None):
        reply = super().get_object(queryset)
        if reply.author_id != self.request.user.pk:
            raise PermissionDenied
        return reply

    def form_valid(self, form):
        messages.success(self.request, 'Your reply has been updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return f'{self.object.discussion.get_absolute_url()}#reply-{self.object.pk}'


def _create_content_report(request, *, discussion=None, reply=None):
    target_discussion = discussion or reply.discussion
    target_author = discussion.author if discussion else reply.author
    if target_author.pk == request.user.pk:
        raise PermissionDenied

    report_lookup = {'reported_by': request.user}
    if discussion:
        report_lookup['discussion'] = discussion
    else:
        report_lookup['reply'] = reply

    existing_report = ContentReport.objects.filter(**report_lookup).first()
    form = ContentReportForm(request.POST if request.method == 'POST' else None)
    if existing_report:
        messages.info(request, 'You have already reported this content.')
        return redirect(target_discussion)

    if request.method == 'POST' and form.is_valid():
        _report, created = ContentReport.objects.get_or_create(
            **report_lookup,
            defaults={
                'reason': form.cleaned_data['reason'],
                'details': form.cleaned_data['details'],
            },
        )
        if created:
            messages.success(request, 'Your report was sent to the moderators.')
        else:
            messages.info(request, 'You have already reported this content.')
        target_url = target_discussion.get_absolute_url()
        if reply:
            target_url = f'{target_url}#reply-{reply.pk}'
        return redirect(target_url)

    return render(
        request,
        'community/report_form.html',
        {
            'form': form,
            'discussion': target_discussion,
            'reply': reply,
        },
        status=400 if request.method == 'POST' else 200,
    )


@login_required
def report_discussion(request, pk):
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])
    discussion = get_object_or_404(
        Discussion.objects.select_related('author', 'section'),
        pk=pk,
    )
    return _create_content_report(request, discussion=discussion)


@login_required
def report_reply(request, pk):
    if request.method not in ('GET', 'POST'):
        return HttpResponseNotAllowed(['GET', 'POST'])
    reply = get_object_or_404(
        Reply.objects.select_related(
            'author',
            'discussion__author',
            'discussion__section',
        ),
        pk=pk,
    )
    return _create_content_report(request, reply=reply)


def _toggle_vote(request, *, discussion_pk=None, reply_pk=None):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    value = request.POST.get('value')
    if value not in Vote.Value.values:
        return HttpResponseBadRequest('Choose either an upvote or a downvote.')

    if discussion_pk is not None:
        discussion = get_object_or_404(Discussion, pk=discussion_pk)
        target_filters = {'discussion': discussion}
        redirect_url = discussion.get_absolute_url()
    else:
        reply = get_object_or_404(
            Reply.objects.select_related('discussion'),
            pk=reply_pk,
        )
        discussion = reply.discussion
        target_filters = {'reply': reply}
        redirect_url = f'{discussion.get_absolute_url()}#reply-{reply.pk}'

    vote_filters = {'user': request.user, **target_filters}
    vote, created = Vote.objects.get_or_create(
        **vote_filters,
        defaults={'value': value},
    )
    if created:
        messages.success(request, 'Your vote has been recorded.')
    elif vote.value == value:
        vote.delete()
        messages.success(request, 'Your vote has been removed.')
    else:
        vote.value = value
        vote.save(update_fields=('value', 'updated_at'))
        messages.success(request, 'Your vote has been changed.')
    return redirect(redirect_url)


@login_required
def vote_discussion(request, pk):
    return _toggle_vote(request, discussion_pk=pk)


@login_required
def vote_reply(request, pk):
    return _toggle_vote(request, reply_pk=pk)


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
