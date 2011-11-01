from django import template
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
import comments
from django.utils.encoding import smart_unicode
from comments.util import annotate_tree_properties, fill_tree

register = template.Library()


class BaseCommentNode(template.Node):
    @classmethod
    def handle_token(cls, parser, token):
        """Class method to parse get_comment_list/count/form and return a Node."""
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must be 'for'" % tokens[0])

        # {% get_whatever for obj as varname %}
        if len(tokens) == 5:
            if tokens[3] != 'as':
                raise template.TemplateSyntaxError("Third argument in %r must be 'as'" % tokens[0])
            return cls(
                object_expr = parser.compile_filter(tokens[2]),
                as_varname = tokens[4],
            )

        # {% get_whatever for app.model pk as varname %}
        elif len(tokens) == 6:
            if tokens[4] != 'as':
                raise template.TemplateSyntaxError("Fourth argument in %r must be 'as'" % tokens[0])
            return cls(
                ctype = BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr = parser.compile_filter(tokens[3]),
                as_varname = tokens[5]
            )

        else:
            raise template.TemplateSyntaxError("%r tag requires 4 or 5 arguments" % tokens[0])

    @staticmethod
    def lookup_content_type(token, tagname):
        try:
            app, model = token.split('.')
            return ContentType.objects.get_by_natural_key(app, model)
        except ValueError:
            raise template.TemplateSyntaxError("Third argument in %r must be in the format 'app.model'" % tagname)
        except ContentType.DoesNotExist:
            raise template.TemplateSyntaxError("%r tag has non-existant content-type: '%s.%s'" % (tagname, app, model))

    def __init__(self, ctype=None, object_pk_expr=None, object_expr=None, as_varname=None, comment=None, parent=None, tag_name=None):
        if ctype is None and object_expr is None:
            raise template.TemplateSyntaxError("Comment nodes must be given either a literal object or a ctype and object pk.")
        self.comment_model = comments.get_model()
        self.as_varname = as_varname
        self.ctype = ctype
        self.object_pk_expr = object_pk_expr
        self.object_expr = object_expr
        self.comment = comment
        self.parent = parent

    def render(self, context):
        qs = self.get_query_set(context)
        context[self.as_varname] = self.get_context_value_from_queryset(context, qs)
        return ''

    def get_query_set(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if not object_pk:
            return self.comment_model.objects.none()

        qs = self.comment_model.objects.select_related('user', 'profile').filter(
            content_type = ctype,
            object_pk    = smart_unicode(object_pk),
            site__pk     = settings.SITE_ID,
        )

        return qs

    def get_target_ctype_pk(self, context):
        if self.object_expr:
            try:
                obj = self.object_expr.resolve(context)
            except template.VariableDoesNotExist:
                return None, None
            return ContentType.objects.get_for_model(obj), obj.pk
        else:
            return self.ctype, self.object_pk_expr.resolve(context, ignore_failures=True)


    def get_context_value_from_queryset(self, context, qs):
        """Subclasses should override this."""
        raise NotImplementedError


class CommentFormNode(BaseCommentNode):
    """
    Insert a form for the comment model into the context.
    """
    @classmethod
    def handle_token(cls, parser, token):
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag "
                "must be 'for'" % (tokens[0],))

        if len(tokens) < 7:
            return super(CommentFormNode, cls).handle_token(parser, token)
        # {% get_comment_form for [object] as [varname] with [parent_id] %}
        if len(tokens) == 7:
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have a 'with' "
                    "as the last but one argument." % (tokens[0],))
            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                as_varname=tokens[4],
                parent=parser.compile_filter(tokens[6]),
            )
        # {% get_comment_form for [app].[model] [object_id] as [varname] with [parent_id] %}
        elif len(tokens) == 8:
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have a 'with' "
                    "as the last but one argument." % (tokens[0],))
            return cls(
                ctype=BaseCommentNode.lookup_content_type(tokens[2],
                    tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
                as_varname=tokens[5],
                parent=parser.compile_filter(tokens[7]),
            )

    def get_form(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        parent_id = None
        if self.parent:
            parent_id = self.parent.resolve(context, ignore_failures=True)
        if object_pk:
            return comments.get_form()(
                ctype.get_object_for_this_type(pk=object_pk), parent=parent_id)
        else:
            return None

    def render(self, context):
        context[self.as_varname] = self.get_form(context)
        return ''

class RenderCommentFormNode(CommentFormNode):
    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse render_comment_form and return a Node.
        """
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must"
                " be 'for'" % tokens[0])

        # {% render_comment_form for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))
        # {% render_comment_form for app.model object_pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3])
            )
        # {% render_comment_form for obj with parent_id %}
        elif len(tokens) == 5:
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have 'with' as "
                    "the last but one argument" % (tokens[0],))
            return cls(
                object_expr=parser.compile_filter(tokens[2]),
                parent=parser.compile_filter(tokens[4])
            )
        # {% render_comment_form for app.model object_pk with parent_id %}
        elif len(tokens) == 6:
            if tokens[-2] != u'with':
                raise template.TemplateSyntaxError("%r tag must have 'with' as "
                    "the last but one argument" % (tokens[0],))
            return cls(
                ctype=BaseCommentNode.lookup_content_type(tokens[2],
                    tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3]),
                parent=parser.compile_filter(tokens[5])
            )
        else:
            raise template.TemplateSyntaxError("%r tag takes 3 to 5 "
                "arguments" % (tokens[0],))

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "comments/%s/%s/form.html" % (ctype.app_label, ctype.model),
                "comments/%s/form.html" % ctype.app_label,
                "comments/form.html"
            ]
            context.push()
            form_str = render_to_string(
                template_search_list,
                {"form" : self.get_form(context)},
                context
            )
            context.pop()
            return form_str
        else:
            return ''

class RenderCommentsNode(BaseCommentNode):
    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse render_comments and return a Node.
        """
        tokens = token.contents.split()
        if tokens[1] != 'for':
            raise template.TemplateSyntaxError("Second argument in %r tag must"
                " be 'for'" % tokens[0])

        # {% render_comments for obj %}
        if len(tokens) == 3:
            return cls(object_expr=parser.compile_filter(tokens[2]))
        # {% render_comments for app.model object_pk %}
        elif len(tokens) == 4:
            return cls(
                ctype=BaseCommentNode.lookup_content_type(tokens[2], tokens[0]),
                object_pk_expr=parser.compile_filter(tokens[3])
            )
        else:
            raise template.TemplateSyntaxError("%r tag takes 3 "
                "arguments" % (tokens[0],))

    def render(self, context):
        ctype, object_pk = self.get_target_ctype_pk(context)
        if object_pk:
            template_search_list = [
                "comments/%s/%s/comments.html" % (ctype.app_label, ctype.model),
                "comments/%s/comments.html" % ctype.app_label,
                "comments/comments.html"
            ]
            context.push()
            qs = self.get_query_set(context)
            form_str = render_to_string(
                template_search_list,
                {
                    "object_pk"   : object_pk,
                    "content_type": "%s.%s" % (ctype.app_label, ctype.model),
                    "comment_list": qs
                },
                context
            )
            context.pop()
            return form_str
        else:
            return ''


@register.tag
def get_comment_form(parser, token):
    """
    Get a (new) form object to post a new comment.

    Syntax::

        {% get_comment_form for [object] as [varname] %}
        {% get_comment_form for [object] as [varname] with [parent_id] %}
        {% get_comment_form for [app].[model] [object_id] as [varname] %}
        {% get_comment_form for [app].[model] [object_id] as [varname] with [parent_id] %}
    """
    return CommentFormNode.handle_token(parser, token)

@register.tag
def render_comment_form(parser, token):
    """
    Render the comment form (as returned by ``{% render_comment_form %}``)
    through the ``comments/form.html`` template.

    Syntax::

        {% render_comment_form for [object] %}
        {% render_comment_form for [object] with [parent_id] %}
        {% render_comment_form for [app].[model] [object_id] %}
        {% render_comment_form for [app].[model] [object_id] with [parent_id] %}
    """
    return RenderCommentFormNode.handle_token(parser, token)

@register.tag
def render_comments(parser, token, *args, **kwargs):
    """
    Render ready to use comments html

    Syntax::
        {% render_comments for [object] %}
        {% render_comments for [app].[model] [object_id] %}
    """
    return RenderCommentsNode.handle_token(parser, token)

@register.simple_tag
def comment_form_target():
    """
    Get the target URL for the comment form.

    Example::
        <form action="{% comment_form_target %}" method="post">
    """
    return comments.get_form_target()


@register.filter
def annotate_tree(comments):
    return annotate_tree_properties(comments)

register.filter(fill_tree)
