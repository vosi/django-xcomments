from django.contrib import admin
from comments.models import Comment
from django.utils.translation import ugettext_lazy as _, ungettext
from comments.views.moderation import perform_delete, perform_hide


class CommentsAdmin(admin.ModelAdmin):
    fieldsets = (
        (_('Content'),
           {'fields': ('user', 'comment')}
        ),
        (_('Metadata'),
           {'fields': ('submit_date', 'ip_address', 'is_public', 'is_removed')}
        ),
    )

    list_display = ('user', 'content_type', 'object_pk', 'parent', 'ip_address', 'submit_date', 'is_public', 'is_removed')
    list_filter = ('submit_date', 'site', 'is_public', 'is_removed')
    date_hierarchy = 'submit_date'
    ordering = ('-submit_date',)
    raw_id_fields = ("parent",)
    search_fields = ('comment', 'user__username', 'ip_address')
    actions = ["hide_comments", "remove_comments"]
    readonly_fields = ['user', 'submit_date', 'ip_address']

    def has_add_permission(self, request):
        return False

    def delete_model(self, request, obj):
        perform_delete(request, obj)

    def get_actions(self, request):
        actions = super(CommentsAdmin, self).get_actions(request)
        # Restrict deleting! (only mark as deleted)
        actions.pop('delete_selected')
        if not request.user.has_perm('comments.can_moderate'):
            if 'hide_comments' in actions:
                actions.pop('hide_comments')
            if 'remove_comments' in actions:
                actions.pop('remove_comments')
        return actions

    def hide_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_hide,
                        lambda n: ungettext('hiden', 'hiden', n))
    hide_comments.short_description = _("Hide selected comments")

    def remove_comments(self, request, queryset):
        self._bulk_flag(request, queryset, perform_delete,
                        lambda n: ungettext('removed', 'removed', n))
    remove_comments.short_description = _("Remove selected comments")

    def _bulk_flag(self, request, queryset, action, done_message):
        """
        Flag, approve, or remove some comments from an admin action. Actually
        calls the `action` argument to perform the heavy lifting.
        """
        n_comments = 0
        for comment in queryset:
            action(request, comment)
            n_comments += 1

        msg = ungettext(u'1 comment was successfully %(action)s.',
                        u'%(count)s comments were successfully %(action)s.',
                        n_comments)
        self.message_user(request, msg % {'count': n_comments, 'action': done_message(n_comments)})

admin.site.register(Comment, CommentsAdmin)
