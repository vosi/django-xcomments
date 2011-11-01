from django.conf.urls import patterns, url
from comments.views.commenting import PostComment
from comments.views.moderation import ModerationHide
from comments.views.rating import RatingRate

urlpatterns = patterns('comments.views',
    url(r'^comments/add/$',                PostComment.as_view(),    name='comments-post-comment'),
    url(r'^comments/moderate/hide/(?P<id>\d+)/', ModerationHide.as_view(), name='comments-moderate-hide'),
    url(r'^comments/rate/(?P<id>\d+)/plus/',     RatingRate.as_view(rate='plus'),       name='comments-rating-plus'),
    url(r'^comments/rate/(?P<id>\d+)/minus/',    RatingRate.as_view(rate='minus'),       name='comments-rating-minus')
)
