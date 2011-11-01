from django import http
from django.contrib.auth.context_processors import PermWrapper
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.template.loader import render_to_string
from django.utils import simplejson
from django.utils.decorators import method_decorator
from django.utils.html import escape
from django.views.generic.edit import FormView
from comments import signals
import comments


class PostComment(FormView):
    form_class = comments.get_form()
    template_name = 'comments/form.html'
    error = False
    http_method_names = ['post', 'get']

    @method_decorator(login_required)
    @method_decorator(permission_required('comments.add_comment'))
    def dispatch(self, *args, **kwargs):
        return super(PostComment, self).dispatch(*args, **kwargs)

    def get_form(self, form_class):
        return form_class(self.target, **self.get_form_kwargs())

    def get_form_kwargs(self):
        kwargs = {'parent': self.request.POST.get('parent', '')}
        if self.request.method in ('POST', 'PUT') and not self.request.POST.get('initial', False):
            kwargs.update({
                'data': self.request.POST,
                'user': self.request.user
            })
        return kwargs

    def get(self, request, *args, **kwargs):
        referer = request.META.get('HTTP_REFERER', '/')
        return http.HttpResponseRedirect(referer)

    def post(self, request, *args, **kwargs):
        objs = self.object_lookup()
        if isinstance(objs, dict):
            return objs

        form = self.get_form(self.form_class)

        if request.POST.get('initial', False):
            content = {
                'state': 'form',
                'html': render_to_string(self.get_template_names(), self.get_context_data(form=form))
            }
        else:
            if form.security_errors():
                content = {
                    'state': 'error',
                    'html': "The comment form failed security verification: %s" % escape(str(form.security_errors()))
                }
                self.error = True

            if not self.error:
                if form.is_valid():
                    content = self.form_valid(form)
                else:
                    content = self.form_invalid(form)

        return http.HttpResponse(simplejson.dumps(content), content_type='application/json')

    def form_valid(self, form):
        comment = form.get_comment_object()

        responses = signals.comment_will_be_posted.send(
           sender  = comment.__class__,
            comment = comment,
            request = self.request
        )
        for (receiver, response) in responses:
            if response == False:
                content = {
                    'state': 'error',
                    'html': "comment_will_be_posted receiver %r killed the comment" % receiver.__name__
                }
                self.error = True
                return content

        if not self.error and comment.parent and comment.parent.depth >= 20:
            content = {
                'state': 'error',
                'html': "Max depth reached. Start a new thread"
            }
            self.error = True
            return content

        comment.ip_address = self.request.META.get("REMOTE_ADDR", None)
        comment.user = self.request.user
        comment.save()

        signals.comment_was_posted.send(
            sender  = comment.__class__,
            comment = comment,
            request = self.request
        )

        #return self.render_to_response(self.get_context_data(form=form))
        context = {
            'comment': comment,
            'user'   : self.request.user,
            'perms'  : PermWrapper(self.request.user),
            'object_pk' : self.request.POST.get('object_pk'),
            'content_type' : self.request.POST.get('content_type')
        }
        return {
            'state': 'comment',
            'html': render_to_string('comments/comment.html', context)
        }

    def form_invalid(self, form):
        return {
            'state': 'form',
            'html': render_to_string(self.get_template_names(), self.get_context_data(form=form))
        }

    def object_lookup(self):
        data = self.request.POST.copy()

        # Look up the object we're trying to comment about
        ctype = data.get("content_type")
        object_pk = data.get("object_pk")
        if ctype is None or object_pk is None:
            self.error = True
            return {
                'state': 'error',
                'html': "Missing content_type or object_pk field."
            }
        try:
            model = models.get_model(*ctype.split(".", 1))
            self.target = model._default_manager.get(pk=object_pk)
        except TypeError:
            self.error = True
            return {
                'state': 'error',
                'html': "Invalid content_type value: %r" % escape(ctype)
            }
        except AttributeError:
            self.error = True
            return {
                'state': 'error',
                'html': "The given content-type %r does not resolve to a valid model." % escape(ctype)
            }
        except ObjectDoesNotExist:
            self.error = True
            return {
                'state': 'error',
                'html': "No object matching content-type %r and object PK %r exists." % \
                    (escape(ctype), escape(object_pk))
            }
        except (ValueError, ValidationError), e:
            self.error = True
            return {
                'state': 'error',
                'html': "Attempting go get content-type %r and object PK %r exists raised %s" % \
                    (escape(ctype), escape(object_pk), e.__class__.__name__)
            }
