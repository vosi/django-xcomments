from django.core import urlresolvers
from comments.models import Comment
from comments.forms import CommentForm

def get_model():
    return Comment

def get_form():
    return CommentForm

def get_form_target():
    return urlresolvers.reverse("comments-post-comment")

def get_flag_url(comment):
    return urlresolvers.reverse("comments.views.moderation.flag", args=(comment.id,))

def get_delete_url(comment):
    return urlresolvers.reverse("comments.views.moderation.delete", args=(comment.id,))
