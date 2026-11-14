from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.models import CustomUser


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
            ('discussions', 'Start a discussion', 'Ask a question or share an idea with the community.', 'Get started'),
            ('bookmarks', 'Your bookmarks', 'Useful discussions you save will be easy to find here.', 'Coming soon'),
            ('notifications', 'Notifications', 'Keep up with replies and activity on your posts.', 'Coming soon'),
        ),
    },
    CustomUser.Role.MODERATOR: {
        'eyebrow': 'MODERATION DESK',
        'heading': 'Keep the conversation thoughtful.',
        'intro': 'A clear view of community reports and the tools moderators will use to review them.',
        'cards': (
            ('reports', 'Reported content', 'Review community reports and decide what needs attention.', 'Coming soon'),
            ('discussions', 'Community discussions', 'Browse conversations that may need moderator support.', 'Coming soon'),
            ('activity-reports', 'Activity overview', 'See moderation and community activity summaries.', 'Coming soon'),
        ),
    },
    CustomUser.Role.ADMINISTRATOR: {
        'eyebrow': 'PLATFORM OVERVIEW',
        'heading': 'The community, at a glance.',
        'intro': 'Manage platform access and get ready to oversee the growing Intelicommunity.',
        'cards': (
            ('user-management', 'User management', 'Review accounts and assign application roles.', 'Open Django admin'),
            ('activity-reports', 'Platform reports', 'Summaries for discussions, sections, and reports.', 'Coming soon'),
            ('platform-settings', 'Platform settings', 'A home for future community-wide settings.', 'Coming soon'),
        ),
    },
}

COMING_SOON_FEATURES = {
    'communities': 'Community Sections',
    'discussions': 'Discussions',
    'bookmarks': 'Saved Discussions',
    'notifications': 'Notifications',
    'reports': 'Content Reports',
    'activity-reports': 'Activity Reports',
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
    return render(
        request,
        'dashboard/home.html',
        {
            **DASHBOARD_CONTENT[role],
            'role_label': request.user.get_role_display(),
        },
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
    if request.user.role != CustomUser.Role.ADMINISTRATOR or not request.user.is_staff:
        raise PermissionDenied
    return redirect(reverse('admin:accounts_customuser_changelist'))
