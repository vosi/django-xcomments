from django.utils import simplejson
from django.utils.decorators import method_decorator
from django.views.generic.base import View
import comments
from django import template, http
from django.conf import settings
from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import get_object_or_404, render_to_response
from django.views.decorators.csrf import csrf_protect
from comments import signals


class ModerationHide(View):
    http_method_names = ['post', 'get']

    @method_decorator(login_required)
    @method_decorator(permission_required('comments.can_moderate'))
    def dispatch(self, *args, **kwargs):
        return super(ModerationHide, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        referer = request.META.get('HTTP_REFERER', '/')
        return http.HttpResponseRedirect(referer)

    def post(self, request, *args, **kwargs):
        try:
            comment = comments.get_model().objects.get(pk=kwargs['id'])
        except comments.get_model().DoesNotExist:
            content = {
                'state': 'error',
            }
        else:
            signals.comment_was_hidden.send(
                sender  = comment.__class__,
                comment = comment,
                request = self.request,
            )

        perform_hide(request, comment)
        content = {
            'state': 'success',
        }
        return http.HttpResponse(simplejson.dumps(content), content_type='application/json')


def perform_delete(request, comment):
    comment.is_removed = True
    comment.save()


def perform_hide(request, comment):
    comment.is_public = False
    comment.save()
