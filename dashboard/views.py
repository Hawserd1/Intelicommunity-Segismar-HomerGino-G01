from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import UserRoleForm
from accounts.models import CustomUser
from community.models import CommunitySection, ContentReport, Discussion, Reply


ROLE_DASHBOARDS = {
    CustomUser.Role.STANDARD_USER: 'dashboard:member',
    CustomUser.Role.MODERATOR: 'dashboard:moderator',
    CustomUser.Role.ADMINISTRATOR: 'dashboard:administrator',
}

DASHBOARD_CONTENT = {
    CustomUser.Role.STANDARD_USER: {
        'eyebrow': 'YOUR COMMUNITY',
        'heading': 'A place for good questions.',
        'intro': 'Find your people, share what you know, and keep useful answers close.',
        'cards': (
            ('communities', 'Explore communities', 'Find conversations in topics you care about.', 'Explore'),
            ('discussions', 'Browse discussions', 'Read questions and insights shared by the community.', 'Browse'),
            ('bookmarks', 'Your bookmarks', 'Useful discussions you save will be easy to find here.', 'Coming soon'),
            ('notifications', 'Notifications', 'Keep up with replies and activity on your posts.', 'Coming soon'),
        ),
    },
    CustomUser.Role.MODERATOR: {
        'eyebrow': 'MODERATION DESK',
        'heading': 'Keep the conversation thoughtful.',
        'intro': 'A clear view of community reports and the tools moderators will use to review them.',
        'cards': (
            ('reports', 'Reported content', 'Review community reports and decide what needs attention.', 'Review'),
            ('discussions', 'Community discussions', 'Browse conversations that may need moderator support.', 'Browse'),
            ('activity-reports', 'Activity overview', 'See moderation and community activity summaries.', 'View reports'),
        ),
    },
    CustomUser.Role.ADMINISTRATOR: {
        'eyebrow': 'PLATFORM OVERVIEW',
        'heading': 'The community, at a glance.',
        'intro': 'Manage platform access and get ready to oversee the growing Intelicommunity.',
        'cards': (
            ('user-management', 'User management', 'Review accounts and assign application roles.', 'Manage roles'),
            ('activity-reports', 'Platform reports', 'Summaries for discussions, sections, and reports.', 'View reports'),
            ('platform-settings', 'Platform settings', 'A home for future community-wide settings.', 'Coming soon'),
        ),
    },
}

COMING_SOON_FEATURES = {
    'bookmarks': 'Saved Discussions',
    'notifications': 'Notifications',
    'platform-settings': 'Platform Settings',
}


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


@login_required
def home(request):
    dashboard_name = ROLE_DASHBOARDS.get(request.user.role)
    if dashboard_name is None:
        raise PermissionDenied
    return redirect(dashboard_name)


def _render_dashboard(request, role):
    context = {
        **DASHBOARD_CONTENT[role],
        'role_label': request.user.get_role_display(),
        'followed_sections': request.user.followed_sections.annotate(
            discussion_count=Count('discussions', distinct=True)
        ),
        'followed_discussions': (
            Discussion.objects.filter(section__followers=request.user)
            .select_related('section', 'author')
            .annotate(reply_count=Count('replies', distinct=True))[:5]
        ),
    }
    if role == CustomUser.Role.MODERATOR:
        context['pending_reports'] = ContentReport.objects.filter(
            status=ContentReport.Status.PENDING
        ).select_related(
            'discussion',
            'discussion__section',
            'reply__discussion',
            'reply__discussion__section',
        )[:5]
        context['pending_report_count'] = ContentReport.objects.filter(
            status=ContentReport.Status.PENDING
        ).count()
    elif role == CustomUser.Role.ADMINISTRATOR:
        role_counts = CustomUser.objects.values('role').annotate(total=Count('pk'))
        context['user_counts_by_role'] = {
            role_value: 0 for role_value, _label in CustomUser.Role.choices
        }
        context['user_counts_by_role'].update(
            {row['role']: row['total'] for row in role_counts}
        )
        context['total_users'] = CustomUser.objects.count()
        context['total_discussions'] = Discussion.objects.count()
        context['total_sections'] = CommunitySection.objects.count()
        context['total_reports'] = ContentReport.objects.count()
    return render(
        request,
        'dashboard/home.html',
        context,
    )


@role_required(CustomUser.Role.STANDARD_USER)
def member_dashboard(request):
    return _render_dashboard(request, CustomUser.Role.STANDARD_USER)


@role_required(CustomUser.Role.MODERATOR)
def moderator_dashboard(request):
    return _render_dashboard(request, CustomUser.Role.MODERATOR)


@role_required(CustomUser.Role.ADMINISTRATOR)
def administrator_dashboard(request):
    return _render_dashboard(request, CustomUser.Role.ADMINISTRATOR)


@login_required
def coming_soon(request, feature):
    title = COMING_SOON_FEATURES.get(feature)
    if title is None:
        return HttpResponseNotFound('That feature was not found.')
    return render(
        request,
        'dashboard/coming_soon.html',
        {'feature_title': title},
        status=501,
    )


@login_required
def user_management(request):
    if request.user.role != CustomUser.Role.ADMINISTRATOR:
        raise PermissionDenied
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    users = CustomUser.objects.exclude(pk=request.user.pk).order_by('username')
    return render(
        request,
        'dashboard/user_management.html',
        {'users': _users_with_role_forms(users)},
    )


def _users_with_role_forms(users, *, form=None, form_user_id=None):
    for user in users:
        user.role_form = (
            form
            if user.pk == form_user_id
            else UserRoleForm(instance=user, auto_id=f'role_{user.pk}_%s')
        )
    return users


@login_required
def update_user_role(request, pk):
    if request.user.role != CustomUser.Role.ADMINISTRATOR:
        raise PermissionDenied
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    user = get_object_or_404(CustomUser.objects.exclude(pk=request.user.pk), pk=pk)
    form = UserRoleForm(request.POST, instance=user, auto_id=f'role_{user.pk}_%s')
    if form.is_valid():
        form.save()
        messages.success(request, f"{user.username}'s role was updated.")
        return redirect('dashboard:user_management')

    users = _users_with_role_forms(
        CustomUser.objects.exclude(pk=request.user.pk).order_by('username'),
        form=form,
        form_user_id=user.pk,
    )
    return render(
        request,
        'dashboard/user_management.html',
        {'users': users},
        status=400,
    )


def _can_view_moderation_reports(user):
    return user.role in (
        CustomUser.Role.MODERATOR,
        CustomUser.Role.ADMINISTRATOR,
    )


@login_required
def reported_content(request):
    if not _can_view_moderation_reports(request.user):
        raise PermissionDenied

    selected_status = request.GET.get('status', ContentReport.Status.PENDING)
    if selected_status not in ContentReport.Status.values and selected_status != 'all':
        selected_status = ContentReport.Status.PENDING

    reports = ContentReport.objects.select_related(
        'reported_by',
        'reviewed_by',
        'discussion__section',
        'discussion__author',
        'reply__discussion__section',
        'reply__discussion__author',
        'reply__author',
    )
    if selected_status != 'all':
        reports = reports.filter(status=selected_status)

    return render(
        request,
        'dashboard/reported_content.html',
        {
            'reports': reports,
            'selected_status': selected_status,
            'statuses': ContentReport.Status.choices,
            'pending_count': ContentReport.objects.filter(
                status=ContentReport.Status.PENDING
            ).count(),
        },
    )


@login_required
def review_report(request, pk):
    if not _can_view_moderation_reports(request.user):
        raise PermissionDenied
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    status = request.POST.get('status')
    if status not in (ContentReport.Status.REVIEWED, ContentReport.Status.DISMISSED):
        return HttpResponseBadRequest('Choose reviewed or dismissed.')

    report = get_object_or_404(ContentReport, pk=pk)
    report.status = status
    report.reviewed_by = request.user
    report.reviewed_at = timezone.now()
    report.save(update_fields=('status', 'reviewed_by', 'reviewed_at'))
    messages.success(request, 'The report status was updated.')
    return redirect('dashboard:reported_content')


@login_required
def activity_reports(request):
    if not _can_view_moderation_reports(request.user):
        raise PermissionDenied

    reported_users = {}
    discussion_author_counts = (
        Discussion.objects.filter(content_reports__isnull=False)
        .values('author_id', 'author__username')
        .annotate(report_count=Count('content_reports'))
    )
    reply_author_counts = (
        Reply.objects.filter(content_reports__isnull=False)
        .values('author_id', 'author__username')
        .annotate(report_count=Count('content_reports'))
    )
    for row in (*discussion_author_counts, *reply_author_counts):
        user_count = reported_users.setdefault(
            row['author_id'],
            {'username': row['author__username'], 'report_count': 0},
        )
        user_count['report_count'] += row['report_count']

    most_reported_users = sorted(
        reported_users.values(),
        key=lambda item: (-item['report_count'], item['username'].casefold()),
    )[:10]
    section_discussions = CommunitySection.objects.annotate(
        discussion_count=Count('discussions', distinct=True),
    ).order_by('-discussion_count', 'name')

    return render(
        request,
        'dashboard/activity_reports.html',
        {
            'total_reports': ContentReport.objects.count(),
            'pending_count': ContentReport.objects.filter(
                status=ContentReport.Status.PENDING
            ).count(),
            'reviewed_count': ContentReport.objects.filter(
                status=ContentReport.Status.REVIEWED
            ).count(),
            'dismissed_count': ContentReport.objects.filter(
                status=ContentReport.Status.DISMISSED
            ).count(),
            'most_reported_users': most_reported_users,
            'section_discussions': section_discussions,
        },
    )
