import datetime
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import urlresolvers
from django.db import models
from django.contrib.contenttypes import generic
from django.conf import settings
from django.db.models.loading import get_model
from django.utils.translation import ugettext_lazy as _
from comments.managers import CommentManager

PATH_SEPARATOR = getattr(settings, 'COMMENT_PATH_SEPARATOR', '/')
PATH_DIGITS = getattr(settings, 'COMMENT_PATH_DIGITS', 10)
COMMENT_MAX_LENGTH = getattr(settings,'COMMENT_MAX_LENGTH',3000)


class BaseCommentAbstractModel(models.Model):
    content_type   = models.ForeignKey(ContentType, verbose_name=_('content type'),
            related_name="content_type_set_for_%(class)s")
    object_pk      = models.TextField(_('object ID'))
    content_object = generic.GenericForeignKey(ct_field="content_type", fk_field="object_pk")
    site           = models.ForeignKey(Site)

    class Meta:
        abstract = True


    def get_content_object_url(self):
        return urlresolvers.reverse(
            "comments-url-redirect",
            args=(self.content_type_id, self.object_pk)
        )


class Comment(BaseCommentAbstractModel):
    user        = models.ForeignKey(User, verbose_name=_('user'), related_name="%(class)s_comments")
    profile     = models.ForeignKey(get_model(*settings.AUTH_PROFILE_MODULE.split('.')), related_name="%(class)s_profile")
    comment     = models.TextField(_('comment'), max_length=COMMENT_MAX_LENGTH)

    rating      = models.IntegerField(_('Rating'), default=0)

    submit_date = models.DateTimeField(_('date/time submitted'), default=None)
    ip_address  = models.IPAddressField(_('IP address'), blank=True, null=True)
    is_public   = models.BooleanField(_('is public'), default=True,
                    help_text=_('Uncheck this box to make the comment effectively ' \
                                'disappear from the site.'))
    is_removed  = models.BooleanField(_('is removed'), default=False,
                    help_text=_('Check this box if the comment is inappropriate. ' \
                                'A "This comment has been removed" message will ' \
                                'be displayed instead.'))
    parent      = models.ForeignKey('self', null=True, blank=True, default=None,
                    related_name='children', verbose_name=_('Parent comment'))
    last_child  = models.ForeignKey('self', null=True, blank=True,
                    verbose_name=_('Last child'), related_name="last_comment")
    tree_path   = models.CharField(_('Tree path'), editable=False,
                    db_index=True, max_length=255)

    objects = CommentManager()

    class Meta(object):
        ordering = ('tree_path',)
        permissions = [("can_moderate", "Can moderate comments")]
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __unicode__(self):
        return "%s: %s..." % (self.user, self.comment[:50])

    def save(self, *args, **kwargs):
        skip_tree_path = kwargs.pop('skip_tree_path', False)
        if self.submit_date is None:
            self.submit_date = datetime.datetime.now()
        self.profile = self.user.get_profile()
        super(Comment, self).save(*args, **kwargs)
        if skip_tree_path:
            return None

        tree_path = unicode(self.pk).zfill(PATH_DIGITS)
        if self.parent:
            tree_path = PATH_SEPARATOR.join((self.parent.tree_path, tree_path))

            self.parent.last_child = self
            Comment.objects.filter(pk=self.parent_id).update(last_child=self)

        self.tree_path = tree_path
        Comment.objects.filter(pk=self.pk).update(tree_path=tree_path)

    def _get_userinfo(self):
        if not hasattr(self, "_userinfo"):
            self._userinfo = {}
            u = self.user
            if u.email:
                self._userinfo["email"] = u.email
            if u.get_full_name():
                self._userinfo["name"] = self.user.get_full_name()
            else:
                self._userinfo["name"] = u.username
        return self._userinfo
    userinfo = property(_get_userinfo, doc=_get_userinfo.__doc__)

    def _get_depth(self):
        return len(self.tree_path.split(PATH_SEPARATOR))
    depth = property(_get_depth)

    def _root_id(self):
        return int(self.tree_path.split(PATH_SEPARATOR)[0])
    root_id = property(_root_id)

    def _root_path(self):
        return Comment.objects.filter(pk__in=self.tree_path.split(PATH_SEPARATOR)[:-1])
    root_path = property(_root_path)

    def get_absolute_url(self, anchor_pattern="#c%(id)s"):
        return self.get_content_object_url() + (anchor_pattern % self.__dict__)

    def get_as_text(self):
        d = {
            'user': self.user,
            'date': self.submit_date,
            'comment': self.comment,
            'domain': self.site.domain,
            'url': self.get_absolute_url()
        }
        return _('Posted by %(user)s at %(date)s\n\n%(comment)s\n\nhttp://%(domain)s%(url)s') % d


class CommentRating(models.Model):
    user      = models.ForeignKey(User, verbose_name=_('user'), related_name="comment_rate")
    comment   = models.ForeignKey(Comment, verbose_name=_('comment'), related_name="rate")
    vote      = models.IntegerField(_('Vote'), db_index=True, choices=((1, '+'),(-1, '-')))
    vote_date = models.DateTimeField(_('date'), default=None)

    class Meta:
        unique_together = [('user', 'comment')]
        verbose_name = _('Comment vote')
        verbose_name_plural = _('Comment votes')

    def __unicode__(self):
        return "%s vote of comment ID %s by %s" % \
            (self.vote, self.comment_id, self.user.username)

    def save(self, *args, **kwargs):
        if self.vote_date is None:
            self.vote_date = datetime.datetime.now()
        super(CommentRating, self).save(*args, **kwargs)
