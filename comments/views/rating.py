from django import http
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import simplejson
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from comments import signals
import comments

class RatingRate(View):
    rate = None
    http_method_names = ['post', 'get']

    @method_decorator(login_required)
    @method_decorator(permission_required('comments.add_commentrating'))
    def dispatch(self, *args, **kwargs):
        return super(RatingRate, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        referer = request.META.get('HTTP_REFERER', '/')
        return http.HttpResponseRedirect(referer)

    def post(self, request, *args, **kwargs):
        try:
            comment = comments.get_model().objects.get(pk=kwargs['id'])
        except comments.get_model().DoesNotExist:
            content = {
                'state': 'error',
                'rating': 0
            }
        else:
            responses = signals.comment_was_rated.send(
                sender  = comment.__class__,
                comment = comment,
                request = self.request,
                rate    = self.rate
            )
            rating = 0
            for (receiver, response) in responses:
                if response:
                    rating += response
            comment.rating = rating
            comment.save()
            content = {
                'state': 'success',
                'rating': rating
            }
        return http.HttpResponse(simplejson.dumps(content), content_type='application/json')

