from django.contrib import admin

from .models import CommunitySection, Discussion, Reply, Tag


@admin.register(CommunitySection)
class CommunitySectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'follower_count', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    @admin.display(description='Followers')
    def follower_count(self, section):
        return section.followers.count()


class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 0
    readonly_fields = ('author', 'body', 'created_at')
    can_delete = False


@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'author', 'created_at')
    list_filter = ('section', 'created_at')
    search_fields = ('title', 'body', 'author__username', 'tags__name')
    filter_horizontal = ('tags',)
    inlines = (ReplyInline,)


@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = ('discussion', 'author', 'created_at')
    search_fields = ('body', 'author__username', 'discussion__title')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
